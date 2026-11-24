"""
Query router for SiteSense.

Classifies incoming questions to pick the best execution pathway:
  - 'vision'     : detections, bounding boxes, cameras, physical site evidence
  - 'policy'     : handbooks, safety rules, compliance clauses, citations
  - 'database'   : SQL counts, aggregations, cross-site stats, history
  - 'multimodal' : user attached an inspection photo
  - 'hybrid'     : requires checking policy rules against actual site observations
  - 'general'    : standard conversational greetings / pleasantries
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from groq import Groq

# Load environment configuration
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

ROUTER_PROMPT = """You are the query router for the SiteSense facility compliance platform.
Analyze the user's question and categorize it into one of these routes:

1. 'multimodal': An image is attached to the request, asking if what is shown is compliant or acceptable.
2. 'vision': Questions about what was seen, detected, filmed, photographed, or placed at a physical site (e.g. 'what was detected at Site 7?', 'is there a pallet in the walkway?', 'show me the detection photo').
3. 'policy': Questions about company compliance handbook, safety rules, PPE standards, clearance thresholds, or citations (e.g. 'what is the walkway clearance rule?', 'what does Clause 2.1 say?', 'can we stack pallets 3 meters high?').
4. 'database': Quantitative, cross-site, aggregate, or historical data questions (e.g. 'how many sites failed last month?', 'list all inspections for Site 7', 'which rule fails most frequently?').
5. 'hybrid': Questions that explicitly demand combining a policy clause with actual site observations or evidence (e.g. 'Did Site 7 pass the walkway clearance rule this week, and show me the evidence?').
6. 'general': Simple greetings, conversational pleasantries, or queries that need no tools.

Respond ONLY with valid JSON in this exact shape:
{"route": "<one of: vision, policy, database, multimodal, hybrid, general>", "confidence": <float between 0 and 1>, "reasoning": "<brief explanation>"}
"""


def route_query(question: str, has_image: bool = False, groq_api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Determines query route and confidence score.
    Uses fast-path heuristics for images and greetings, and calls Groq for semantic classification.
    """
    # If an image was attached by user, immediately route to multimodal
    if has_image:
        return {
            "route": "multimodal",
            "confidence": 0.99,
            "reasoning": "Image is attached to user question; requires multimodal visual analysis."
        }

    q = question.lower().strip()

    # Short greeting shortcut - saves an LLM roundtrip
    greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "thanks", "thank you"]
    if any(q.startswith(g) for g in greetings) and len(q.split()) <= 4:
        return {
            "route": "general",
            "confidence": 0.98,
            "reasoning": "Standard conversational greeting."
        }

    api_key = groq_api_key or os.getenv("GROQ_API_KEY")
    
    # Offline keyword heuristics fallback (in case API key is missing or offline)
    if not api_key:
        if any(w in q for w in ["clause", "rule says", "policy", "handbook", "standard", "regulation", "permitted"]):
            if any(w in q for w in ["site", "detected", "evidence", "yesterday", "passed", "failed"]):
                return {"route": "hybrid", "confidence": 0.85, "reasoning": "Heuristic match: combines policy with site findings."}
            return {"route": "policy", "confidence": 0.88, "reasoning": "Heuristic match: policy question."}
        if any(w in q for w in ["how many", "count", "average", "total sites", "list all", "ranking", "most often"]):
            return {"route": "database", "confidence": 0.90, "reasoning": "Heuristic match: statistical database query."}
        if any(w in q for w in ["detected", "seen", "camera", "photo", "pallet", "box", "spill", "zone", "walkway"]):
            return {"route": "vision", "confidence": 0.85, "reasoning": "Heuristic match: vision detections query."}
        return {"route": "general", "confidence": 0.70, "reasoning": "Default heuristic route."}

    # Model classification
    try:
        client = Groq(api_key=api_key)
        model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        resp = client.chat.completions.create(
            messages=[
                {"role": "system", "content": ROUTER_PROMPT},
                {"role": "user", "content": f"User question: {question}"}
            ],
            model=model,
            response_format={"type": "json_object"},
            temperature=0.0
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as err:
        # Fallback if network or rate limit hiccup occurs
        return {
            "route": "hybrid",
            "confidence": 0.75,
            "reasoning": f"Router API fallback due to: {str(err)}"
        }
