from datetime import datetime, timezone
from typing import List, Optional, Tuple
import uuid
from sqlalchemy.orm import Session
from app.core.exceptions import NotFoundError
from app.models.agent_review import Ticket
from app.models.knowledge_compliance import Finding
from app.models.users_sites import User
from app.schemas.tickets import TicketCreate, TicketResponse


class TicketService:
    """Service encapsulating database queries for Remediation Tickets."""

    @classmethod
    def list_tickets(
        cls,
        db: Session,
        *,
        finding_id: Optional[uuid.UUID] = None,
        inspection_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[TicketResponse], int]:
        """List tickets with optional status and finding filters."""
        query = db.query(Ticket)
        if finding_id:
            query = query.filter(Ticket.finding_id == finding_id)
        if inspection_id:
            query = query.filter(Ticket.inspection_id == inspection_id)
        if status:
            query = query.filter(Ticket.status == status.strip().lower())

        total = query.count()
        tickets = query.order_by(Ticket.created_at.desc()).offset(offset).limit(limit).all()
        return [TicketResponse.model_validate(t) for t in tickets], total

    @classmethod
    def create_ticket(
        cls, db: Session, current_user: User, payload: TicketCreate
    ) -> TicketResponse:
        """Create a new ticket from a finding (proposed by agent or raised by human)."""
        finding = db.query(Finding).filter(Finding.id == payload.finding_id).first()
        if not finding:
            raise NotFoundError(message=f"Finding '{payload.finding_id}' not found.")

        inspection_id = payload.inspection_id or finding.inspection_id

        ticket = Ticket(
            finding_id=payload.finding_id,
            inspection_id=inspection_id,
            title=payload.title,
            description=payload.description,
            priority=payload.priority or "medium",
            status="proposed" if payload.proposed_by_agent else "approved",
            proposed_by_agent=payload.proposed_by_agent or False,
            created_by=current_user.id,
            approved_by=current_user.id if not payload.proposed_by_agent else None,
            approved_at=datetime.now(timezone.utc) if not payload.proposed_by_agent else None,
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        return TicketResponse.model_validate(ticket)

    @classmethod
    def approve_or_reject_ticket(
        cls,
        db: Session,
        ticket_id: uuid.UUID,
        approver: User,
        *,
        approved: bool,
        resolution_notes: Optional[str] = None,
    ) -> TicketResponse:
        """Human manager approval gate for AI-proposed tickets."""
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise NotFoundError(message=f"Ticket '{ticket_id}' not found.")

        ticket.status = "approved" if approved else "rejected"
        ticket.approved_by = approver.id
        ticket.approved_at = datetime.now(timezone.utc)
        if resolution_notes:
            ticket.description = f"{ticket.description}\n[Manager Notes]: {resolution_notes}"

        db.commit()
        db.refresh(ticket)
        return TicketResponse.model_validate(ticket)
