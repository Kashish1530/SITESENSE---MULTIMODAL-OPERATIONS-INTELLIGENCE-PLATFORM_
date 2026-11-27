from typing import Optional
import uuid
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.core.exceptions import NotFoundError
from app.models.users_sites import User
from app.schemas.chat import (
    ChatAttachmentUploadResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatQueryResponse,
    ChatSessionCreate,
    ChatSessionResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.chat_service import ChatService
from app.services.storage_service import StorageService

router = APIRouter()


@router.get(
    "/sessions",
    response_model=PaginatedResponse[ChatSessionResponse],
    summary="List User Chat Sessions",
    description="Lists all conversational chat sessions created by the authenticated user.",
)
def list_chat_sessions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponse[ChatSessionResponse]:
    """List chat sessions for the current user."""
    items, total = ChatService.list_sessions(db, current_user, limit=limit, offset=offset)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.post(
    "/sessions",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Chat Session",
    description="Starts a new conversational session with optional site context.",
)
def create_chat_session(
    payload: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatSessionResponse:
    """Create a new chat conversation thread."""
    return ChatService.create_session(db, current_user, payload)


@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionResponse,
    summary="Get Chat Session Metadata",
    description="Retrieves session title, site context, and timestamps.",
)
def get_chat_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatSessionResponse:
    """Get chat session details."""
    return ChatService.get_session(db, session_id, current_user)


@router.get(
    "/sessions/{session_id}/messages",
    response_model=PaginatedResponse[ChatMessageResponse],
    summary="Get Chat Message History",
    description="Retrieves conversational history, citations, and attachments for a session.",
)
def get_chat_messages(
    session_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponse[ChatMessageResponse]:
    """Retrieve message history for a chat session."""
    items, total = ChatService.get_messages(db, session_id, current_user, limit=limit, offset=offset)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatQueryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send Multimodal Chat Message",
    description="Sends a user question with optional attached media. Returns grounded assistant answer with policy citations.",
)
def send_chat_message(
    session_id: uuid.UUID,
    payload: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatQueryResponse:
    """Send user message and receive grounded AI assistant response."""
    return ChatService.send_message(db, session_id, current_user, payload)


@router.post(
    "/upload-attachment",
    response_model=ChatAttachmentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Multimodal Chat Attachment",
    description="Uploads photo, video, PDF, or Excel spreadsheet to MinIO for Intelligence Chat.",
)
def upload_chat_attachment(
    file: UploadFile = File(..., description="Binary media file (photo, video, PDF, Excel sheet)"),
    session_id: Optional[uuid.UUID] = Form(None, description="Optional chat session ID"),
    current_user: User = Depends(get_current_user),
) -> ChatAttachmentUploadResponse:
    """Stream chat attachment to disk and MinIO bucket 'sitesense-media'."""
    storage = StorageService()
    res = storage.save_chat_attachment(file=file, session_id=session_id)
    return ChatAttachmentUploadResponse(
        id=str(res["id"]),
        name=res["filename"],
        type=res["type"],
        mime_type=res["mime_type"],
        size=res["file_size_bytes"],
        path=res["path"],
        download_url=f"/api/v1/chat/attachments/{res['id']}?path={res['path']}",
    )


@router.get(
    "/attachments/{attachment_id}",
    summary="Download or Stream Chat Attachment",
    description="Streams uploaded chat media (photo, video, PDF, Excel) from secure storage or MinIO.",
)
def download_chat_attachment(
    attachment_id: uuid.UUID,
    path: str = Query(..., description="Storage path"),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Stream chat attachment."""
    storage = StorageService()
    safe_path = storage.resolve_safe_path(path)
    if not safe_path.exists():
        if storage.minio_client:
            try:
                minio_key = f"chat/{path.replace('chat/', '')}" if not path.startswith("chat/") else path
                storage.minio_client.fget_object(storage.minio_bucket, minio_key, str(safe_path))
            except Exception:
                raise NotFoundError(message="Chat attachment not found.")
        else:
            raise NotFoundError(message="Chat attachment not found.")
    _, mime_type = storage.validate_file_metadata(safe_path.name)
    return FileResponse(path=str(safe_path), media_type=mime_type, filename=safe_path.name)
