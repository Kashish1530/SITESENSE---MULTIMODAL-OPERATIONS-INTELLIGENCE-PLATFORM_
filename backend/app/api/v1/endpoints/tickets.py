from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db, require_manager
from app.models.users_sites import User
from app.schemas.common import PaginatedResponse
from app.schemas.tickets import TicketApproveRequest, TicketCreate, TicketResponse
from app.services.ticket_service import TicketService

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[TicketResponse],
    summary="List Maintenance & Remediation Tickets",
    description="Returns remediation tickets with optional status and finding filters. Accessible by Managers and Admins.",
)
def list_tickets(
    finding_id: Optional[uuid.UUID] = Query(None, description="Filter by finding ID"),
    inspection_id: Optional[uuid.UUID] = Query(None, description="Filter by inspection ID"),
    status: Optional[str] = Query(None, description="Filter by status (proposed, approved, rejected, resolved)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponse[TicketResponse]:
    """List tickets with pagination."""
    items, total = TicketService.list_tickets(
        db,
        finding_id=finding_id,
        inspection_id=inspection_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Raise Remediation Ticket from Finding",
    description="Creates a ticket linked to a compliance failure. Agent can propose tickets, or managers can create directly.",
)
def create_ticket(
    payload: TicketCreate,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> TicketResponse:
    """Create a remediation ticket."""
    return TicketService.create_ticket(db, current_user, payload)


@router.post(
    "/{ticket_id}/approve",
    response_model=TicketResponse,
    summary="Approve or Reject AI-Proposed Ticket (Manager Only)",
    description="Human-in-the-loop approval gate: Approves or rejects an AI agent proposed ticket.",
)
def approve_ticket(
    ticket_id: uuid.UUID,
    payload: TicketApproveRequest,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> TicketResponse:
    """Approve or reject ticket proposal."""
    return TicketService.approve_or_reject_ticket(
        db,
        ticket_id,
        current_user,
        approved=payload.approved,
        resolution_notes=payload.resolution_notes,
    )
