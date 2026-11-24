"""
SiteSense Operations Agent - Core Runtime.

Orchestrates the ReAct (Reason-Act-Observe) loop using Groq function calling,
delegates tasks to registered domain tools, and records full audit traces
to the Postgres 'agent_runs' table.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from groq import Groq
import psycopg2

# Load environment configuration
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from agentic.tools import registry
from agentic.router import route_query
from agentic.guardrails import check_input_guardrail
from agentic.memory import memory
from agentic.tools.query_database import get_db_url

AGENT_PROMPT = """You are SiteSense Operations Agent, an AI compliance auditor for physical operational facilities (retail superstores, warehouses, distribution centers).

Tool Guidelines:
1. `search_policies`: Call this to retrieve governing policy clauses, section numbers, and mandatory standards.
2. `analyse_media`: Call this with `site_id` (e.g. site_id='Site 7') to retrieve visual detections, bounding boxes, zones, and annotated image evidence paths for a site.
3. `query_database`: Call this for SQL queries. Common query pattern for rule compliance:
   SELECT s.name as site, f.status, f.evidence_ids, r.name as rule, r.policy_ref, i.created_at
   FROM findings f
   JOIN inspections i ON f.inspection_id = i.id
   JOIN sites s ON i.site_id = s.id
   JOIN rules r ON f.rule_id = r.id
   WHERE s.name ILIKE '%<site_name>%'
4. `raise_ticket`: Propose a ticket for a failed finding (status is always 'proposed' awaiting approval).

Rules for your answers:
- Always cite the exact Policy Clause (e.g., 'Clause 4.1' or 'Clause 4.2').
- If an inspection failed or passed, state the exact status ('pass', 'fail', 'review') and reference the evidence (detection ID, zone, and annotated image URL).
- Synthesize your final answer concisely once you have the policy and site findings. Do not call redundant queries.
"""


def log_agent_run_to_neon(
    user_id: Optional[str],
    question: str,
    route: str,
    tools_called: List[Dict[str, Any]],
    tokens: int,
    cost: float,
    latency: float
) -> Optional[str]:
    """Logs the execution trace, tokens, and latency to the Neon DB 'agent_runs' table."""
    db_url = get_db_url()
    if not db_url:
        return None

    try:
        with psycopg2.connect(db_url) as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO agent_runs (user_id, question, route, tools_called, tokens, cost, latency)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (
                    user_id,
                    question,
                    route,
                    json.dumps(tools_called),
                    tokens,
                    cost,
                    round(latency, 3)
                ))
                run_id = cur.fetchone()[0]
                return str(run_id)
    except Exception as err:
        print(f"[Audit Log Warning] Could not persist agent run: {err}")
        return None


class SiteSenseAgent:
    """Core ReAct controller for the SiteSense platform."""

    def __init__(self, model_name: Optional[str] = None, max_iterations: int = 6):
        self.model_name = model_name or os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        self.max_iterations = max_iterations
        self.api_key = os.getenv("GROQ_API_KEY")

    def run(
        self,
        question: str,
        session_id: str = "default_session",
        user_id: Optional[str] = None,
        has_image: bool = False
    ) -> Dict[str, Any]:
        """
        Executes the agentic workflow:
        1. Checks input guardrails for prompt injections or malicious commands.
        2. Routes the query to find the best domain path.
        3. Drives the iterative Reason-Act-Observe tool loop until complete.
        4. Saves session turns and logs execution telemetry to Postgres.
        """
        start_time = time.time()
        tool_trace: List[Dict[str, Any]] = []
        total_tokens = 0

        # Safety filter
        is_safe, guard_reason = check_input_guardrail(question)
        if not is_safe:
            return {
                "answer": f"Request blocked by safety guardrails: {guard_reason}",
                "route": "blocked",
                "tools_called": [],
                "tokens": 0,
                "cost": 0.0,
                "latency": round(time.time() - start_time, 3),
                "audit_run_id": None
            }

        # Route query
        routing = route_query(question, has_image=has_image, groq_api_key=self.api_key)
        route = routing.get("route", "general")

        # Early exit for brief conversational greetings
        if route == "general" and len(question.split()) <= 4:
            greeting = (
                "Hello! I am the SiteSense Operations Agent. I can assist you with policy clauses, "
                "site inspection findings, visual detections, and compliance reports. How can I help you today?"
            )
            elapsed = time.time() - start_time
            run_id = log_agent_run_to_neon(user_id, question, route, [], 35, 0.0001, elapsed)
            return {
                "answer": greeting,
                "route": route,
                "tools_called": [],
                "tokens": 35,
                "cost": 0.0001,
                "latency": round(elapsed, 3),
                "audit_run_id": run_id
            }

        # Prepare context and tool schemas
        client = Groq(api_key=self.api_key)
        schemas = registry.get_all_schemas()

        messages = [
            {"role": "system", "content": AGENT_PROMPT}
        ]

        # Inject session history if any exists
        messages.extend(memory.get_history(session_id))
        messages.append({"role": "user", "content": question})

        iteration = 0
        final_answer = ""

        # Main reasoning loop
        while iteration < self.max_iterations:
            iteration += 1

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=schemas,
                tool_choice="auto",
                temperature=0.1
            )

            choice = response.choices[0]
            msg = choice.message
            if hasattr(response, "usage") and response.usage:
                total_tokens += response.usage.total_tokens

            # Process tool calls
            if msg.tool_calls:
                messages.append(msg)

                for call in msg.tool_calls:
                    fn_name = call.function.name
                    try:
                        fn_args = json.loads(call.function.arguments)
                    except Exception:
                        fn_args = {}

                    print(f"  [Agent Step {iteration}] Calling tool: {fn_name} with {fn_args}", flush=True)
                    
                    # Execute tool via registry
                    exec_result = registry.execute(fn_name, fn_args)
                    output_str = json.dumps(exec_result)

                    tool_trace.append({
                        "step": iteration,
                        "tool": fn_name,
                        "arguments": fn_args,
                        "result": exec_result.get("result") or exec_result.get("error")
                    })

                    # Supply observation back to context
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": fn_name,
                        "content": output_str
                    })
            else:
                # Agent concluded reasoning
                final_answer = msg.content or ""
                break

        # Fallback if iterations exhausted
        if not final_answer and iteration >= self.max_iterations:
            final_answer = (
                "Analysis reached iteration limit. Based on collected observations, "
                "please check the specific inspection findings or policy clauses listed in the trace."
            )

        # Telemetry calculations
        cost = round((total_tokens / 1000.0) * 0.003, 6)
        elapsed = time.time() - start_time

        # Update session memory
        memory.add_message(session_id, "user", question)
        memory.add_message(session_id, "assistant", final_answer)

        # Log to Neon DB
        run_id = log_agent_run_to_neon(
            user_id=user_id,
            question=question,
            route=route,
            tools_called=tool_trace,
            tokens=total_tokens,
            cost=cost,
            latency=elapsed
        )

        return {
            "answer": final_answer,
            "route": route,
            "tools_called": tool_trace,
            "tokens": total_tokens,
            "cost": cost,
            "latency": round(elapsed, 3),
            "audit_run_id": run_id
        }
