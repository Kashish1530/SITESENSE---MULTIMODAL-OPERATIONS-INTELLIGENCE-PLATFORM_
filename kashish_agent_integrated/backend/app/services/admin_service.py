from typing import List, Optional, Tuple
import uuid
from sqlalchemy.orm import Session
from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.agent_review import Ticket
from app.models.inspections_media import Inspection
from app.models.knowledge_compliance import Finding
from app.models.system import AuditLog
from app.models.users_sites import Site, SiteMembership, User
from app.schemas.admin import (
    AdminStatsResponse,
    AdminUserCreate,
    AdminUserResponse,
    AdminUserUpdate,
    AuditLogResponse,
)


class AdminService:
    """Service managing administration, user provisioning, system audits, and metrics."""

    @classmethod
    def list_users(
        cls,
        db: Session,
        *,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[AdminUserResponse], int]:
        """List system users with site memberships."""
        query = db.query(User)
        if role:
            query = query.filter(User.role == role.strip().lower())
        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        total = query.count()
        users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()

        responses: List[AdminUserResponse] = []
        for u in users:
            site_ids = [m.site_id for m in u.site_memberships]
            responses.append(
                AdminUserResponse(
                    id=u.id,
                    name=u.name,
                    email=u.email,
                    role=u.role,
                    is_active=u.is_active,
                    site_ids=site_ids,
                    created_at=u.created_at,
                    updated_at=u.updated_at,
                )
            )
        return responses, total

    @classmethod
    def create_user(cls, db: Session, payload: AdminUserCreate, admin_user: User) -> AdminUserResponse:
        """Provision a new user and assign site membership."""
        existing = db.query(User).filter(User.email == payload.email.strip().lower()).first()
        if existing:
            raise ConflictError(message=f"User with email '{payload.email}' already exists.")

        hashed_pw = hash_password(payload.password)
        new_user = User(
            name=payload.name.strip(),
            email=payload.email.strip().lower(),
            role=payload.role.strip().lower(),
            password_hash=hashed_pw,
            is_active=True,
        )
        db.add(new_user)
        db.flush()

        site_ids: List[uuid.UUID] = []
        if payload.site_id:
            site = db.query(Site).filter(Site.id == payload.site_id).first()
            if not site:
                raise NotFoundError(message=f"Site '{payload.site_id}' not found.")
            membership = SiteMembership(user_id=new_user.id, site_id=payload.site_id)
            db.add(membership)
            site_ids.append(payload.site_id)

        # Audit log
        audit = AuditLog(
            user_id=admin_user.id,
            action="create_user",
            entity_type="user",
            entity_id=new_user.id,
            details={"email": new_user.email, "role": new_user.role},
        )
        db.add(audit)

        db.commit()
        db.refresh(new_user)

        return AdminUserResponse(
            id=new_user.id,
            name=new_user.name,
            email=new_user.email,
            role=new_user.role,
            is_active=new_user.is_active,
            site_ids=site_ids,
            created_at=new_user.created_at,
            updated_at=new_user.updated_at,
        )

    @classmethod
    def update_user(
        cls, db: Session, user_id: uuid.UUID, payload: AdminUserUpdate, admin_user: User
    ) -> AdminUserResponse:
        """Update user role, status, or site assignment."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundError(message=f"User '{user_id}' not found.")

        changes = {}
        if payload.name is not None:
            changes["name"] = {"old": user.name, "new": payload.name}
            user.name = payload.name.strip()
        if payload.role is not None:
            changes["role"] = {"old": user.role, "new": payload.role}
            user.role = payload.role.strip().lower()
        if payload.is_active is not None:
            changes["is_active"] = {"old": user.is_active, "new": payload.is_active}
            user.is_active = payload.is_active

        if payload.site_id is not None:
            site = db.query(Site).filter(Site.id == payload.site_id).first()
            if not site:
                raise NotFoundError(message=f"Site '{payload.site_id}' not found.")
            existing_mem = (
                db.query(SiteMembership)
                .filter(SiteMembership.user_id == user.id, SiteMembership.site_id == payload.site_id)
                .first()
            )
            if not existing_mem:
                db.add(SiteMembership(user_id=user.id, site_id=payload.site_id))
                changes["added_site_id"] = str(payload.site_id)

        # Audit log
        if changes:
            audit = AuditLog(
                user_id=admin_user.id,
                action="update_user",
                entity_type="user",
                entity_id=user.id,
                details=changes,
            )
            db.add(audit)

        db.commit()
        db.refresh(user)

        site_ids = [m.site_id for m in user.site_memberships]
        return AdminUserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            site_ids=site_ids,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    @classmethod
    def list_audit_logs(
        cls,
        db: Session,
        *,
        user_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[AuditLogResponse], int]:
        """Retrieve system audit logs."""
        query = db.query(AuditLog)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action.strip().lower())

        total = query.count()
        logs = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
        return [AuditLogResponse.model_validate(log) for log in logs], total

    @classmethod
    def get_system_stats(cls, db: Session) -> AdminStatsResponse:
        """Calculate system-wide platform statistics."""
        total_users = db.query(User).count()
        total_sites = db.query(Site).count()
        total_inspections = db.query(Inspection).count()
        total_findings = db.query(Finding).count()
        total_tickets = db.query(Ticket).count()

        # Compute average pass rate
        inspections = db.query(Inspection.pass_rate).filter(Inspection.pass_rate != None).all()  # noqa: E711
        if inspections:
            rates = [r[0] for r in inspections if r[0] is not None]
            pass_rate = round(sum(rates) / len(rates), 2) if rates else 100.0
        else:
            pass_rate = 100.0

        return AdminStatsResponse(
            total_users=total_users,
            total_sites=total_sites,
            total_inspections=total_inspections,
            total_findings=total_findings,
            total_tickets=total_tickets,
            pass_rate=pass_rate,
        )
