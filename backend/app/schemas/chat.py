from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class CitationItem(BaseModel):
    source_file: Optional[str] = Field(default=None, description="Source policy or manual filename")
    page: Optional[int] = Field(default=None, description="Page number")
    clause: Optional[str] = Field(default=None, description="Policy clause reference")
    excerpt: Optional[str] = Field(default=None, description="Quoted policy text")


class ChatSessionCreate(BaseModel):
    title: Optional[str] = Field(default="New Conversation", description="Session title")
    site_id: Optional[uuid.UUID] = Field(default=None, description="Optional site context")


class ChatSessionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    site_id: Optional[uuid.UUID] = None
    title: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ChatAttachmentItem(BaseModel):
    id: Optional[str] = None
    name: str
    type: str = Field(..., description="image | video | pdf | excel | doc")
    size: Optional[int] = None
    preview_url: Optional[str] = None
    storage_path: Optional[str] = None
    mime_type: Optional[str] = None


class ChatAttachmentUploadResponse(BaseModel):
    id: str
    name: str
    type: str
    mime_type: str
    size: int
    path: str
    download_url: str


class ChatMessageCreate(BaseModel):
    content: Optional[str] = Field(default="", description="Message prompt content")
    attached_media_id: Optional[uuid.UUID] = Field(default=None, description="Optional single media attachment")
    attached_media_ids: Optional[List[uuid.UUID]] = Field(default=None, description="Optional list of media attachment IDs")
    attachments: Optional[List[ChatAttachmentItem]] = Field(default=None, description="Multimodal attachments (photos, videos, PDFs, Excel sheets)")


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str = Field(..., description="Message author role: user | assistant | system")
    content: str
    attached_media_id: Optional[uuid.UUID] = None
    attachment_metadata: Optional[List[Dict[str, Any]]] = None
    citations: Optional[List[Dict[str, Any]]] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ChatQueryResponse(BaseModel):
    session_id: uuid.UUID
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
    route: str = Field(default="multimodal", description="Routing decision: vision | policy | database | multimodal | direct")
    citations: List[Dict[str, Any]] = Field(default_factory=list)
