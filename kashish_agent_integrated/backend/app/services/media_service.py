from typing import Any, Dict, List, Optional
import uuid
from fastapi import UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.api.deps import verify_site_access
from app.config.settings import get_settings
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.inspections_media import Inspection, Job, Media
from app.models.users_sites import User
from app.schemas.media import MediaBatchUploadResponse, MediaResponse
from app.services.storage_service import storage_service

settings = get_settings()


class MediaService:
    """Business service orchestrating media uploads, metadata storage in PostgreSQL, file serving, and deletions."""

    @staticmethod
    def _build_media_response(
        media: Media,
        detection_summary: Optional[Dict[str, Any]] = None,
        ocr_summary: Optional[Dict[str, Any]] = None,
    ) -> MediaResponse:
        """Helper to construct MediaResponse with full download URL."""
        download_url = f"{settings.API_V1_PREFIX}/media/{media.id}/download"
        metadata_dict = media.metadata_json if isinstance(media.metadata_json, dict) else {}
        return MediaResponse(
            id=media.id,
            inspection_id=media.inspection_id,
            type=media.type,
            path=media.path,
            filename=media.filename,
            mime_type=media.mime_type,
            file_size_bytes=media.file_size_bytes or 0,
            metadata=metadata_dict,
            is_annotated=media.is_annotated,
            annotated_path=media.annotated_path,
            download_url=download_url,
            created_at=media.created_at,
            detection_summary=detection_summary,
            ocr_summary=ocr_summary,
        )

    @classmethod
    def _enqueue_image_job(
        cls,
        db: Session,
        inspection_id: uuid.UUID,
        media_ids: List[str],
        user_id: str,
    ) -> Optional[Job]:
        """Create a Neon Job record and dispatch the image batch to Redis/Celery."""
        if not media_ids:
            return None

        job = Job(
            inspection_id=inspection_id,
            job_type="vision_ocr_batch",
            status="queued",
            progress=0,
            current_stage=f"queued_{len(media_ids)}_images_for_celery",
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        try:
            from app.workers.image_tasks import process_image_batch_task

            process_image_batch_task.delay(str(job.id), media_ids, user_id)
        except Exception as exc:
            import logging
            import threading
            from app.workers.image_tasks import process_image_batch_task

            logging.getLogger("app.media").warning(
                f"Celery/Redis dispatch failed ({exc}); running batch job {job.id} in background thread."
            )
            threading.Thread(
                target=process_image_batch_task.run,
                args=(str(job.id), media_ids, user_id),
                daemon=True,
            ).start()

        return job

    @classmethod
    def upload_media(
        cls,
        db: Session,
        inspection_id: uuid.UUID,
        file: UploadFile,
        current_user: User,
        auto_process: bool = True,
        enqueue_async: bool = False,
    ) -> MediaResponse:
        """Validate site access, stream file to storage, persist media record, and run or enqueue YOLO + OCR for images."""
        # 1. Verify inspection existence
        inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
        if not inspection:
            raise NotFoundError(
                message=f"Inspection {inspection_id} not found.",
                detail={"inspection_id": str(inspection_id)},
            )

        # 2. Enforce site access boundary
        verify_site_access(inspection.site_id, current_user, db)

        # 3. Stream file to storage (local + MinIO)
        saved_file = storage_service.save_file_stream(file, inspection_id)

        # 4. Save metadata to DB
        media = Media(
            inspection_id=inspection_id,
            type=saved_file["media_type"],
            path=saved_file["relative_path"],
            filename=saved_file["filename"],
            mime_type=saved_file["mime_type"],
            file_size_bytes=saved_file["file_size_bytes"],
            metadata_json=saved_file["metadata"],
            is_annotated=False,
        )
        db.add(media)
        db.commit()
        db.refresh(media)

        detection_summary: Optional[Dict[str, Any]] = None
        ocr_summary: Optional[Dict[str, Any]] = None

        # 5. Either enqueue to Redis/Celery or run inline for images & videos
        if auto_process and media.type in ("image", "video"):
            if enqueue_async:
                job = cls._enqueue_image_job(
                    db=db,
                    inspection_id=inspection_id,
                    media_ids=[str(media.id)],
                    user_id=str(current_user.id),
                )
                if job:
                    ocr_summary = {"job_id": str(job.id), "status": job.status}
            else:
                try:
                    from app.workers.image_tasks import run_single_media_pipeline

                    res = run_single_media_pipeline(db=db, media_id=media.id, current_user=current_user)
                    db.refresh(media)
                    detection_summary = res.get("detection_summary") or (
                        {
                            "model_version": "yolo_best3_best2_ensemble",
                            "total_detections": res.get("total_detections", 0),
                            "class_counts": res.get("class_counts", {}),
                            "violations_detected": res.get("violations_detected", 0),
                            "annotated_media_url": res.get("annotated_media_url"),
                        }
                        if media.type == "video"
                        else None
                    )
                    ocr_summary = res.get("ocr_summary") or (
                        {"ocr_reports_count": res.get("ocr_reports_count", 0)}
                        if media.type == "video"
                        else None
                    )
                except Exception as exc:
                    import logging
                    logging.getLogger("app.media").error(
                        f"Auto YOLO+OCR pipeline failed for media {media.id}: {exc}", exc_info=True
                    )

        return cls._build_media_response(
            media,
            detection_summary=detection_summary,
            ocr_summary=ocr_summary,
        )

    @classmethod
    def upload_batch(
        cls,
        db: Session,
        inspection_id: uuid.UUID,
        files: List[UploadFile],
        current_user: User,
    ) -> MediaBatchUploadResponse:
        """Batch upload up to 15-20+ media files, store originals in MinIO/Neon, and enqueue a Celery job in Redis."""
        inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
        if not inspection:
            raise NotFoundError(
                message=f"Inspection {inspection_id} not found.",
                detail={"inspection_id": str(inspection_id)},
            )

        verify_site_access(inspection.site_id, current_user, db)

        uploaded: List[MediaResponse] = []
        image_media_ids: List[str] = []
        errors: List[Dict[str, Any]] = []

        for file in files:
            try:
                res = cls.upload_media(
                    db,
                    inspection_id,
                    file,
                    current_user,
                    auto_process=False,
                    enqueue_async=False,
                )
                uploaded.append(res)
                if res.type in ("image", "video"):
                    image_media_ids.append(str(res.id))
            except Exception as e:
                errors.append({
                    "filename": file.filename,
                    "error": str(e),
                })

        job = cls._enqueue_image_job(
            db=db,
            inspection_id=inspection_id,
            media_ids=image_media_ids,
            user_id=str(current_user.id),
        )

        return MediaBatchUploadResponse(
            uploaded=uploaded,
            total_uploaded=len(uploaded),
            errors=errors,
            job_id=str(job.id) if job else None,
            status=job.status if job else "completed",
        )

    @classmethod
    def get_media(
        cls,
        db: Session,
        media_id: uuid.UUID,
        current_user: User,
    ) -> MediaResponse:
        """Retrieve media metadata by ID, checking access permissions."""
        media = db.query(Media).filter(Media.id == media_id).first()
        if not media:
            raise NotFoundError(
                message=f"Media {media_id} not found.",
                detail={"media_id": str(media_id)},
            )

        inspection = db.query(Inspection).filter(Inspection.id == media.inspection_id).first()
        if inspection:
            verify_site_access(inspection.site_id, current_user, db)

        return cls._build_media_response(media)

    @classmethod
    def get_file_response(
        cls,
        db: Session,
        media_id: uuid.UUID,
        current_user: User,
        annotated: bool = False,
    ) -> FileResponse:
        """Stream the actual binary file from disk to the client with correct MIME type."""
        media = db.query(Media).filter(Media.id == media_id).first()
        if not media:
            raise NotFoundError(
                message=f"Media {media_id} not found.",
                detail={"media_id": str(media_id)},
            )

        inspection = db.query(Inspection).filter(Inspection.id == media.inspection_id).first()
        if inspection:
            verify_site_access(inspection.site_id, current_user, db)

        target_path_str = media.annotated_path if (annotated and media.annotated_path) else media.path
        abs_path = storage_service.get_absolute_path(target_path_str)

        filename = media.filename or "media_file"
        if annotated:
            filename = f"annotated_{filename}"

        return FileResponse(
            path=str(abs_path),
            media_type=media.mime_type or "application/octet-stream",
            filename=filename,
        )

    @classmethod
    def list_media_for_inspection(
        cls,
        db: Session,
        inspection_id: uuid.UUID,
        current_user: User,
        media_type: Optional[str] = None,
    ) -> List[MediaResponse]:
        """List all media records for an inspection."""
        inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
        if not inspection:
            raise NotFoundError(
                message=f"Inspection {inspection_id} not found.",
                detail={"inspection_id": str(inspection_id)},
            )

        verify_site_access(inspection.site_id, current_user, db)

        query = db.query(Media).filter(Media.inspection_id == inspection_id)
        if media_type:
            query = query.filter(Media.type == media_type.lower())

        records = query.order_by(Media.created_at.asc()).all()
        return [cls._build_media_response(m) for m in records]

    @classmethod
    def delete_media(
        cls,
        db: Session,
        media_id: uuid.UUID,
        current_user: User,
    ) -> bool:
        """Delete media record and underlying storage files."""
        media = db.query(Media).filter(Media.id == media_id).first()
        if not media:
            raise NotFoundError(
                message=f"Media {media_id} not found.",
                detail={"media_id": str(media_id)},
            )

        inspection = db.query(Inspection).filter(Inspection.id == media.inspection_id).first()
        if inspection:
            user_role = (current_user.role or "").lower()
            is_owner = inspection.user_id == current_user.id
            if user_role not in ("admin", "manager") and not is_owner:
                raise ForbiddenError(
                    message="Only managers, admins, or the inspection author can delete media.",
                    detail={"user_role": current_user.role, "media_id": str(media_id)},
                )

        # Remove physical files
        storage_service.delete_file(media.path)
        if media.annotated_path:
            storage_service.delete_file(media.annotated_path)

        # Remove from DB (cascades to detections/extractions)
        db.delete(media)
        db.commit()
        return True
