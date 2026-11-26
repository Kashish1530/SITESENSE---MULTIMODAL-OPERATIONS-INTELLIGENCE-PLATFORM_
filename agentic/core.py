"""
SiteSense Operations Agent - Core Runtime.

Orchestrates the ReAct (Reason-Act-Observe) loop using Groq function calling,
delegates tasks to registered domain tools, and records full audit traces
to the Postgres 'agent_runs' table.
"""

import os
import re
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from groq import Groq
import psycopg2

# Load environment configuration (root .env and backend/.env)
_ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT_DIR / "backend" / ".env")
load_dotenv(_ROOT_DIR / ".env")

from agentic.tools import registry
from agentic.router import route_query
from agentic.guardrails import check_input_guardrail
from agentic.memory import memory
from agentic.tools.query_database import get_db_url

# Integration with GenAI Module 3 (Prompt Management & Semantic Caching)
try:
    from genai.prompts.prompt_manager import prompt_manager
    AGENT_PROMPT = prompt_manager.get_prompt("agent_system", "v1.0")
except Exception:
    AGENT_PROMPT = """You are SiteSense Operations Agent, an expert AI operations and compliance supervisor for physical facilities (warehouses, retail centers, construction sites).

Your Capabilities:
- Auditing visual media (images, videos) for PPE adherence (helmets, high-vis vests), forklift-pedestrian clearance, and walkway obstructions.
- Answering questions about governing company policies (WHP-001 through WHP-020, SHB-01 through SHB-08) with exact clause citations.
- Ingesting and verifying user-uploaded site policies and safety handbooks (PDFs) with highest precedence.
- Querying live facility operational databases for inspection records, fail rates, and site metrics safely.
- Drafting and managing remediation tickets held by the human approval gate.
- Generating formal compliance audit reports (REP-XXXXXX).

What You CANNOT Do (Your Operational Boundaries):
- You cannot unilaterally activate or dispatch critical safety tickets without explicit human supervisor sign-off (Human Approval Gate).
- You cannot execute destructive database commands (DROP, DELETE, UPDATE, INSERT) — database access is strictly read-only.
- You cannot bypass security guardrails, reveal system credentials, or ignore safety protocols.
- You cannot visually inspect physical scenes without submitted photos, videos, or camera data.

Guidelines for Conversational & General Questions:
- If the user asks about your identity ("what are you?", "who are you?"), describe your role as SiteSense Operations Agent and explain what you can do.
- If the user asks about your limitations ("what can't you do?", "what are your limits?"), clearly outline your operational boundaries (human approval gate, read-only safety, security guardrails).
- For general questions that do not require tool calls, respond conversationally, concisely, and directly.

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
5. `generate_report`: Generate comprehensive evidence-linked compliance reports exportable as PDF.
6. `review_extractions`: Query extracted fields from delivery notes and invoices requiring human review.

Formatting Rules for Tables and Markdown:
- Whenever generating tabular data (such as worker detections, PPE compliance status, database tables, or violation counts), ALWAYS use standard multi-line Markdown tables with every row on its own line:
| Header 1 | Header 2 | Header 3 |
| :--- | :--- | :--- |
| Val 1 | Val 2 | Val 3 |
- NEVER output table rows squashed onto a single line separated by `| |`. Each row MUST have a newline before and after it.
- Precede and follow every table with an empty blank line.

Rules for your answers:
- Always cite the exact Policy Clause (e.g., 'Clause 4.1' or 'Clause 4.2').
- If an inspection failed or passed, state the exact status ('pass', 'fail', 'review') and reference the evidence.
- Synthesize your final answer concisely once you have the policy and site findings. Do not call redundant queries.
"""

try:
    from genai.caching.cache_manager import cache_manager
