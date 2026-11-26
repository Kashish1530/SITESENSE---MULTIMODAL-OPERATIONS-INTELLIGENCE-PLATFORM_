from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.schemas.common import HealthResponse
from app.services.health_service import HealthService

router = APIRouter()


@router.get(
    "",
    response_model=HealthResponse,
    summary="Comprehensive Health Check",
    description="Returns backend uptime, environment, and verifies database connectivity with latency measurement.",
)
def get_health() -> HealthResponse:
    """Check backend operational health and database connection."""
    health_data = HealthService.check_health()
    if not health_data.database.connected:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=health_data.model_dump(mode="json"),
        )
    return health_data


@router.get(
    "/live",
    summary="Liveness Probe",
    description="Simple probe for container orchestrators to verify the process is alive.",
)
def get_liveness() -> dict:
    return {"status": "alive", "uptime_seconds": HealthService.get_uptime_seconds()}


@router.get(
    "/ready",
    summary="Readiness Probe",
    description="Readiness probe confirming the backend is ready to accept traffic and the database is accessible.",
)
def get_readiness() -> dict:
    health_data = HealthService.check_health()
    if not health_data.database.connected:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "reason": "Database connection unavailable"},
        )
    return {
        "status": "ready",
        "database": health_data.database.dialect,
        "latency_ms": health_data.database.latency_ms,
    }
