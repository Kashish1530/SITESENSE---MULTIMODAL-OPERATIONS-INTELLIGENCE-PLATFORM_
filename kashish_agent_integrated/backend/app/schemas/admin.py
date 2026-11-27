from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AdminUserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Full display name")
    email: EmailStr = Field(..., description="User unique login email")
    password: str = Field(..., min_length=6, description="Initial password")
    role: str = Field(default="field", description="User role: admin | manager | field | reviewer")
    site_id: Optional[uuid.UUID] = Field(default=None, description="Initial site assignment")


class AdminUserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, description="Updated full display name")
    role: Optional[str] = Field(default=None, description="Updated role: admin | manager | field | reviewer")
    is_active: Optional[bool] = Field(default=None, description="Active status flag")
    site_id: Optional[uuid.UUID] = Field(default=None, description="Assign site membership")


class AdminUserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: str
    is_active: bool
    site_ids: List[uuid.UUID] = Field(default_factory=list, description="Assigned site IDs")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    action: str
    entity_type: str
    entity_id: Optional[uuid.UUID] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AdminStatsResponse(BaseModel):
    total_users: int
    total_sites: int
    total_inspections: int
    total_findings: int
    total_tickets: int
    pass_rate: float
