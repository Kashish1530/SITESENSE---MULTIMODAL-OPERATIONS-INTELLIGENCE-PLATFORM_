import hashlib
import logging
import os
from pathlib import Path
import re
import shutil
from typing import Any, Dict, Optional, Set, Tuple
import uuid
from fastapi import UploadFile
from PIL import Image
from app.config.settings import get_settings
from app.core.exceptions import BadRequestError, InternalServerError

logger = logging.getLogger("app.storage")
settings = get_settings()

# Allowed extensions and classification
ALLOWED_EXTENSIONS: Dict[str, str] = {
    # Images
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".webp": "image",
    ".bmp": "image",
    ".tiff": "image",
    # Videos
    ".mp4": "video",
    ".mov": "video",
    ".avi": "video",
    ".mkv": "video",
    ".webm": "video",
    # Documents & Spreadsheets
    ".pdf": "doc",
    ".xlsx": "doc",
    ".xls": "doc",
    ".csv": "doc",
    ".json": "doc",
    ".txt": "doc",
}

# Default MIME type mapping fallback
MIME_TYPE_MAPPING: Dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".pdf": "application/pdf",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".csv": "text/csv",
    ".json": "application/json",
    ".txt": "text/plain",
}


_minio_unreachable: bool = False


class StorageService:
    """Manages file storage, path isolation, integrity, and media metadata extraction with MinIO and local fallback."""

    def __init__(self, base_dir: Optional[str] = None):
        global _minio_unreachable
        self.base_dir = Path(base_dir or settings.MEDIA_STORAGE_PATH).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

        # MinIO S3 Object Storage Client
        self.minio_client = None
        if not _minio_unreachable and getattr(settings, "STORAGE_BACKEND", "local").lower() == "minio":
            try:
                from minio import Minio
                self.minio_client = Minio(
                    endpoint=settings.MINIO_ENDPOINT,
                    access_key=settings.MINIO_ACCESS_KEY,
                    secret_key=settings.MINIO_SECRET_KEY,
                    secure=settings.MINIO_SECURE,
                )
                if not self.minio_client.bucket_exists(settings.MINIO_BUCKET_NAME):
                    self.minio_client.make_bucket(settings.MINIO_BUCKET_NAME)
                logger.info(f"Connected to MinIO at {settings.MINIO_ENDPOINT}, bucket: '{settings.MINIO_BUCKET_NAME}'")
            except Exception as e:
                _minio_unreachable = True
                logger.warning(f"Could not connect to MinIO ({e}). Fallback to local storage permanently.")
                self.minio_client = None

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent directory traversal or filesystem corruption."""
        name = os.path.basename(filename)
        # Strip path traversal attempts and special characters
        name = re.sub(r"[^\w\.-]", "_", name)
        return name or "file"

    def get_extension(self, filename: str) -> str:
        """Extract lowercase file extension."""
        _, ext = os.path.splitext(filename)
        return ext.lower()

    def validate_file_metadata(self, filename: str, content_type: Optional[str] = None) -> Tuple[str, str]:
        """Validate filename extension and determine media type (image | video | doc)."""
        ext = self.get_extension(filename)
        if not ext or ext not in ALLOWED_EXTENSIONS:
            allowed = ", ".join(sorted(ALLOWED_EXTENSIONS.keys()))
            raise BadRequestError(
                message=f"Unsupported file format '{ext}'. Allowed extensions: {allowed}",
                detail={"filename": filename, "extension": ext, "allowed": allowed},
            )

        media_type = ALLOWED_EXTENSIONS[ext]
        mime_type = content_type or MIME_TYPE_MAPPING.get(ext, "application/octet-stream")
        return media_type, mime_type

    def resolve_safe_path(self, relative_path: str) -> Path:
        """Resolve a relative storage path safely, ensuring it resides inside base_dir."""
        # Normalize separators
        clean_relative = relative_path.replace("\\", "/").lstrip("/")
        target = (self.base_dir / clean_relative).resolve()
        try:
            target.relative_to(self.base_dir)
        except ValueError:
            raise BadRequestError(
                message="Invalid storage path: directory traversal detected.",
                detail={"path": relative_path},
            )
        return target

    def save_file_stream(
        self,
        file: UploadFile,
        inspection_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Stream an uploaded file to disk with size checks, hashing, and metadata extraction."""
        original_name = file.filename or "upload"
        sanitized = self.sanitize_filename(original_name)
        media_type, mime_type = self.validate_file_metadata(sanitized, file.content_type)

        # Create inspection-specific subfolder
        subfolder = self.base_dir / str(inspection_id)
        subfolder.mkdir(parents=True, exist_ok=True)

        unique_prefix = uuid.uuid4().hex[:12]
        unique_filename = f"{unique_prefix}_{sanitized}"
        target_path = subfolder / unique_filename
        relative_path = f"{inspection_id}/{unique_filename}"

        hasher = hashlib.sha256()
        total_size = 0
        chunk_size = 1024 * 1024  # 1MB buffer

        try:
            file.file.seek(0)
            with open(target_path, "wb") as f_out:
                while True:
                    chunk = file.file.read(chunk_size)
                    if not chunk:
                        break
                    total_size += len(chunk)
                    if total_size > self.max_size_bytes:
                        raise BadRequestError(
                            message=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
                            detail={
                                "max_size_mb": settings.MAX_UPLOAD_SIZE_MB,
                                "bytes_received": total_size,
                            },
                        )
                    hasher.update(chunk)
                    f_out.write(chunk)
        except Exception as e:
            # Clean up partial file on failure
            if target_path.exists():
                try:
                    target_path.unlink()
                except OSError:
                    pass
            if isinstance(e, BadRequestError):
                raise
            raise InternalServerError(
                message="Failed to write uploaded file to storage.",
                detail={"error": str(e)},
            )

        metadata: Dict[str, Any] = {
            "sha256": hasher.hexdigest(),
            "original_filename": original_name,
        }

        # Extract image dimensions if image
        if media_type == "image":
            try:
                with Image.open(target_path) as img:
                    metadata["width"] = img.width
                    metadata["height"] = img.height
                    metadata["format"] = img.format
                    metadata["color_mode"] = img.mode
            except Exception:
                # If Pillow cannot parse metadata, continue without crashing
                pass

        # Stream binary object into MinIO
        minio_object_key = f"inspections/{inspection_id}/{unique_filename}"
        if self.minio_client:
            try:
                with open(target_path, "rb") as f_data:
                    self.minio_client.put_object(
                        bucket_name=settings.MINIO_BUCKET_NAME,
                        object_name=minio_object_key,
                        data=f_data,
                        length=total_size,
                        content_type=mime_type,
                    )
                metadata["storage_backend"] = "minio"
                metadata["minio_bucket"] = settings.MINIO_BUCKET_NAME
                metadata["minio_object_key"] = minio_object_key
            except Exception as e:
                logger.warning(f"Failed to stream to MinIO: {e}")
                metadata["storage_backend"] = "local"
        else:
            metadata["storage_backend"] = "local"

        return {
            "relative_path": relative_path,
            "filename": original_name,
            "media_type": media_type,
            "mime_type": mime_type,
            "file_size_bytes": total_size,
            "metadata": metadata,
        }

    def delete_file(self, relative_path: str) -> bool:
        """Safely delete a file from disk and MinIO if it exists."""
        deleted = False
        try:
            target = self.resolve_safe_path(relative_path)
            if target.exists() and target.is_file():
                target.unlink()
                deleted = True
        except Exception:
            pass

        if self.minio_client:
            try:
                clean_key = relative_path.replace("\\", "/").lstrip("/")
                object_key = clean_key if clean_key.startswith("inspections/") else f"inspections/{clean_key}"
                self.minio_client.remove_object(settings.MINIO_BUCKET_NAME, object_key)
                deleted = True
            except Exception:
                pass

        return deleted

    def file_exists(self, relative_path: str) -> bool:
        """Check if file exists on disk or in MinIO."""
        try:
            target = self.resolve_safe_path(relative_path)
            if target.exists() and target.is_file():
                return True
        except Exception:
            pass

        if self.minio_client:
            try:
                clean_key = relative_path.replace("\\", "/").lstrip("/")
                object_key = clean_key if clean_key.startswith("inspections/") else f"inspections/{clean_key}"
                self.minio_client.stat_object(settings.MINIO_BUCKET_NAME, object_key)
                return True
            except Exception:
                pass

        return False

    def get_absolute_path(self, relative_path: str) -> Path:
        """Get absolute Path object for streaming with automatic MinIO retrieval if missing on disk."""
        target = self.resolve_safe_path(relative_path)
        if not target.exists() or not target.is_file():
            # Check MinIO and retrieve if present
            if self.minio_client:
                try:
                    clean_key = relative_path.replace("\\", "/").lstrip("/")
                    object_key = clean_key if clean_key.startswith("inspections/") else f"inspections/{clean_key}"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    self.minio_client.fget_object(settings.MINIO_BUCKET_NAME, object_key, str(target))
                    if target.exists() and target.is_file():
                        return target
                except Exception as e:
                    logger.warning(f"Could not retrieve '{relative_path}' from MinIO: {e}")

            raise BadRequestError(
                message="Target media file does not exist on storage.",
                detail={"path": relative_path},
            )
        return target

    def get_presigned_url(self, relative_path: str, expiry_hours: int = 1) -> Optional[str]:
        """Generate direct presigned URL from MinIO."""
        if not self.minio_client:
            return None
        try:
            from datetime import timedelta
            clean_key = relative_path.replace("\\", "/").lstrip("/")
            object_key = clean_key if clean_key.startswith("inspections/") else f"inspections/{clean_key}"
            return self.minio_client.presigned_get_object(
                settings.MINIO_BUCKET_NAME, object_key, expires=timedelta(hours=expiry_hours)
            )
        except Exception as e:
            logger.warning(f"Could not generate presigned URL: {e}")
            return None

    def save_chat_attachment(
        self,
        file: UploadFile,
        session_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Stream an uploaded multimodal chat attachment (photo, video, PDF, or Excel) to disk and MinIO."""
        original_name = file.filename or "attachment"
        sanitized = self.sanitize_filename(original_name)
        media_type, mime_type = self.validate_file_metadata(sanitized, file.content_type)

        sess_folder = str(session_id) if session_id else "general"
        subfolder = self.base_dir / "chat" / sess_folder
        subfolder.mkdir(parents=True, exist_ok=True)

        unique_prefix = uuid.uuid4().hex[:12]
        unique_filename = f"{unique_prefix}_{sanitized}"
        target_path = subfolder / unique_filename
        relative_path = f"chat/{sess_folder}/{unique_filename}"

        hasher = hashlib.sha256()
        total_size = 0
        chunk_size = 1024 * 1024

        try:
            file.file.seek(0)
            with open(target_path, "wb") as f_out:
                while True:
                    chunk = file.file.read(chunk_size)
                    if not chunk:
                        break
                    total_size += len(chunk)
                    if total_size > self.max_size_bytes:
                        raise BadRequestError(
                            message=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
                            detail={
                                "max_size_mb": settings.MAX_UPLOAD_SIZE_MB,
                                "bytes_received": total_size,
                            },
                        )
                    hasher.update(chunk)
                    f_out.write(chunk)
        except Exception as e:
            if target_path.exists():
                try:
                    target_path.unlink()
                except OSError:
                    pass
            if isinstance(e, BadRequestError):
                raise
            raise InternalServerError(
                message="Failed to write uploaded chat attachment to storage.",
                detail={"error": str(e)},
            )

        minio_key = f"chat/{sess_folder}/{unique_filename}"
        if self.minio_client:
            try:
                self.minio_client.fput_object(
                    bucket_name=settings.MINIO_BUCKET_NAME,
                    object_name=minio_key,
                    file_path=str(target_path),
                    content_type=mime_type,
                )
            except Exception as exc:
                logger.warning(f"Failed to sync chat attachment '{minio_key}' to MinIO: {exc}")

        ext = self.get_extension(sanitized)
        if ext in [".xlsx", ".xls", ".csv"]:
            friendly_type = "excel"
        elif ext in [".pdf"]:
            friendly_type = "pdf"
        elif ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
            friendly_type = "video"
        elif ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"]:
            friendly_type = "image"
        else:
            friendly_type = "doc"

        return {
            "id": uuid.uuid4(),
            "filename": original_name,
            "type": friendly_type,
            "media_type": media_type,
            "mime_type": mime_type,
            "file_size_bytes": total_size,
            "path": relative_path,
            "minio_key": minio_key,
            "sha256": hasher.hexdigest(),
        }


# Singleton instance
storage_service = StorageService()
