"""
SITESENSE - Inspection & Upload Router (Feature 1.1, 1.2, 1.3, API Contract)
Endpoints:
  - POST /inspections       : Multi-format upload (images, video, documents), returns job_id < 2s
  - GET  /jobs/{job_id}     : Poll asynchronous processing status
  - GET  /inspections       : Filterable list of inspections with pass rates
  - GET  /inspections/{id}  : Detailed inspection view with media, detections, and findings
"""

import os
import uuid
import json
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException, Query
from dotenv import load_dotenv

from storage.metadata_extractor import extract_image_metadata
from api.jobs_manager import job_manager

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
DATABASE_URL = os.getenv("DATABASE_URL")

router = APIRouter(tags=["Inspections"])

UPLOAD_ROOT = Path(__file__).resolve().parent.parent.parent / "storage" / "uploads"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {
    "image": [".jpg", ".jpeg", ".png", ".webp"],
    "video": [".mp4", ".mov", ".avi", ".mkv"],
    "doc": [".pdf", ".docx", ".doc", ".png", ".jpg"]
}

def get_file_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    for ftype, extensions in ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            return ftype
    return "doc"

@router.post("/inspections", status_code=202)
async def create_inspection_and_upload(
    background_tasks: BackgroundTasks,
    site_id: str = Form(...),
    user_id: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    files: List[UploadFile] = File(...)
):
    """
    Feature 1.1 & 1.2: Multi-format upload.
    Accepts images, videos, and documents tied to a site and user.
    Extracts metadata (timestamp, GPS, device), saves files, creates inspection,
    and returns immediately (<2s) with job_id for async processing.
    """
    if not files:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "EMPTY_FILES", "message": "No files provided in upload."}}
        )

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 1. Verify Site exists
    cur.execute("SELECT id, name FROM sites WHERE id::text = %s OR name ILIKE %s LIMIT 1;", (site_id, f"%{site_id}%"))
    site_row = cur.fetchone()
    if not site_row:
        cur.close()
        conn.close()
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "SITE_NOT_FOUND", "message": f"Site '{site_id}' does not exist."}}
        )
    actual_site_id = str(site_row["id"])

    # 2. Default user if not provided
    if not user_id:
        cur.execute("SELECT id FROM users WHERE role = 'field' LIMIT 1;")
        u_row = cur.fetchone()
        user_id = str(u_row["id"]) if u_row else None

    # 3. Create Inspection record
    inspection_id = str(uuid.uuid4())
    job_id = job_manager.create_job(result_id=inspection_id)

    cur.execute("""
        INSERT INTO inspections (id, site_id, user_id, status, job_id)
        VALUES (%s, %s, %s, 'queued', %s)
        RETURNING id;
    """, (inspection_id, actual_site_id, user_id, job_id))

    # 4. Save files and extract metadata
    insp_folder = UPLOAD_ROOT / inspection_id
    insp_folder.mkdir(parents=True, exist_ok=True)

    for upload_file in files:
        orig_name = upload_file.filename
        file_type = get_file_type(orig_name)
        save_path = insp_folder / orig_name

        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)

        # Extract metadata
        meta = {
            "original_filename": orig_name,
            "site_id": actual_site_id,
            "user_id": user_id,
            "uploaded_at": datetime.utcnow().isoformat() + "Z"
        }

        if file_type == "image":
            img_meta = extract_image_metadata(
                str(save_path),
                site_id=actual_site_id,
                user_id=str(user_id),
                fallback_lat=latitude,
                fallback_lng=longitude
            )
            meta.update(img_meta)

        # Save media row in Neon DB
        media_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO media (id, inspection_id, type, path, metadata)
            VALUES (%s, %s, %s, %s, %s);
        """, (media_id, inspection_id, file_type, str(save_path), json.dumps(meta)))

    cur.close()
    conn.close()

    # 5. Dispatch async processing job to background worker
    background_tasks.add_task(job_manager.process_inspection_async, job_id, inspection_id)

    return {
        "inspection_id": inspection_id,
        "job_id": job_id,
        "status": "queued"
    }

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Feature 1.3: Poll asynchronous processing status.
    Returns status: queued -> processing -> completed | failed.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "JOB_NOT_FOUND", "message": f"Job '{job_id}' not found."}}
        )

    return {
        "status": job["status"],
        "progress": job["progress"],
        "result_id": job.get("result_id"),
        "error": job.get("error")
    }

@router.get("/inspections/{id}")
async def get_inspection_detail(id: str):
    """
    API Contract: GET /inspections/{id}
    Returns full inspection with media[], detections[], extractions[], and findings[].
    """
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT i.id, i.site_id, s.name AS site_name, s.location, i.user_id, u.name AS inspector_name, 
               i.status, i.job_id, i.created_at
        FROM inspections i
        JOIN sites s ON i.site_id = s.id
        LEFT JOIN users u ON i.user_id = u.id
        WHERE i.id::text = %s;
    """, (id,))
    insp = cur.fetchone()

    if not insp:
        cur.close()
        conn.close()
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "INSPECTION_NOT_FOUND", "message": f"Inspection '{id}' not found."}}
        )

    # Fetch Media
    cur.execute("SELECT id, type, path, metadata, created_at FROM media WHERE inspection_id::text = %s;", (id,))
    media = cur.fetchall()

    # Fetch Detections
    cur.execute("""
        SELECT d.id, d.media_id, d.class_name, d.bbox, d.confidence, d.zone, d.frame_no, d.created_at
        FROM detections d
        JOIN media m ON d.media_id = m.id
        WHERE m.inspection_id::text = %s;
    """, (id,))
    detections = cur.fetchall()

    # Fetch Extractions
    cur.execute("""
        SELECT e.id, e.media_id, e.field_name, e.value, e.confidence, e.reviewed_by
        FROM extractions e
        JOIN media m ON e.media_id = m.id
        WHERE m.inspection_id::text = %s;
    """, (id,))
    extractions = cur.fetchall()

    # Fetch Findings & Rules
    cur.execute("""
        SELECT f.id, f.rule_id, r.name AS rule_name, r.policy_ref, f.status, f.evidence_ids, f.created_at
        FROM findings f
        JOIN rules r ON f.rule_id = r.id
        WHERE f.inspection_id::text = %s;
    """, (id,))
    findings = cur.fetchall()

    cur.close()
    conn.close()

    return {
        "inspection": {
            "id": str(insp["id"]),
            "site": insp["site_name"],
            "location": insp["location"],
            "inspector": insp["inspector_name"],
            "status": insp["status"],
            "created_at": str(insp["created_at"])
        },
        "media": [{k: str(v) if k == "id" else v for k, v in m.items()} for m in media],
        "detections": [{k: str(v) if "id" in k else v for k, v in d.items()} for d in detections],
        "extractions": [{k: str(v) if "id" in k else v for k, v in e.items()} for e in extractions],
        "findings": [{k: str(v) if "id" in k else v for k, v in f.items()} for f in findings]
    }

