from datetime import date
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_policy_uploader
from app.models.knowledge_compliance import Policy, PolicyChunk
from app.models.users_sites import User
from app.services.policy_ingestion_service import PolicyIngestionService

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
    site_id: Optional[uuid.UUID] = None
    file_path: Optional[str] = None

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
                site_id=p.site_id,
                file_path=p.file_path,
            ).model_dump(mode="json")
        )

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get(
    "/{policy_id}",
    summary="Get Policy Details",
    description="Returns detailed metadata and chunk counts for a specific policy document.",
)
def get_policy(
    policy_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy document not found.")

    chunks_count = db.query(func.count(PolicyChunk.id)).filter(PolicyChunk.policy_id == policy_id).scalar() or 0

    return PolicySummaryResponse(
        id=policy.id,
        title=policy.title,
        version=policy.version,
        source_file=policy.source_file,
        effective_date=policy.effective_date.isoformat() if policy.effective_date else None,
        description=policy.description,
        status=policy.status,
        chunks_count=chunks_count,
        site_id=policy.site_id,
        file_path=policy.file_path,
    ).model_dump(mode="json")


@router.get(
    "/{policy_id}/chunks",
    summary="Get Chunks for Policy",
    description="Returns all extracted and vectorized policy chunks for inspection by admin/reviewers.",
)
def get_policy_chunks(
    policy_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    chunks = (
        db.query(PolicyChunk)
        .filter(PolicyChunk.policy_id == policy_id)
        .order_by(PolicyChunk.chunk_index.asc())
        .all()
    )
    return [
        {
            "id": str(c.id),
            "chunk_index": c.chunk_index,
            "page_number": c.page_number,
            "section_heading": c.section_heading,
            "content": c.content,
            "embedding_id": c.embedding_id,
            "metadata_json": c.metadata_json,
        }
        for c in chunks
    ]


@router.post(
    "/upload",
    summary="Upload and ingest a policy document",
    description="Uploads and processes an operational policy PDF/DOCX for RAG chunking and vector storage.",
)
def upload_policy(
    site_id: uuid.UUID = Form(...),
    title: str = Form(...),
    version: str = Form("1.0"),
    effective_date: Optional[date] = Form(None),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user=Depends(require_policy_uploader),
    db: Session = Depends(get_db),
):
    try:
        return PolicyIngestionService.ingest(
            db=db,
            site_id=site_id,
            current_user=current_user,
            upload=file,
            title=title,
            version=version,
            effective_date=effective_date,
            description=description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Policy ingestion failed. Check backend logs.",
        )
