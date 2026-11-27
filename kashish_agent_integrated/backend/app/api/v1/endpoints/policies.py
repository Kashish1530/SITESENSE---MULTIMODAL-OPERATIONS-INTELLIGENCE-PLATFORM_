from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.models.knowledge_compliance import Policy, PolicyChunk
from app.models.users_sites import User

router = APIRouter()


class PolicySummaryResponse(BaseModel):
    id: uuid.UUID
    title: str
    version: str
    source_file: str
    effective_date: Optional[str] = None
    description: Optional[str] = None
    status: str
    chunks_count: int = 0

    model_config = ConfigDict(from_attributes=True)


@router.get(
    "",
    response_model=Dict[str, Any],
    summary="List Operational Policies",
    description="Returns authoritative operational and compliance policy documents stored in the database.",
)
def list_policies(
    q: Optional[str] = Query(None, description="Optional search query across title, source file, or description"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """List operational policy documents from the database."""
    query = db.query(Policy)
    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(
            (Policy.title.ilike(term))
            | (Policy.source_file.ilike(term))
            | (Policy.description.ilike(term))
        )

    total = query.count()
    policies = query.order_by(Policy.created_at.desc()).offset(offset).limit(limit).all()

    chunk_counts = dict(
        db.query(PolicyChunk.policy_id, func.count(PolicyChunk.id))
        .group_by(PolicyChunk.policy_id)
        .all()
    )

    items: List[Dict[str, Any]] = []
    for p in policies:
        items.append(
            PolicySummaryResponse(
                id=p.id,
                title=p.title,
                version=p.version,
                source_file=p.source_file,
                effective_date=p.effective_date.isoformat() if p.effective_date else None,
                description=p.description,
                status=p.status,
                chunks_count=chunk_counts.get(p.id, 0),
            ).model_dump(mode="json")
        )

    return {"items": items, "total": total, "limit": limit, "offset": offset}
