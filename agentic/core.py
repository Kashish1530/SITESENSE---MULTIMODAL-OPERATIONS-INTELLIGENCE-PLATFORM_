"""
SITESENSE - Agent Core Reason-Act-Observe Loop & Audit Trail (Features 4.2 & 4.11)
Executes tool-calling reasoning loop, enforces iterations/cost limits, 
and logs every interaction to the Neon DB 'agent_runs' table.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from groq import Groq
import psycopg2

# Load environment variables
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from agentic.tools import registry
from agentic.router import route_query
from agentic.guardrails import check_input_guardrail
from agentic.memory import memory
from agentic.tools.query_database import get_db_url

AGENT_SYSTEM_PROMPT = """You are SiteSense Operations Agent, an expert AI compliance auditor for physical operational facilities (retail stores, warehouses, distribution centers).

Tool Usage Guidelines:
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
    """Persists full audit trail to the Neon DB 'agent_runs' table."""
    db_url = get_db_url()
    if not db_url:
        return None

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
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
        cur.close()
        conn.close()
        return str(run_id)
    except Exception as e:
        print(f"Warning: Failed to log agent run to Neon DB: {e}")
        return None

class SiteSenseAgent:
    def __init__(self, model_name: str = None, max_iterations: int = 6):
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
        start_time = time.time()
        tool_trace = []
        total_tokens = 0

        # Step 1: Input Guardrail Check
        is_safe, guardrail_msg = check_input_guardrail(question)
        if not is_safe:
            return {
                "answer": f"Request blocked by safety guardrails: {guardrail_msg}",
                "route": "blocked",
                "tools_called": [],
                "tokens": 0,
                "cost": 0.0,
                "latency": round(time.time() - start_time, 3),
                "audit_run_id": None
            }

        # Step 2: Query Router
        router_result = route_query(question, has_image=has_image, groq_api_key=self.api_key)
        route = router_result.get("route", "general")

        # Step 3: Fast-path for simple greetings
        if route == "general" and len(question.split()) <= 4:
            answer = "Hello! I am the SiteSense Operations Agent. I can assist you with policy clauses, site inspection findings, visual detections, and compliance reports. How can I help you today?"
            latency = time.time() - start_time
            run_id = log_agent_run_to_neon(user_id, question, route, [], 35, 0.0001, latency)
            return {
                "answer": answer,
                "route": route,
                "tools_called": [],
                "tokens": 35,
                "cost": 0.0001,
                "latency": round(latency, 3),
                "audit_run_id": run_id
            }

        # Step 4: Prepare Agent Execution Context
        client = Groq(api_key=self.api_key)
        available_tools = registry.get_all_schemas()

        messages = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT}
        ]

        # Add conversation history
        history = memory.get_history(session_id)
        messages.extend(history)
        messages.append({"role": "user", "content": question})

        iteration = 0
        final_answer = ""

        # Step 5: Reason-Act-Observe Loop
        while iteration < self.max_iterations:
            iteration += 1

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=available_tools,
                tool_choice="auto",
                temperature=0.1
            )

            choice = response.choices[0]
            msg = choice.message
            if hasattr(response, "usage") and response.usage:
                total_tokens += response.usage.total_tokens

            # Check if model wants to call tools
            if msg.tool_calls:
                # Append assistant tool call message
                messages.append(msg)

                for tool_call in msg.tool_calls:
                    func_name = tool_call.function.name
                    func_args_str = tool_call.function.arguments
                    try:
                        func_args = json.loads(func_args_str)
                    except Exception:
                        func_args = {}

                    print(f"  [Agent Step {iteration}] Calling tool: {func_name} with {func_args}", flush=True)
                    # Execute the tool safely via central registry
                    tool_execution = registry.execute(func_name, func_args)
                    tool_output = json.dumps(tool_execution)

                    tool_trace.append({
                        "step": iteration,
                        "tool": func_name,
                        "arguments": func_args,
                        "result": tool_execution.get("result") or tool_execution.get("error")
                    })

                    # Feed observation back to model
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": func_name,
                        "content": tool_output
                    })
            else:
                # Agent provided final answer
                final_answer = msg.content or ""
                break

        if not final_answer and iteration >= self.max_iterations:
            final_answer = "Analysis reached iteration limit. Based on collected observations, please check the specific inspection findings or policy clauses listed in the trace."

        # Calculate cost estimation ($0.003 per 1K tokens estimate)
        cost = round((total_tokens / 1000.0) * 0.003, 6)
        latency = time.time() - start_time

        # Update session memory
        memory.add_message(session_id, "user", question)
        memory.add_message(session_id, "assistant", final_answer)

        # Step 6: Log Full Trace to Neon DB audit table (agent_runs)
        run_id = log_agent_run_to_neon(
            user_id=user_id,
            question=question,
            route=route,
            tools_called=tool_trace,
            tokens=total_tokens,
            cost=cost,
            latency=latency
        )

        return {
            "answer": final_answer,
            "route": route,
            "tools_called": tool_trace,
            "tokens": total_tokens,
            "cost": cost,
            "latency": round(latency, 3),
            "audit_run_id": run_id
        }
