from typing import Generator, List, Optional
import uuid
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config.settings import get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.users_sites import SiteMembership, User

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False
)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Dependency that extracts and validates the Bearer token, returning the authenticated User."""
    if not token:
        raise UnauthorizedError(
            message="Authentication required. Please provide a Bearer token in the Authorization header.",
            detail={"header": "Authorization"},
        )

    payload = decode_token(token)
    if payload.get("type") != "access":
        raise UnauthorizedError(
            message="Invalid token type. Access token expected.",
            detail={"expected": "access", "received": payload.get("type")},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedError(message="Token payload is missing subject.")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedError(message="Malformed user ID in token.")

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise UnauthorizedError(message="User not found or account removed.")

    return user


class RoleChecker:
    """Callable dependency to enforce Role-Based Access Control (RBAC)."""

    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = [r.lower() for r in allowed_roles]

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        user_role = (current_user.role or "").lower()

        # Admin role possesses universal superuser access
        if user_role == "admin" or user_role in self.allowed_roles:
            return current_user

        raise ForbiddenError(
            message=f"Access forbidden: role '{current_user.role}' lacks permission for this action.",
            detail={
                "user_role": current_user.role,
                "required_roles": self.allowed_roles,
            },
        )


# Role-specific dependency shortcuts
require_admin = RoleChecker(["admin"])
require_manager = RoleChecker(["admin", "manager"])
require_policy_uploader = RoleChecker(["admin", "manager", "reviewer", "supervisor"])
require_reviewer = RoleChecker(["admin", "reviewer", "supervisor"])
require_field = RoleChecker(["admin", "manager", "field", "reviewer", "supervisor", "employee"])


def verify_site_access(site_id: uuid.UUID, user: User, db: Session) -> bool:
    """Verify that user is authorized to view or modify resources for a given site.
    Admins, Managers, and Supervisors have authorized access; Field users are verified via site_memberships.
    """
    user_role = (user.role or "").lower()
    if user_role in ("admin", "manager", "supervisor"):
        return True

    # Check site membership
    membership = (
        db.query(SiteMembership)
        .filter(
            SiteMembership.site_id == site_id,
            SiteMembership.user_id == user.id,
        )
        .first()
    )

    if not membership:
        raise ForbiddenError(
            message="Access denied: you are not assigned to this site.",
            detail={"site_id": str(site_id), "user_id": str(user.id)},
        )

    return True
