from datetime import datetime, timezone
import time
from typing import Dict, List
from app.config.settings import get_settings
from app.db.session import check_database_connection
from app.schemas.common import DatabaseHealth, HealthResponse, ModuleInfo, ModuleReadinessResponse

settings = get_settings()
_start_time = time.time()


class HealthService:
    """Service to monitor system health, database state, and module readiness."""

    @staticmethod
    def get_uptime_seconds() -> float:
        return round(time.time() - _start_time, 2)

    @classmethod
    def check_health(cls) -> HealthResponse:
        """Perform comprehensive system and database health check."""
        db_check = check_database_connection()
        db_health = DatabaseHealth(
            status=db_check["status"],
            connected=db_check["connected"],
            dialect=db_check["dialect"],
            latency_ms=db_check["latency_ms"],
            error=db_check.get("error"),
        )

        overall_status = "healthy" if db_health.connected else "unhealthy"

        return HealthResponse(
            status=overall_status,
            timestamp=datetime.now(timezone.utc),
            environment=settings.ENVIRONMENT,
            version=settings.VERSION,
            database=db_health,
            uptime_seconds=cls.get_uptime_seconds(),
        )

    @classmethod
    def get_module_readiness(cls) -> ModuleReadinessResponse:
        """Return operational status and backend orchestration readiness for all 8 modules."""
        modules: List[ModuleInfo] = [
            ModuleInfo(
                code="M1",
                name="Computer Vision",
                category="Vision Service",
                supported=True,
                status="ready_for_integration",
                notes="Detections, tracking, zones, and annotated media contracts ready in data layer.",
            ),
            ModuleInfo(
                code="M2",
                name="Knowledge / Document Intelligence",
                category="Knowledge Service",
                supported=True,
                status="ready_for_integration",
                notes="Policy chunking, hybrid retrieval, and document extraction contracts mapped.",
            ),
            ModuleInfo(
                code="M3",
                name="GenAI",
                category="Generation Engine",
                supported=True,
                status="ready_for_integration",
                notes="Grounded Q&A, visual QA, and inspection report generation endpoints mapped.",
            ),
            ModuleInfo(
                code="M4",
                name="Agentic Layer",
                category="Orchestration",
                supported=True,
                status="ready_for_integration",
                notes="Tool registry, query router, execution loop, and audit trail hooks ready.",
            ),
            ModuleInfo(
                code="M5",
                name="Backend and APIs",
                category="Core Platform",
                supported=True,
                status="operational",
                notes="Base FastAPI foundation, versioning (/api/v1), database session, and logging active.",
            ),
            ModuleInfo(
                code="M6",
                name="Frontend",
                category="Client Application",
                supported=True,
                status="ready_for_integration",
                notes="Swagger OpenAPI specifications exposed for frontend mock and client generation.",
            ),
            ModuleInfo(
                code="M7",
                name="Evaluation and Observability",
                category="Telemetry",
                supported=True,
                status="ready_for_integration",
                notes="Correlation IDs, request timing middleware, and structured logging in place.",
            ),
            ModuleInfo(
                code="M8",
                name="Security, Deployment & Documentation",
                category="Operations",
                supported=True,
                status="ready_for_integration",
                notes="Pydantic settings loaded from environment variables; zero credentials in source.",
            ),
        ]

        return ModuleReadinessResponse(
            total_modules=len(modules),
            active_integration_layer="FastAPI 0.110+ Orchestration Layer",
            modules=modules,
        )
