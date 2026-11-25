from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class TicketCreate(BaseModel):
    finding_id: uuid.UUID = Field(..., description="Failed finding that triggered this ticket")
    inspection_id: Optional[uuid.UUID] = Field(default=None, description="Inspection ID")
    title: Optional[str] = Field(default="Remediation Ticket", description="Ticket summary")
    description: Optional[str] = Field(default="", description="Detailed remediation instructions")
    priority: Optional[str] = Field(default="medium", description="low | medium | high | critical")
    proposed_by_agent: Optional[bool] = Field(default=False, description="Proposed by AI agent")


class TicketApproveRequest(BaseModel):
    approved: bool = Field(..., description="True to approve, False to reject")
    resolution_notes: Optional[str] = Field(default=None, description="Manager notes")


class TicketResponse(BaseModel):
    id: uuid.UUID
    finding_id: uuid.UUID
    inspection_id: Optional[uuid.UUID] = None
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = "medium"
    status: str
    proposed_by_agent: Optional[bool] = False
    created_by: Optional[uuid.UUID] = None
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
