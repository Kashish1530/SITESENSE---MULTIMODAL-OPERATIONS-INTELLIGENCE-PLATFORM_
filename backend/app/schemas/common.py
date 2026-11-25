from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Uniform error detail matching SiteSense API specification:
    { "error": { "code": str, "message": str, "detail": Any } }
    """
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error description")
    detail: Optional[Any] = Field(default=None, description="Optional extra error context")


class ErrorResponse(BaseModel):
    """Enveloping error schema."""
    error: ErrorDetail


class StandardResponse(BaseModel, Generic[T]):
    """Standard success envelope for single item responses."""
    success: bool = Field(default=True, description="Operation success status")
    data: Optional[T] = Field(default=None, description="Payload data")
    message: Optional[str] = Field(default=None, description="Optional user-facing message")

    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard pagination envelope for list endpoints."""
    items: List[T] = Field(default_factory=list, description="List of items for current page")
    total: int = Field(..., description="Total items matching query")
    limit: int = Field(default=50, description="Items requested per page")
    offset: int = Field(default=0, description="Items offset from start")

    model_config = ConfigDict(from_attributes=True)


class DatabaseHealth(BaseModel):
    """Database connectivity health status."""
    status: str
    connected: bool
    dialect: str
    latency_ms: float
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Comprehensive health check response schema."""
    status: str = Field(..., description="Overall service status (healthy / degraded / unhealthy)")
    timestamp: datetime = Field(..., description="Server timestamp (ISO 8601 UTC)")
    environment: str = Field(..., description="Runtime environment (development / production)")
    version: str = Field(..., description="Backend release version")
    database: DatabaseHealth = Field(..., description="Database connection health")
    uptime_seconds: float = Field(..., description="Server process uptime in seconds")


class ModuleInfo(BaseModel):
    """Status and contract metadata for an individual SiteSense module."""
    code: str
    name: str
    category: str
    supported: bool
    status: str
    notes: str


class ModuleReadinessResponse(BaseModel):
    """Summary of all 8 core platform modules and their backend support status."""
    total_modules: int
    active_integration_layer: str
    modules: List[ModuleInfo]
