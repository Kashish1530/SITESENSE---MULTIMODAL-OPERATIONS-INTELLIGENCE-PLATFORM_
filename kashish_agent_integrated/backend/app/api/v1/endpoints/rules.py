from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db, require_admin
from app.schemas.common import PaginatedResponse
from app.schemas.rules import RuleCreate, RuleResponse, RuleUpdate
from app.services.rule_service import RuleService

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[RuleResponse],
    summary="List Compliance Rules",
    description="Returns machine-readable compliance rules evaluated against detections and extractions. Accessible by Managers and Admins.",
)
def list_rules(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponse[RuleResponse]:
    """List compliance rules."""
    items, total = RuleService.list_rules(db, limit=limit, offset=offset, is_active=is_active)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/{rule_id}",
    response_model=RuleResponse,
    summary="Get Rule Details",
    description="Returns parameters, policy clause reference, and severity for a specific rule.",
)
def get_rule(
    rule_id: uuid.UUID,
    _user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RuleResponse:
    """Retrieve single compliance rule by ID."""
    return RuleService.get_rule(db, rule_id)


@router.post(
    "",
    response_model=RuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Compliance Rule (Admin Only)",
    description="Defines a new machine-readable compliance rule linked to an authoritative policy reference.",
)
def create_rule(
    payload: RuleCreate,
    _user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> RuleResponse:
    """Register a new compliance rule."""
    return RuleService.create_rule(db, payload)


@router.put(
    "/{rule_id}",
    response_model=RuleResponse,
    summary="Update Compliance Rule (Admin Only)",
    description="Modifies rule parameters, threshold, or active status.",
)
def update_rule(
    rule_id: uuid.UUID,
    payload: RuleUpdate,
    _user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> RuleResponse:
    """Update rule configuration."""
    return RuleService.update_rule(db, rule_id, payload)

