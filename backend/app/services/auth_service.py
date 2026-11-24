from datetime import datetime, timezone
from typing import List, Optional
import uuid
from sqlalchemy.orm import Session
from app.config.settings import get_settings
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError, UnauthorizedError
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.users_sites import RefreshToken, SiteMembership, User
from app.schemas.auth import (
    TokenRefreshResponse,
    TokenResponse,
    UserSummary,
)

logger = get_logger("app.services.auth")
settings = get_settings()


class AuthService:
    """Authentication and Role-Based Access Control Service."""

    @staticmethod
    def seed_default_passwords_if_needed(db: Session, default_password: str = "SiteSense@2026") -> int:
        """Seed default password for initial seed users who currently have null password_hash."""
        users_without_pwd = db.query(User).filter(User.password_hash.is_(None)).all()
        if not users_without_pwd:
            return 0

        hashed = hash_password(default_password)
        for u in users_without_pwd:
            u.password_hash = hashed
            logger.info(f"Initialized default password for seed user: {u.email} ({u.role})")
        db.commit()
        return len(users_without_pwd)

    @classmethod
    def authenticate_user(cls, db: Session, email: str, password: str) -> User:
        """Authenticate user credentials and return the active User record."""
        # Check if seed users need default passwords initialized
        cls.seed_default_passwords_if_needed(db)

        user = db.query(User).filter(User.email == email.strip().lower()).first()
        if not user:
            logger.warning(f"Failed login attempt: email '{email}' not found")
            raise UnauthorizedError(
                message="Invalid email or password",
                detail={"field": "credentials"},
            )

        if not verify_password(password, user.password_hash):
            logger.warning(f"Failed login attempt: incorrect password for user '{email}'")
            raise UnauthorizedError(
                message="Invalid email or password",
                detail={"field": "credentials"},
            )

        return user

    @classmethod
    def create_token_pair(cls, db: Session, user: User) -> TokenResponse:
        """Issue access and refresh tokens, recording the refresh token in the database."""
        access_token = create_access_token(
            subject=user.id, email=user.email, role=user.role
        )
        refresh_token_str = create_refresh_token(subject=user.id)

        # Decode refresh token to extract exact expiration timestamp
        payload = decode_token(refresh_token_str)
        expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

        # Store refresh token in database
        db_refresh_token = RefreshToken(
            user_id=user.id,
            token=refresh_token_str,
            expires_at=expires_at,
            revoked=False,
        )
        db.add(db_refresh_token)
        db.commit()

        user_summary = UserSummary(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
        )

        return TokenResponse(
            token=access_token,
            access_token=access_token,
            refresh_token=refresh_token_str,
            token_type="bearer",
            expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            user=user_summary,
        )

    @classmethod
    def refresh_access_token(cls, db: Session, refresh_token_str: str) -> TokenRefreshResponse:
        """Rotate refresh token: validate existing token, revoke it, and issue a fresh pair."""
        payload = decode_token(refresh_token_str)
        if payload.get("type") != "refresh":
            raise UnauthorizedError(message="Invalid token type. Refresh token required.")

        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedError(message="Malformed refresh token payload.")

        # Lookup token in database
        db_token = (
            db.query(RefreshToken)
            .filter(RefreshToken.token == refresh_token_str)
            .first()
        )
        if not db_token:
            raise UnauthorizedError(message="Refresh token not recognized or already revoked.")

        if db_token.revoked:
            logger.warning(f"Attempt to reuse revoked refresh token for user {user_id}")
            raise UnauthorizedError(message="Refresh token has been revoked. Please log in again.")

        # Normalize datetime for offset-naive (SQLite) and offset-aware (PostgreSQL)
        token_expires_at = db_token.expires_at
        if token_expires_at.tzinfo is None:
            token_expires_at = token_expires_at.replace(tzinfo=timezone.utc)

        if token_expires_at < datetime.now(timezone.utc):
            raise UnauthorizedError(message="Refresh token has expired. Please log in again.")

        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        if not user:
            raise UnauthorizedError(message="User associated with token no longer exists.")

        # Revoke the used refresh token (Token Rotation Security)
        db_token.revoked = True

        # Generate new token pair
        new_access_token = create_access_token(
            subject=user.id, email=user.email, role=user.role
        )
        new_refresh_token = create_refresh_token(subject=user.id)
        new_payload = decode_token(new_refresh_token)
        new_expires_at = datetime.fromtimestamp(new_payload["exp"], tz=timezone.utc)

        db_new_token = RefreshToken(
            user_id=user.id,
            token=new_refresh_token,
            expires_at=new_expires_at,
            revoked=False,
        )
        db.add(db_new_token)
        db.commit()

        return TokenRefreshResponse(
            token=new_access_token,
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        )

    @classmethod
    def revoke_refresh_token(cls, db: Session, refresh_token_str: str) -> bool:
        """Mark refresh token as revoked upon user logout."""
        db_token = (
            db.query(RefreshToken)
            .filter(RefreshToken.token == refresh_token_str)
            .first()
        )
        if db_token:
            db_token.revoked = True
            db.commit()
            return True
        return False

    @classmethod
    def change_password(
        cls, db: Session, user: User, current_password: str, new_password: str
    ) -> None:
        """Verify current password, update password hash, and revoke all active refresh tokens."""
        if not verify_password(current_password, user.password_hash):
            raise BadRequestError(message="Current password does not match.")

        user.password_hash = hash_password(new_password)

        # Revoke all active refresh tokens for this user
        db.query(RefreshToken).filter(
            RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False)
        ).update({"revoked": True})

        db.commit()
        logger.info(f"Password changed and sessions revoked for user: {user.email}")
