"""
SITESENSE - Policy Search Tool (Feature 4.5)
Retrieves relevant policy clauses with citations from the Policy Handbook.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from agentic.tools.registry import registry

POLICIES_JSON_PATH = Path(__file__).resolve().parent.parent.parent / "policies" / "policy_clauses.json"

@registry.register(
    name="search_policies",
    description="Search company Operations and Safety Policies (Site Safety Policy & Warehouse Storage Policy) for clauses, standards, and citations.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language query, topic, or CV class name (e.g. 'forklift', 'safety-helmet', 'empty-shelf', 'pallets', 'spill', 'fire-hose')."
            },
            "clause_id": {
                "type": ["string", "null"],
                "description": "Optional specific clause identifier (e.g. 'Clause S1.2', 'Clause W2.1')."
            },
            "policy_type": {
                "type": ["string", "null"],
                "description": "Optional filter: 'site' for outdoor/depot/construction sites, or 'warehouse' for indoor storage/racking facilities."
            }
        },
        "required": ["query"]
    }
)
def search_policies(query: str, clause_id: str = None, policy_type: str = None) -> Dict[str, Any]:
    if not POLICIES_JSON_PATH.exists():
        return {"found": False, "message": "Policy handbook database not found."}

    with open(POLICIES_JSON_PATH, "r", encoding="utf-8") as f:
        clauses: List[Dict[str, Any]] = json.load(f)

    results = []
    query_lower = query.lower()

    # Normalization for class aliases (e.g., safet--fire-extinguisher -> safety-fire-extinguisher)
    if "safet--" in query_lower:
        query_lower = query_lower.replace("safet--", "safety-")

    for item in clauses:
        # Match specific clause ID if provided
        if clause_id and clause_id.lower() in item.get("clause_id", "").lower():
            results.append(item)
            continue

        # Filter by policy type if requested
        if policy_type:
            p_type_lower = policy_type.lower()
            if p_type_lower == "site" and "site" not in item.get("policy_doc", "").lower():
                continue
            if p_type_lower == "warehouse" and "warehouse" not in item.get("policy_doc", "").lower():
                continue

        # Match text content, keywords, or governing CV classes
        title_match = any(word in item["title"].lower() for word in query_lower.split())
        summary_match = any(word in item["summary"].lower() for word in query_lower.split())
        keyword_match = any(kw in query_lower for kw in item.get("keywords", []))
        class_match = any(gc.lower() in query_lower for gc in item.get("governing_classes", []))

        if title_match or summary_match or keyword_match or class_match:
            results.append(item)

    if not results:
        return {
            "found": False,
            "query": query,
            "message": "No governing policy clause was found matching your query. (Refusal standard: ungrounded answers are prohibited)."
        }

    formatted = []
    for r in results[:4]:
        formatted.append({
            "citation": f"{r['clause_id']} — {r['title']} ({r.get('policy_doc', 'Policy Handbook')}, Page {r['page']})",
            "policy_document": r.get("policy_doc", "Operations & Safety Policy"),
            "section": r["section"],
            "clause_id": r["clause_id"],
            "summary": r["summary"],
            "severity": r["severity"],
            "rule_type": r["rule_type"],
            "governing_classes": r.get("governing_classes", [])
        })

    return {
        "found": True,
        "count": len(formatted),
        "results": formatted
    }