@router.get("/inspections")
async def list_inspections(
    site_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    API Contract: GET /inspections?site_id&status&limit&offset
    Returns [{id, site, date, status, pass_rate}].
    """
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT i.id, s.name AS site, i.created_at AS date, i.status,
               COUNT(f.id) AS total_findings,
               COUNT(CASE WHEN f.status = 'pass' THEN 1 END) AS passed_findings
        FROM inspections i
        JOIN sites s ON i.site_id = s.id
        LEFT JOIN findings f ON i.id = f.inspection_id
        WHERE 1=1
    """
    params = []
    if site_id:
        query += " AND (s.id::text = %s OR s.name ILIKE %s)"
        params.extend([site_id, f"%{site_id}%"])
    if status:
        query += " AND i.status = %s"
        params.append(status)

    query += " GROUP BY i.id, s.name, i.created_at, i.status ORDER BY i.created_at DESC LIMIT %s OFFSET %s;"
    params.extend([limit, offset])

    cur.execute(query, params)
    rows = cur.fetchall()

    result = []
    for r in rows:
        total = r["total_findings"] or 0
        passed = r["passed_findings"] or 0
        rate = f"{(passed / total * 100):.0f}%" if total > 0 else "N/A"

        result.append({
            "id": str(r["id"]),
            "site": r["site"],
            "date": str(r["date"]),
            "status": r["status"],
            "pass_rate": rate
        })

    cur.close()
    conn.close()
    return result
