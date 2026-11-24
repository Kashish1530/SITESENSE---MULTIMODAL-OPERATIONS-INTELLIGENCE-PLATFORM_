from typing import Optional
from fastapi import APIRouter, Body, Depends, Request, status
from sqlalchemy.orm import Session
from app.api.deps import (
    get_current_user,
    get_db,
    require_admin,
    require_manager,
)
from app.core.exceptions import BadRequestError
from app.models.users_sites import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutResponse,
    RefreshTokenRequest,
    TokenRefreshResponse,
    TokenResponse,
    UserSummary,
)
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate User and Obtain Token Pair",
    description="Validates email/username and password via JSON body or OAuth2 Form, issuing a JWT access token and a refresh token. Matches contract: { token, user: { id, name, role } }",
)
async def login(
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate and return JWT access token, refresh token, and user profile."""
    content_type = request.headers.get("content-type", "").lower()
    email = None
    password = None

    if "application/json" in content_type:
        try:
            body = await request.json()
            email = body.get("email") or body.get("username")
            password = body.get("password")
        except Exception:
            raise BadRequestError(message="Invalid JSON payload.")
    else:
        try:
            form = await request.form()
            email = form.get("username") or form.get("email")
            password = form.get("password")
        except Exception:
            raise BadRequestError(message="Invalid form data.")

    if not email or not password:
        raise BadRequestError(message="Email and password are required.")

    user = AuthService.authenticate_user(db, str(email).strip(), str(password))
    return AuthService.create_token_pair(db, user)


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    summary="Rotate Refresh Token and Obtain Fresh Access Token",
    description="Validates active refresh token, revokes it (rotation protection), and issues a new access token.",
)
def refresh_token(
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> TokenRefreshResponse:
    """Rotate refresh token and issue new access token."""
    return AuthService.refresh_access_token(db, payload.refresh_token)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Log Out and Revoke Active Refresh Token",
    description="Explicitly revokes the refresh token in the database so it can no longer be used.",
)
def logout(
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> LogoutResponse:
    """Revoke refresh token on logout."""
    AuthService.revoke_refresh_token(db, payload.refresh_token)
    return LogoutResponse(
        success=True,
        message="Session terminated and refresh token revoked successfully.",
    )


@router.get(
    "/me",
    response_model=UserSummary,
    summary="Get Authenticated User Profile",
    description="Returns the current authenticated user's ID, name, email, and role.",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserSummary:
    """Return authenticated caller identity."""
    return UserSummary(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
    )


@router.post(
    "/change-password",
    summary="Change User Password",
    description="Validates current password, applies new password hash, and invalidates all existing sessions.",
)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Change user password and revoke existing refresh tokens."""
    AuthService.change_password(
        db, current_user, payload.current_password, payload.new_password
    )
    return {"success": True, "message": "Password changed successfully. Please log in with your new credentials."}


# ------------------------------------------------------------------------------
# RBAC Verification Endpoints (Demonstrating API-level Role Enforcement)
# ------------------------------------------------------------------------------
@router.get(
    "/rbac-test/manager-only",
    summary="RBAC Test: Manager & Admin Access Only",
    description="Enforces that Field Users and Reviewers receive HTTP 403 Forbidden, while Managers and Admins succeed.",
)
def manager_only_endpoint(
    current_user: User = Depends(require_manager),
) -> dict:
    """Protected endpoint accessible only by Manager or Admin roles."""
    return {
        "status": "granted",
        "message": f"Welcome {current_user.role.title()} {current_user.name}. You have managerial clearance.",
        "user_id": str(current_user.id),
        "role": current_user.role,
    }


@router.get(
    "/rbac-test/admin-only",
    summary="RBAC Test: Admin Access Only",
    description="Enforces that only Admin role can access system configuration.",
)
def admin_only_endpoint(
    current_user: User = Depends(require_admin),
) -> dict:
    """Protected endpoint accessible strictly by Admin role."""
    return {
        "status": "granted",
        "message": f"Welcome Administrator {current_user.name}.",
        "user_id": str(current_user.id),
        "role": current_user.role,
    }
