"""
Policy search tool for the SiteSense agent.

Queries company safety handbooks and warehouse policies using:
1. Hybrid search engine (BM25 + pgvector Dense + RRF + Cross-Encoder reranker).
2. Structured policy clauses indexed in policy_clauses.json.
3. Strict refusal signal when no relevant clause meets the threshold.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from agentic.tools.registry import registry

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
POLICIES_JSON_PATH = PROJECT_ROOT / "policies" / "policy_clauses.json"

_hybrid_search_instance = None


def get_hybrid_search():
    """Lazy loader for the HybridSearch retrieval engine."""
    global _hybrid_search_instance
    if _hybrid_search_instance is None:
        try:
            from genai.retrieval.hybrid_search import HybridSearch
            _hybrid_search_instance = HybridSearch()
        except Exception as err:
            print(f"[PolicySearch] Could not load HybridSearch pipeline: {err}")
    return _hybrid_search_instance


@registry.register(
    name="search_policies",
    description="Search company Operations and Safety Policies (WHP-001 to WHP-020, Handbooks SHB-01 to SHB-10, Site & Warehouse Rules) for clauses, standards, and citations.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language query, topic, or CV class name (e.g. 'forklift', 'safety-helmet', 'empty-shelf', 'pallets', 'spill', 'fire-hose')."
            },
            "clause_id": {
                "type": ["string", "null"],
                "description": "Optional specific clause identifier (e.g. 'Clause S1.2', 'WHP-006', 'SHB-03')."
            },
            "policy_type": {
                "type": ["string", "null"],
                "description": "Optional filter: 'site' or 'warehouse'."
            }
        },
        "required": ["query"]
    }
)
def search_policies(query: str, clause_id: Optional[str] = None, policy_type: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves relevant policy standards and citations matching user query."""
    q_norm = query.lower().strip()
    if "safet--" in q_norm:
        q_norm = q_norm.replace("safet--", "safety-")

    hits: List[Dict[str, Any]] = []

    # 1. Query hybrid RAG engine (Dense + BM25 + Cross-Encoder)
    searcher = get_hybrid_search()
    if searcher:
        try:
            results = searcher.search(query=query, top_k=4)
            for r in results:
                # Filter out low-confidence negative rerank scores
                score = r.get("rerank_score")
                if score is not None and score < -4.0:
                    continue

                doc_id = r.get("document_id", "DOC")
                source_doc = r.get("source_file", "Policy Document")
                page = r.get("page_number", 1)
                text = r.get("text", "")
                chunk = r.get("chunk_id", "")

                hits.append({
                    "citation": f"[{doc_id}] {source_doc} (Page {page}, Chunk {chunk})",
                    "policy_document": source_doc,
                    "section": f"Page {page}",
                    "clause_id": doc_id,
                    "summary": text[:350] + "..." if len(text) > 350 else text,
                    "severity": "major",
                    "rule_type": "operational_standard",
                    "retrieval_method": "HybridSearch (BM25 + Dense + RRF + Cross-Encoder)",
                    "rrf_score": r.get("rrf_score"),
                    "rerank_score": r.get("rerank_score")
                })
        except Exception as err:
            print(f"[PolicySearch] Hybrid search encountered an error: {err}")

    # 2. Check structured clauses in JSON as complementary reference
    if POLICIES_JSON_PATH.exists():
        try:
            with open(POLICIES_JSON_PATH, "r", encoding="utf-8") as f:
                clauses: List[Dict[str, Any]] = json.load(f)

            for item in clauses:
                if clause_id and clause_id.lower() in item.get("clause_id", "").lower():
                    hits.append({
                        "citation": f"{item['clause_id']} — {item['title']} ({item.get('policy_doc', 'Policy Handbook')}, Page {item['page']})",
                        "policy_document": item.get("policy_doc", "Operations & Safety Policy"),
                        "section": item["section"],
                        "clause_id": item["clause_id"],
                        "summary": item["summary"],
                        "severity": item["severity"],
                        "rule_type": item["rule_type"],
                        "retrieval_method": "Policy Clause Index"
                    })
                    continue

                if policy_type:
                    p_lower = policy_type.lower()
                    if p_lower == "site" and "site" not in item.get("policy_doc", "").lower():
                        continue
                    if p_lower == "warehouse" and "warehouse" not in item.get("policy_doc", "").lower():
                        continue

                title_match = any(w in item["title"].lower() for w in q_norm.split() if len(w) > 2)
                summary_match = any(w in item["summary"].lower() for w in q_norm.split() if len(w) > 2)
                kw_match = any(kw in q_norm for kw in item.get("keywords", []))
                class_match = any(gc.lower() in q_norm for gc in item.get("governing_classes", []))

                if title_match or summary_match or kw_match or class_match:
                    hits.append({
                        "citation": f"{item['clause_id']} — {item['title']} ({item.get('policy_doc', 'Policy Handbook')}, Page {item['page']})",
                        "policy_document": item.get("policy_doc", "Operations & Safety Policy"),
                        "section": item["section"],
                        "clause_id": item["clause_id"],
                        "summary": item["summary"],
                        "severity": item["severity"],
                        "rule_type": item["rule_type"],
                        "retrieval_method": "Policy Clause Index"
                    })
        except Exception:
            pass

    # 3. Grounded refusal signal if nothing matched
    if not hits:
        return {
            "found": False,
            "query": query,
            "message": "No governing policy clause was found matching your query. (Refusal standard: ungrounded answers are prohibited)."
        }

    # Deduplicate citations and keep top 4
    deduped = []
    seen = set()
    for item in hits:
        cit = item["citation"]
        if cit not in seen:
            seen.add(cit)
            deduped.append(item)

    return {
        "found": True,
        "count": len(deduped[:4]),
        "results": deduped[:4]
    }
