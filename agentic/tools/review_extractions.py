"""
Document extraction and review tool for the SiteSense agent.

Queries structured fields extracted from delivery notes, invoices, and permits,
identifying low-confidence items flagged for the review queue.
"""

from typing import Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from agentic.tools.registry import registry
from agentic.tools.query_database import get_db_url

@registry.register(
    name="review_extractions",
    description="Query structured fields extracted from uploaded documents (delivery notes, permits, invoices) and identify low-confidence fields requiring human review.",
    parameters={
        "type": "object",
        "properties": {
            "media_id": {
                "type": "string",
                "description": "Optional UUID of the document media record."
            },
            "low_confidence_only": {
                "type": "boolean",
                "description": "If true, returns only extractions below the 0.85 confidence threshold flagged for human review."
            }
        }
    }
)
def review_extractions(media_id: str = None, low_confidence_only: bool = False) -> Dict[str, Any]:
    db_url = get_db_url()
    if not db_url:
        return {"success": False, "error": "DATABASE_URL not configured."}

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT e.id, e.media_id, e.field_name, e.value, e.confidence, e.reviewed_by, m.path AS source_doc
            FROM extractions e
            JOIN media m ON e.media_id = m.id
            WHERE 1=1
        """
        params = []
        if media_id:
            query += " AND e.media_id::text = %s"
            params.append(media_id)
        if low_confidence_only:
            query += " AND e.confidence < 0.85"

        query += " ORDER BY e.created_at DESC LIMIT 20;"

        cur.execute(query, params)
        extractions = cur.fetchall()
        cur.close()
        conn.close()

        formatted = []
        for e in extractions:
            formatted.append({
                "extraction_id": str(e["id"]),
                "field_name": e["field_name"],
                "value": e["value"],
                "confidence": float(e["confidence"]),
                "needs_human_review": float(e["confidence"]) < 0.85,
                "reviewed": e["reviewed_by"] is not None,
                "document_path": e["source_doc"]
            })

        return {
            "success": True,
            "total_extracted_fields": len(formatted),
            "extractions": formatted
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

