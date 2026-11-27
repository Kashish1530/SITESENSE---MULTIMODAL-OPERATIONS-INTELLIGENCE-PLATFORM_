from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db, require_admin, require_manager
from app.models.users_sites import User
from app.schemas.admin import (
    AdminStatsResponse,
    AdminUserCreate,
    AdminUserResponse,
    AdminUserUpdate,
    AuditLogResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.admin_service import AdminService

router = APIRouter()


@router.get(
    "/directory",
    response_model=PaginatedResponse[AdminUserResponse],
    summary="List Organization User Directory",
    description="Returns active platform users and site memberships for authenticated workspace views.",
)
def list_user_directory(
    role: Optional[str] = Query(None, description="Filter by role (admin, manager, field, reviewer)"),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponse[AdminUserResponse]:
    """Authenticated read-only user directory backed by PostgreSQL."""
    items, total = AdminService.list_users(
        db, role=role, is_active=True, limit=limit, offset=offset
    )
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/users",
    response_model=PaginatedResponse[AdminUserResponse],
    summary="List All Platform Users (Admin Only)",
    description="Returns all registered users with their assigned roles, active status, and site memberships.",
)
def list_users(
    role: Optional[str] = Query(None, description="Filter by role (admin, manager, field, reviewer)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PaginatedResponse[AdminUserResponse]:
    """Admin endpoint to list system users."""
    items, total = AdminService.list_users(
        db, role=role, is_active=is_active, limit=limit, offset=offset
    )
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.post(
    "/users",
    response_model=AdminUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Provision New User (Admin Only)",
    description="Creates a new user account with hashed password and optional site membership assignment.",
)
def create_user(
    payload: AdminUserCreate,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserResponse:
    """Admin endpoint to provision a new user."""
    return AdminService.create_user(db, payload, admin_user)


@router.patch(
    "/users/{user_id}",
    response_model=AdminUserResponse,
    summary="Update User Role or Status (Admin Only)",
    description="Updates user attributes (role, active state, site assignment). Automatically creates audit trail.",
)
def update_user(
    user_id: uuid.UUID,
    payload: AdminUserUpdate,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserResponse:
    """Admin endpoint to update user settings."""
    return AdminService.update_user(db, user_id, payload, admin_user)


@router.get(
    "/audit-logs",
    response_model=PaginatedResponse[AuditLogResponse],
    summary="Query System Audit Logs (Admin Only)",
    description="Retrieves system audit log entries recording administrative mutations, reviews, and security events.",
)
def list_audit_logs(
    user_id: Optional[uuid.UUID] = Query(None, description="Filter by user ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PaginatedResponse[AuditLogResponse]:
    """Admin endpoint to inspect system audit trail."""
    items, total = AdminService.list_audit_logs(
        db, user_id=user_id, action=action, limit=limit, offset=offset
    )
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    summary="Platform Overview Metrics",
    description="Aggregates platform metrics (total users, sites, inspections, findings, tickets, and overall pass rate).",
)
def get_system_stats(
    _manager: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> AdminStatsResponse:
    """Retrieve platform-wide operational statistics."""
    return AdminService.get_system_stats(db)
