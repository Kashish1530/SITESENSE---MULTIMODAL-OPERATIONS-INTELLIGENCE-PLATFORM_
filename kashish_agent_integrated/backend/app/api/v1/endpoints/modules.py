from fastapi import APIRouter
from app.schemas.common import ModuleReadinessResponse
from app.services.health_service import HealthService

router = APIRouter()


@router.get(
    "",
    response_model=ModuleReadinessResponse,
    summary="Platform Modules Integration Status",
    description="Lists the integration and orchestration status for all 8 SiteSense modules (M1 - M8).",
)
def get_modules() -> ModuleReadinessResponse:
    """Retrieve integration readiness for M1 through M8."""
    return HealthService.get_module_readiness()
