import logging
import uuid
from typing import Any, Dict, List

from app.db.session import SessionLocal
from app.models.base import ist_now
from app.models.inspections_media import Inspection, Job, Media
from app.models.users_sites import User
from app.services.detection_service import DetectionService
from app.services.ocr_service import OCRService
from app.services.storage_service import storage_service
from app.workers.celery_app import celery_app

logger = logging.getLogger("app.workers.image_tasks")


def run_single_media_pipeline(
    db,
    media_id: uuid.UUID,
    current_user: User,
    progress_callback=None,
) -> Dict[str, Any]:
    """
    Execute the full pipeline for one uploaded image or video:
    - Image: YOLO (best_3.pt + best_2.pt) -> annotated image -> MinIO + Neon -> OCR JSON -> 5 Neon OCR tables
    - Video: YOLO (best_3.pt + best_2.pt) + Tracking + ZoneEngine -> annotated video (MinIO + Neon)
             -> violation/alert evidence snapshots (MinIO) -> OCR JSON on all snapshots -> 5 Neon OCR tables
    """
    media = db.query(Media).filter(Media.id == media_id).first()
    if not media:
        raise ValueError(f"Media {media_id} not found")

    if media.type == "video":
        from app.services.video_service import VideoService

        return VideoService.process_video(
            db=db,
            media_id=media.id,
            current_user=current_user,
            progress_callback=progress_callback,
        )

    return run_single_image_pipeline(db, media_id, current_user)


def run_single_image_pipeline(db, media_id: uuid.UUID, current_user: User) -> Dict[str, Any]:
    """
    Execute the full image pipeline for one uploaded image:
    1. YOLO detection (best_3.pt + best_2.pt) -> annotated image -> MinIO + Neon
    2. OCR extraction on annotated image -> JSON -> MinIO + 5 Neon OCR tables
    """
    media = db.query(Media).filter(Media.id == media_id).first()
    if not media:
        raise ValueError(f"Media {media_id} not found")

    det_res = DetectionService.detect_media(
        db=db,
        media_id=media.id,
        current_user=current_user,
        conf_threshold=0.25,
        iou_threshold=0.45,
        save_annotated=True,
    )
    db.refresh(media)

    detection_summary = {
        "model_version": det_res.get("model_version"),
        "total_detections": det_res.get("total_detections", 0),
        "class_counts": det_res.get("class_counts", {}),
        "violations_detected": det_res.get("violations_detected", 0),
        "annotated_media_url": det_res.get("annotated_media_url"),
        "inference_time_ms": det_res.get("inference_time_ms", 0.0),
    }

    annotated_abs_path = det_res.get("annotated_abs_path")
    if not annotated_abs_path and media.annotated_path:
        annotated_abs_path = str(storage_service.get_absolute_path(media.annotated_path))

    ocr_summary: Dict[str, Any] = {}
    if annotated_abs_path:
        inspection = db.query(Inspection).filter(Inspection.id == media.inspection_id).first()
        site_id_str = str(inspection.site_id) if inspection else "SITE-DEFAULT"
        ocr_res = OCRService.process_annotated_image(
            db=db,
            media=media,
            annotated_image_path=annotated_abs_path,
            site_id=site_id_str,
        )
        db.refresh(media)
        ocr_summary = {
            "report_id": ocr_res.get("report_id"),
            "json_path": ocr_res.get("json_path"),
            "full_text": ocr_res.get("full_text", ""),
            "entities_count": ocr_res.get("entities_count", 0),
            "review_queue_count": ocr_res.get("review_queue_count", 0),
            "compliance_checks_count": ocr_res.get("compliance_checks_count", 0),
        }

    return {
        "media_id": str(media.id),
        "filename": media.filename,
        "annotated_path": media.annotated_path,
        "detection_summary": detection_summary,
        "ocr_summary": ocr_summary,
    }


@celery_app.task(name="sitesense.process_image_batch", bind=True)
def process_image_batch_task(self, job_id: str, media_ids: List[str], user_id: str) -> Dict[str, Any]:
    """
    Celery background task to process a batch of uploaded images (e.g., 15-20 images):
    YOLO (best_3.pt + best_2.pt) -> Image Annotation -> MinIO -> OCR -> JSON -> Neon.
    Updates Job progress and status in Neon after each image.
    """
    db = SessionLocal()
    try:
        job_uuid = uuid.UUID(job_id)
        user_uuid = uuid.UUID(user_id)

        job = db.query(Job).filter(Job.id == job_uuid).first()
        user = db.query(User).filter(User.id == user_uuid).first()
        if not job or not user:
            raise ValueError(f"Job ({job_id}) or User ({user_id}) not found")

        total = len(media_ids)
        job.status = "processing"
        job.started_at = ist_now()
        job.progress = 5 if total > 0 else 100
        job.current_stage = f"ai_inference_0_of_{total}"
        db.commit()

        results: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        total_detections = 0
        total_ocr_reports = 0

        def _update_job_progress(pct: int, stage: str) -> None:
            j = db.query(Job).filter(Job.id == job_uuid).first()
            if j:
                j.progress = pct
                j.current_stage = stage
                db.commit()

        for idx, mid_str in enumerate(media_ids, start=1):
            try:
                cb = _update_job_progress if total == 1 else None
                item_res = run_single_media_pipeline(db, uuid.UUID(mid_str), user, progress_callback=cb)
                results.append(item_res)
                if item_res.get("media_type") == "video":
                    total_detections += item_res.get("total_detections", 0)
                    total_ocr_reports += item_res.get("ocr_reports_count", 0)
                else:
                    total_detections += item_res.get("detection_summary", {}).get("total_detections", 0)
                    if item_res.get("ocr_summary", {}).get("report_id"):
                        total_ocr_reports += 1
            except Exception as exc:
                logger.error(f"Batch item {mid_str} failed: {exc}", exc_info=True)
                db.rollback()
                errors.append({"media_id": mid_str, "error": str(exc)})

            job = db.query(Job).filter(Job.id == job_uuid).first()
            if job:
                job.progress = min(99, max(5, int((idx / max(1, total)) * 100)))
                job.current_stage = f"processed_{idx}_of_{total}"
                db.commit()

        payload = {
            "total_images": total,
            "processed_count": len(results),
            "failed_count": len(errors),
            "total_detections": total_detections,
            "total_ocr_reports": total_ocr_reports,
            "items": results,
            "errors": errors,
        }

        job = db.query(Job).filter(Job.id == job_uuid).first()
        if job:
            job.status = "completed" if len(results) > 0 or total == 0 else "failed"
            job.progress = 100
            job.current_stage = "completed"
            job.completed_at = ist_now()
            job.result_payload = payload
            if errors and not results:
                job.error_message = errors[0]["error"]
            db.commit()

        return payload
    except Exception as exc:
        logger.error(f"Celery batch task failed for job {job_id}: {exc}", exc_info=True)
        try:
            job = db.query(Job).filter(Job.id == uuid.UUID(job_id)).first()
            if job:
                job.status = "failed"
                job.current_stage = "failed"
                job.error_message = str(exc)
                job.completed_at = ist_now()
                db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()
