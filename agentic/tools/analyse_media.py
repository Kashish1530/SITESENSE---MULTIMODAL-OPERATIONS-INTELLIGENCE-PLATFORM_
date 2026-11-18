"""
SITESENSE - Media & Vision Analysis Tool (Feature 4.4)
Retrieves visual evidence, detections, zones, bounding boxes, and annotated image paths.
"""

from typing import Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from agentic.tools.registry import registry
from agentic.tools.query_database import get_db_url

@registry.register(
    name="analyse_media",
    description="Retrieve visual findings, object detections, bounding boxes, zones, and annotated image paths for a site or inspection.",
    parameters={
        "type": "object",
        "properties": {
            "site_id": {
                "type": ["string", "null"],
                "description": "Optional UUID or site name (e.g. 'Site 7') to retrieve media findings for."
            },
            "inspection_id": {
                "type": ["string", "null"],
                "description": "Optional inspection UUID."
            },
            "class_name": {
                "type": ["string", "null"],
                "description": "Optional object class to filter (e.g. 'pallet', 'person', 'safety_helmet', 'spill', 'fire_extinguisher')."
            }
        }
    }
)
def analyse_media(site_id: str = None, inspection_id: str = None, class_name: str = None) -> Dict[str, Any]:
    db_url = get_db_url()
    if not db_url:
        return {"success": False, "error": "DATABASE_URL not configured."}

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT 
                s.name AS site_name,
                i.id AS inspection_id,
                i.status AS inspection_status,
                m.id AS media_id,
                m.type AS media_type,
                m.path AS media_path,
                d.id AS detection_id,
                d.class_name,
                d.bbox,
                d.confidence,
                d.zone
            FROM detections d
            JOIN media m ON d.media_id = m.id
            JOIN inspections i ON m.inspection_id = i.id
            JOIN sites s ON i.site_id = s.id
            WHERE 1=1
        """
        params = []
        if site_id:
            query += " AND (s.id::text = %s OR s.name ILIKE %s)"
            params.extend([site_id, f"%{site_id}%"])
        if inspection_id:
            query += " AND i.id::text = %s"
            params.append(inspection_id)
        if class_name:
            query += " AND d.class_name ILIKE %s"
            params.append(f"%{class_name}%")

        query += " ORDER BY d.created_at DESC LIMIT 15;"

        cur.execute(query, params)
        detections = cur.fetchall()
        cur.close()
        conn.close()

        if not detections:
            return {
                "success": True,
                "found": False,
                "message": "No visual detections found matching the given criteria."
            }

        formatted = []
        for d in detections:
            formatted.append({
                "site": d["site_name"],
                "class_name": d["class_name"],
                "confidence": float(d["confidence"]),
                "zone": d["zone"],
                "bbox_xyxy": d["bbox"],
                "media_path": d["media_path"],
                "annotated_evidence_url": f"/media/{d['media_id']}?annotated=true",
                "detection_id": str(d["detection_id"])
            })

        return {
            "success": True,
            "found": True,
            "count": len(formatted),
            "detections": formatted
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