except Exception:
    cache_manager = None


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

    def __init__(self, model_name: Optional[str] = None, max_iterations: int = 4):
        self.model_name = model_name or os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
        self.max_iterations = max_iterations
        self.api_key = os.getenv("GROQ_API_KEY")

    def run(
        self,
        question: str,
        session_id: str = "default_session",
        user_id: Optional[str] = None,
        has_image: bool = False,
        use_cache: bool = True,
        user_role: Optional[str] = "admin"
    ) -> Dict[str, Any]:
        """
        Executes the agentic workflow:
        1. Checks input guardrails for prompt injections or malicious commands.
        2. Consults GenAI semantic/exact cache for repeated queries (Feature 3.10).
        3. Routes the query to find the best domain path.
        4. Drives the iterative Reason-Act-Observe tool loop until complete.
        5. Saves session turns and logs execution telemetry to Postgres.
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

        # Check GenAI Semantic / Exact Request Cache (Feature 3.10)
        if use_cache and cache_manager:
            hit, cached_data, match_type = cache_manager.get(question)
            if hit and cached_data:
                return {
                    "answer": cached_data.get("answer", ""),
                    "route": cached_data.get("route", "cached"),
                    "tools_called": cached_data.get("tools_called", []),
                    "tokens": 0,
                    "cost": 0.0,
                    "latency": 0.002,
                    "audit_run_id": cached_data.get("audit_run_id"),
                    "cache_hit": True,
                    "cache_match_type": match_type
                }

        # Route query
        routing = route_query(question, has_image=has_image, groq_api_key=self.api_key)
        route = routing.get("route", "general")

        # Role-Based Access Control (RBAC): Database queries restricted to Admin, Supervisor, and Super Admin
        role_clean = (user_role or "field").lower().strip()
        allowed_db_roles = {"admin", "super_admin", "supervisor", "manager"}
        db_keywords = ["database", "audit_log", "audit log", "table", "sql query", "select from", "records from", "show me data", "give me data", "data of"]
        is_db_query = route == "database" or any(kw in question.lower() for kw in db_keywords)

        if is_db_query and role_clean not in allowed_db_roles:
            refusal_msg = (
                f"### Access Denied: Database Access Restricted\n\n"
                f"🔒 **Permission Required:** Direct database inspection, table queries, and audit log retrieval are strictly restricted to **Admin**, **Supervisor**, and **Super Admin** personnel.\n\n"
                f"Your current account role is `{user_role or 'field'}`. Access to database tables and raw system records is denied."
            )
            elapsed = time.time() - start_time
            run_id = log_agent_run_to_neon(user_id, question, "blocked", [], 25, 0.0001, elapsed)
            return {
                "answer": refusal_msg,
                "route": "blocked",
                "tools_called": [],
                "tokens": 25,
                "cost": 0.0001,
                "latency": round(elapsed, 3),
                "audit_run_id": run_id
            }

        # Early exit strictly for literal greetings (e.g. 'hi', 'hello', 'hey')
        q_clean = question.lower().strip().rstrip("!?.,")
        pure_greetings = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening", "howdy", "greetings"}
        if route == "general" and q_clean in pure_greetings:
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

            response = None
            models_to_try = [self.model_name]
            for fb in ["openai/gpt-oss-20b", "qwen/qwen3.8-27b"]:
                if fb not in models_to_try:
                    models_to_try.append(fb)

            last_err = None
            for m in models_to_try:
                try:
                    response = client.chat.completions.create(
                        model=m,
                        messages=messages,
                        tools=schemas,
                        tool_choice="auto",
                        temperature=0.1
                    )
                    break
                except Exception as call_err:
                    last_err = call_err
                    if "429" in str(call_err) or "rate_limit" in str(call_err).lower():
                        print(f"  [RateLimit Warning] Model {m} hit rate limit, falling back...", flush=True)
                        continue
                    raise call_err

            if response is None:
                if last_err:
                    raise last_err
                raise RuntimeError("All Groq models unavailable.")

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
                    
                    # Check RBAC for query_database tool
                    if fn_name == "query_database" and role_clean not in allowed_db_roles:
                        exec_result = {
                            "success": False,
                            "error": f"Permission Denied: User role '{user_role}' is not authorized to execute database queries. Only Admin, Supervisor, and Super Admin can query the database."
                        }
                    else:
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

                    # Performance optimization: For policy, multimodal, or hybrid queries, once governing clauses are retrieved, synthesize immediately
                    if route in ["policy", "multimodal", "hybrid"] and fn_name == "search_policies" and exec_result.get("result", {}).get("found"):
                        try:
                            synth_prompt = (
                                "Based on the governing policy standards retrieved above, provide a comprehensive, well-structured compliance answer with exact policy citations. "
                                "Format key requirements clearly with bold titles and exact measurements. Do NOT output any XML or <tool_call> tags."
                            )
                            synth_resp = client.chat.completions.create(
                                model=self.model_name,
                                messages=messages + [{"role": "user", "content": synth_prompt}],
                                temperature=0.1
                            )
                            raw_synth = (synth_resp.choices[0].message.content or "").strip()
                            raw_synth = re.sub(r'<tool_call>[\s\S]*?</tool_call>', '', raw_synth).strip()
                            raw_synth = re.sub(r'<function=[\s\S]*?</function>', '', raw_synth).strip()
                            if raw_synth:
                                final_answer = raw_synth
                                break
                        except Exception:
                            pass
                
                if final_answer:
                    break
            else:
                # Agent concluded reasoning
                final_answer = (msg.content or "").strip()
                final_answer = re.sub(r'<tool_call>[\s\S]*?</tool_call>', '', final_answer).strip()
                if not final_answer and tool_trace:
                    # Final synthesis from collected observations
                    try:
                        synth_prompt = (
                            "Please provide your final concise answer and citation to the user based on the tool observations above. Do NOT output any <tool_call> tags."
                        )
                        synth_resp = client.chat.completions.create(
                            model=self.model_name,
                            messages=messages + [{"role": "user", "content": synth_prompt}],
                            temperature=0.1
                        )
                        final_answer = (synth_resp.choices[0].message.content or "").strip()
                        final_answer = re.sub(r'<tool_call>[\s\S]*?</tool_call>', '', final_answer).strip()
                    except Exception:
                        pass
                break

        # Fallback if iterations exhausted but observations exist
        if not final_answer and tool_trace:
            try:
                synth_resp = client.chat.completions.create(
                    model=self.model_name,
                    messages=messages + [{"role": "user", "content": "Synthesize a clear summary answer and policy citations from the findings above. Do NOT output any <tool_call> tags."}],
                    temperature=0.1
                )
                final_answer = (synth_resp.choices[0].message.content or "").strip()
                final_answer = re.sub(r'<tool_call>[\s\S]*?</tool_call>', '', final_answer).strip()
            except Exception:
                pass

        if not final_answer:
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

        result_payload = {
            "answer": final_answer,
            "route": route,
            "tools_called": tool_trace,
            "tokens": total_tokens,
            "cost": cost,
            "latency": round(elapsed, 3),
            "audit_run_id": run_id
        }

        # Cache result in GenAI Semantic Cache
        if use_cache and cache_manager and final_answer:
            try:
                cache_manager.put(question, result_payload, cost=cost, latency=elapsed)
            except Exception:
                pass

        return result_payload
