import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    """Payload for user authentication."""
    email: EmailStr = Field(..., description="Registered user email", example="manager@sitesense.io")
    password: str = Field(..., min_length=4, description="User password", example="SiteSense@2026")


class UserSummary(BaseModel):
    """User representation returned in auth responses."""
    id: uuid.UUID
    name: str
    email: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """OAuth2 / JWT token response matching SiteSense API contract:
    { token: access_token, user: { id, name, role } }
    """
    token: str = Field(..., description="JWT Bearer access token")
    access_token: str = Field(..., description="Standard access token field")
    refresh_token: str = Field(..., description="Long-lived refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in_minutes: int = Field(..., description="Token lifespan in minutes")
    user: UserSummary = Field(..., description="Authenticated user summary")


class RefreshTokenRequest(BaseModel):
    """Request payload to rotate refresh tokens."""
    refresh_token: str = Field(..., description="Valid active refresh token string")


class TokenRefreshResponse(BaseModel):
    """Rotated access and refresh tokens."""
    token: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class ChangePasswordRequest(BaseModel):
    """Payload to change user password."""
    current_password: str = Field(..., description="Current plain password")
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")


class LogoutResponse(BaseModel):
    """Confirmation of successful logout and session revocation."""
    success: bool = True
    message: str = "Successfully logged out and revoked refresh token."
