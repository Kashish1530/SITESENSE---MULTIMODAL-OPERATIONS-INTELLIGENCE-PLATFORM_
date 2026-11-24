"""
api_service.py  — SiteSense Member 2  (v2 — Violation Lifecycle Edition)
FastAPI Microservice.

Endpoints:
  GET  /                              Health check
  POST /vision/analyze-video          Run pipeline + auto-insert violations to DB
  GET  /vision/events/{site_id}       Fetch raw events log (for Member 3 / GenAI)

  — Violation Lifecycle —
  GET  /vision/violations/active                Active violations (filterable)
  GET  /vision/violations/resolved              Resolved violations (filterable by week)
  GET  /vision/violations/weekly-summary        Per-week stats
  GET  /vision/violations/{violation_id}        Single record + resolution proof
  POST /vision/violations/resolve               Mark violation resolved + upload proof photo
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Response
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import json
import shutil
import cv2
from pathlib import Path

import sys
sys.path.append(os.path.abspath("src"))
from pipeline import run_site_analytics
from annotator import VisualAnnotator
from zone_validator import ZoneConfigValidator, get_zone_config_json_schema
from violation_db import (
    init_db, insert_violation, resolve_violation,
    get_active_violations, get_resolved_violations,
    get_violation_by_id, get_weekly_summary, get_all_violations_count
)

# Bootstrap DB at startup
init_db()

app = FastAPI(
    title="SiteSense Vision Analytics API",
    description=(
        "Video tracking, zone spatial intelligence, blockage hazard detection, "
        "and violation lifecycle management microservice — Member 2"
    ),
    version="2.0.0"
)

# ── Schemas ───────────────────────────────────────────────────────────────────

DEFAULT_MODEL = "models/best_3.pt" if os.path.exists("models/best_3.pt") else "models/best.pt"

class VideoAnalysisRequest(BaseModel):
    video_path:          str
    zones_config_path:   Optional[str]  = "config/zones_warehouse.json"
    model_weights:       Optional[str]  = DEFAULT_MODEL
    site_id:             Optional[str]  = "SITE_01"
    save_annotated_video: Optional[bool] = True
    max_frames:          Optional[int]  = None


class VideoAnalysisResponse(BaseModel):
    status:                 str
    site_id:                str
    total_frames_processed: int
    total_events_emitted:   int
    unique_person_count:    int = 0
    unique_counts_by_class: Dict[str, int] = {}
    events_log_file:        str
    annotated_video_path:   Optional[str] = None
    summary_violations:     List[Dict[str, Any]]
    db_violation_ids:       List[str]


class ResolveViolationRequest(BaseModel):
    violation_id:    str
    resolved_by:     Optional[str] = "site_supervisor"
    resolution_note: Optional[str] = ""


class DynamicZoneConfigPayload(BaseModel):
    site_id: Optional[str] = None
    site_name: Optional[str] = "SiteSense Managed Facility"
    site_type: Optional[str] = "warehouse"
    camera_id: Optional[str] = "CAM_01"
    resolution: Optional[List[int]] = [1280, 720]
    zones: Dict[str, Any]
    counting_lines: Optional[Dict[str, Any]] = {}


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/")
def health_check():
    stats = get_all_violations_count()
    return {
        "service": "SiteSense Video Analytics & Spatial Engine",
        "status":  "RUNNING",
        "version": "2.0.0",
        "db_stats": stats,
        "supported_features": [
            "2.3 Video Tracking (ByteTrack + YOLOv11)",
            "2.4 Zone Engine (Dwell Timer, Counting Lines)",
            "Exit Blockage Detection",
            "Dynamic Zone Configuration (Admin Screen 12 - M6.9)",
            "Violation Lifecycle Management (Store → Resolve → Progress)"
        ]
    }


# ── Video Analysis ─────────────────────────────────────────────────────────────

@app.post("/vision/analyze-video", response_model=VideoAnalysisResponse)
def analyze_video_endpoint(req: VideoAnalysisRequest):
    """
    Executes Member 2 video analytics pipeline.
    Returns structured spatial events + auto-inserts unique violations into DB.
    """
    if not os.path.exists(req.video_path):
        raise HTTPException(404, f"Video not found: {req.video_path}")
    if not os.path.exists(req.zones_config_path):
        raise HTTPException(404, f"Zones config not found: {req.zones_config_path}")

    try:
        events = run_site_analytics(
            video_path=req.video_path,
            zones_config_path=req.zones_config_path,
            model_weights=req.model_weights,
            site_id=req.site_id,
            output_dir="outputs",
            show_display=False,
            save_annotated_video=req.save_annotated_video,
            max_frames=req.max_frames
        )

        video_stem     = Path(req.video_path).stem
        annotated_video = f"outputs/annotated_videos/{video_stem}_annotated.mp4"
        log_file        = f"outputs/events/site_{req.site_id}_events.json"

        # Unique violations summary + DB insert
        summary       = []
        db_ids        = []
        seen          = set()
        inserted_keys = {}

        for e in events:
            sig = (e["event_type"], e["target"]["track_id"], e["zone_name"])
            if sig not in seen:
                seen.add(sig)
                summary.append(e)

                # Only persist HIGH/CRITICAL events
                if e.get("severity") in ["HIGH", "CRITICAL"]:
                    track_key = (e["zone_id"], e["target"]["track_id"])
                    if track_key not in inserted_keys:
                        db_id = insert_violation(
                            e,
                            evidence_path=None,
                            video_name=Path(req.video_path).name
                        )
                        inserted_keys[track_key] = db_id
                        db_ids.append(db_id)

        # Extract executive tracking stats (Feature 2.3)
        summary_meta = getattr(events, "summary", {})
        unique_person_count = summary_meta.get("unique_person_count", 0)
        raw_class_counts = summary_meta.get("unique_counts_by_class", {})
        unique_counts_by_class = {
            VisualAnnotator.CLASS_NAMES.get(int(k), str(k)): v
            for k, v in raw_class_counts.items()
        }
        total_frames = summary_meta.get("total_frames_processed", len(events))

        return VideoAnalysisResponse(
            status="SUCCESS",
            site_id=req.site_id,
            total_frames_processed=total_frames,
            total_events_emitted=len(events),
            unique_person_count=unique_person_count,
            unique_counts_by_class=unique_counts_by_class,
            events_log_file=log_file,
            annotated_video_path=annotated_video if os.path.exists(annotated_video) else None,
            summary_violations=summary,
            db_violation_ids=db_ids
        )

    except Exception as exc:
        raise HTTPException(500, f"Vision Pipeline Error: {str(exc)}")


# ── Dynamic Zone Configuration (Admin Screen 12 - M6.9) ───────────────────────

@app.get("/vision/zones/schema")
def get_zones_schema():
    """
    Returns the authoritative JSON Schema specification for SiteSense zone configs.
    Used by Frontend / Admin Zone Editor form generator (Screen 12 - M6.9).
    """
    return get_zone_config_json_schema()


@app.post("/vision/zones/validate")
def validate_zone_configuration(payload: DynamicZoneConfigPayload):
    """
    Validates candidate zone polygons and parameters without persisting to disk.
    Used by Admin Zone Editor for instant UI feedback before saving.
    """
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    is_valid, errors, sanitized = ZoneConfigValidator.validate(data)
    return {
        "valid": is_valid,
        "errors": errors,
        "zones_count": len(sanitized.get("zones", {})),
        "sanitized_config": sanitized if is_valid else None
    }


@app.get("/vision/zones/{site_id}")
def get_site_zones(site_id: str):
    """
    Fetches active zone polygons and counting line configurations for a site.
    Used by Admin Zone Editor (Screen 12 - M6.9).
    """
    config_candidates = [
        f"config/zones_{site_id.lower()}.json",
        f"config/zones_{site_id}.json",
        "config/zones_warehouse.json" if "warehouse" in site_id.lower() else "config/zones_construction.json"
    ]
    for path in config_candidates:
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
    raise HTTPException(404, f"No zone configuration found for site '{site_id}'")


@app.post("/vision/zones/{site_id}")
def update_site_zones(site_id: str, payload: DynamicZoneConfigPayload):
    """
    Saves/Updates dynamic zone polygons created by Admin in Screen 12 (M6.9).
    Validates polygon geometry, class mappings, and dwell timers to guarantee
    zero runtime crashes, and hot-reloads the configuration without restarting services.
    """
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    data["site_id"] = site_id

    # Strict validation before saving
    is_valid, errors, sanitized = ZoneConfigValidator.validate(data)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "VALIDATION_FAILED",
                "message": "Zone configuration geometry or parameters failed validation.",
                "errors": errors
            }
        )

    os.makedirs("config", exist_ok=True)
    save_path = f"config/zones_{site_id.lower()}.json"
    with open(save_path, "w") as f:
        json.dump(sanitized, f, indent=2)

    return {
        "status": "SUCCESS",
        "site_id": site_id,
        "zones_saved": len(sanitized["zones"]),
        "config_file": save_path,
        "message": f"Successfully validated and saved {len(sanitized['zones'])} zones for site '{site_id}'."
    }


@app.get("/vision/camera/{site_id}/reference-frame")
def get_camera_reference_frame(site_id: str, video_path: Optional[str] = None):
    """
    Returns a JPEG snapshot from the site's camera feed so the Admin Zone Editor
    (Screen 12) can display the background frame for polygon drawing.
    """
    target_video = video_path
    if not target_video or not os.path.exists(target_video):
        candidates = [
            f"data/sample_videos/{site_id.lower()}.mp4",
            "data/sample_videos/warehouse1.mp4" if "warehouse" in site_id.lower() else "data/sample_videos/constructionsite1.mp4"
        ]
        for c in candidates:
            if os.path.exists(c):
                target_video = c
                break

    if not target_video or not os.path.exists(target_video):
        raise HTTPException(404, f"No video source found to extract frame for site '{site_id}'")

    cap = cv2.VideoCapture(target_video)
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        raise HTTPException(500, f"Failed to extract frame from {target_video}")

    success, encoded_img = cv2.imencode(".jpg", frame)
    if not success:
        raise HTTPException(500, "Failed to encode frame to JPEG")

    return Response(content=encoded_img.tobytes(), media_type="image/jpeg")


# ── Events (Legacy / Member 3 compat) ─────────────────────────────────────────

@app.get("/vision/events/{site_id}")
def get_site_events(site_id: str):
    """Called by Member 3 (Compliance Engine) and GenAI Agent 'analyse_media' tool."""
    log_file = f"outputs/events/site_{site_id}_events.json"
    if not os.path.exists(log_file):
        raise HTTPException(404, f"No events log for site: {site_id}")
    with open(log_file) as f:
        data = json.load(f)
    return {"site_id": site_id, "total_events": len(data), "events": data}


# ── Violation Lifecycle Endpoints ──────────────────────────────────────────────

@app.get("/vision/violations/active")
def get_active(site_id: Optional[str] = None, zone_id: Optional[str] = None):
    """
    Returns all ACTIVE (unresolved) violations.
    GenAI Tool: 'Show active violations on site X'
    """
    rows = get_active_violations(site_id=site_id, zone_id=zone_id)
    return {
        "status":  "SUCCESS",
        "count":   len(rows),
        "violations": rows
    }


@app.get("/vision/violations/resolved")
def get_resolved(site_id: Optional[str] = None, week: Optional[int] = None):
    """
    Returns all RESOLVED violations (filterable by site and ISO week number).
    GenAI Tool: 'Show resolved violations this week'
    """
    rows = get_resolved_violations(site_id=site_id, week=week)
    return {
        "status":  "SUCCESS",
        "count":   len(rows),
        "violations": rows
    }


@app.get("/vision/violations/weekly-summary")
def weekly_summary_endpoint(site_id: Optional[str] = None):
    """Per-week breakdown of total / active / resolved counts."""
    rows = get_weekly_summary(site_id=site_id)
    return {"status": "SUCCESS", "weekly_summary": rows}


@app.get("/vision/violations/{violation_id}")
def get_one_violation(violation_id: str):
    """
    Fetch a single violation record + its resolution proof (if resolved).
    GenAI Tool: 'Get details for violation VID-XXXX'
    """
    row = get_violation_by_id(violation_id)
    if not row:
        raise HTTPException(404, f"Violation not found: {violation_id}")
    return {"status": "SUCCESS", "violation": row}


@app.post("/vision/violations/resolve")
async def resolve_violation_endpoint(
    violation_id:    str  = Form(...),
    resolved_by:     str  = Form("site_supervisor"),
    resolution_note: str  = Form(""),
    proof_photo:     Optional[UploadFile] = File(None)
):
    """
    Mark a violation as RESOLVED.
    Accepts multipart form: violation_id, resolved_by, resolution_note, proof_photo (file).
    GenAI Tool: 'Resolve violation VID-XXXX — obstacle removed'
    """
    photo_save_path = None

    if proof_photo is not None:
        os.makedirs("outputs/resolution_proofs", exist_ok=True)
        safe_name = f"RESOLVED_{violation_id[:8]}_{proof_photo.filename}"
        photo_save_path = os.path.abspath(f"outputs/resolution_proofs/{safe_name}")
        with open(photo_save_path, "wb") as out:
            shutil.copyfileobj(proof_photo.file, out)

    success = resolve_violation(
        violation_id=violation_id,
        resolved_by=resolved_by,
        resolution_photo_path=photo_save_path,
        resolution_note=resolution_note
    )

    if not success:
        raise HTTPException(404, f"Violation not found or already resolved: {violation_id}")

    return {
        "status":        "RESOLVED",
        "violation_id":  violation_id,
        "resolved_by":   resolved_by,
        "proof_stored":  photo_save_path,
        "message":       "Violation marked resolved. Alert discarded. Record preserved."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_service:app", host="0.0.0.0", port=8000, reload=True)
