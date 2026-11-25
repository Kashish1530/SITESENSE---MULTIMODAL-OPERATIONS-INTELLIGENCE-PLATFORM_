"""
SITESENSE - Asynchronous Job Queue Manager (Feature 1.3, Week 1)
Tracks job statuses (queued, processing, completed, failed) and executes
asynchronous computer vision detection & compliance rule checking in the background.
"""

import os
import uuid
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

from vision_service.detector import detector
from agentic.compliance_engine import evaluate_inspection_compliance
from storage.preprocessing import preprocess_media

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
DATABASE_URL = os.getenv("DATABASE_URL")

class JobManager:
    def __init__(self):
        # In-memory job state tracker
        self.jobs: Dict[str, Dict[str, Any]] = {}

    def create_job(self, result_id: str = None) -> str:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        self.jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "progress": 0,
            "result_id": result_id,
            "error": None,
            "created_at": time.time(),
            "updated_at": time.time()
        }
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.jobs.get(job_id)

    def update_job(self, job_id: str, status: str, progress: int = 0, error: str = None):
        if job_id in self.jobs:
            self.jobs[job_id]["status"] = status
            self.jobs[job_id]["progress"] = progress
            self.jobs[job_id]["error"] = error
            self.jobs[job_id]["updated_at"] = time.time()

    def process_inspection_async(self, job_id: str, inspection_id: str):
        """
        Background worker task:
        1. Reads uploaded media files for this inspection.
        2. Runs object detector on image files.
        3. Persists bounding boxes and confidence to the Neon DB detections table.
        4. Runs compliance engine to evaluate rules against policy clauses.
        5. Updates job status to completed.
        """
        print(f"[Worker] Starting background processing for job {job_id} (Inspection: {inspection_id})")
        self.update_job(job_id, status="processing", progress=20)

        conn = None
        try:
            conn = psycopg2.connect(DATABASE_URL)
            conn.autocommit = True
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # Fetch media files for this inspection
            cur.execute("""
                SELECT id, type, path, metadata 
                FROM media 
                WHERE inspection_id::text = %s;
            """, (inspection_id,))
            media_files = cur.fetchall()

            total_files = len(media_files)
            print(f"[Worker] Processing {total_files} media files for inspection {inspection_id}")

            for idx, m in enumerate(media_files, 1):
                media_id = str(m["id"])
                file_path = m["path"]
                media_type = m["type"]

                if os.path.exists(file_path):
                    # Preprocess media (normalizes image, samples video frames, renders PDF pages)
                    pre_res = preprocess_media(file_path)
                    target_images = pre_res.get("primary_targets", [file_path]) if pre_res["media_type"] in ["image", "video", "document"] else []

                    for img_target in target_images:
                        if os.path.exists(img_target) and Path(img_target).suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                            detections = detector.detect(img_target)
                            print(f"[Worker] File {Path(img_target).name}: {len(detections)} objects detected")

                            for d in detections:
                                cur.execute("""
                                    INSERT INTO detections (media_id, class_name, bbox, confidence, zone)
                                    VALUES (%s, %s, %s, %s, %s);
                                """, (
                                    media_id,
                                    d["class_name"],
                                    json.dumps(d["bbox"]),
                                    d["confidence"],
                                    d.get("zone")
                                ))

                progress_val = 20 + int((idx / max(total_files, 1)) * 50)
                self.update_job(job_id, status="processing", progress=progress_val)

            cur.close()
            conn.close()

            # 4. Evaluate compliance rules against the newly stored detections
            print(f"[Worker] Running automated compliance engine for inspection {inspection_id}...")
            self.update_job(job_id, status="processing", progress=80)
            eval_result = evaluate_inspection_compliance(inspection_id)

            print(f"[Worker] Inspection completed! Flagged violations: {eval_result.get('violations_flagged', 0)}")
            self.update_job(job_id, status="completed", progress=100)

        except Exception as e:
            print(f"[Worker Error] Job {job_id} failed: {e}")
            if conn:
                conn.close()
            self.update_job(job_id, status="failed", progress=100, error=str(e))

# Global job manager singleton
job_manager = JobManager()
