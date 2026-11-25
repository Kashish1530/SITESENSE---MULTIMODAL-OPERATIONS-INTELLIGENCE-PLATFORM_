from datetime import datetime
from typing import Any, Dict, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class RuleBase(BaseModel):
    name: str = Field(..., max_length=255, description="Rule name", example="Walkway Clearance Rule")
    description: str = Field(..., description="Rule details")
    rule_type: str = Field(..., max_length=100, description="Rule evaluation type", example="forbidden_object")
    parameters: Dict[str, Any] = Field(..., description="Rule parameter thresholds (JSONB)")
    policy_ref: str = Field(..., max_length=255, description="Governing policy clause", example="Clause 4.2.1")
    severity: Optional[str] = Field(default="high", description="low | medium | high | critical")
    is_active: Optional[bool] = Field(default=True, description="Rule active status")
    policy_id: Optional[uuid.UUID] = Field(default=None, description="Optional parent policy ID")


class RuleCreate(RuleBase):
    pass


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    rule_type: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    policy_ref: Optional[str] = None
    severity: Optional[str] = None
    is_active: Optional[bool] = None
    policy_id: Optional[uuid.UUID] = None


class RuleResponse(RuleBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
