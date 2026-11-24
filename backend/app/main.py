from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, RedirectResponse
from app.api.v1.router import api_router
from app.config.settings import get_settings
from app.core.handlers import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.core.middleware import RequestLoggingMiddleware
from app.db.session import check_database_connection

settings = get_settings()
logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager to initialize logging, database, and background services."""
    # 1. Initialize logging
    setup_logging(settings.LOG_LEVEL)
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")

    # 2. Verify database connection
    db_status = check_database_connection()
    if db_status["connected"]:
        logger.info(
            f"Database connected successfully: {db_status['dialect']} (latency: {db_status['latency_ms']}ms)"
        )
    else:
        logger.error(f"Database connection failed on startup: {db_status.get('error')}")

    logger.info(f"API v1 endpoints mounted under {settings.API_V1_PREFIX}")
    logger.info(f"Swagger Documentation available at /docs")

    yield

    # Shutdown
    logger.info("Shutting down SiteSense backend...")


def create_application() -> FastAPI:
    """Application factory creating the configured FastAPI instance."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="""
# SiteSense - Multimodal Operations Intelligence Platform

The backend serves as the **central integration and orchestration layer** connecting:
* **M1 - Computer Vision**: Detections, tracking, zone analysis, and annotated evidence.
* **M2 - Knowledge / Document Intelligence**: Hybrid retrieval, chunking, and document extraction.
* **M3 - GenAI**: Grounded Q&A, citations, multimodal visual QA, and report generation.
* **M4 - Agentic Layer**: ReAct loop, tool registry, query routing, and human-in-the-loop approvals.
* **M5 - Backend and APIs**: Auth & RBAC, job queue, streaming chat (SSE), and audit trails.
* **M6 - Frontend**: Web app endpoints, review queue, and management dashboards.
* **M7 - Evaluation & Observability**: Tracing, latency tracking, and golden test benchmarks.
* **M8 - Security, Deployment & Documentation**: Central config, PII handling, and container deployment.

---
### API Conventions
- **Errors**: Uniform shape `{ "error": { "code": str, "message": str, "detail": Any } }`
- **Timestamps**: ISO 8601 UTC
- **Bounding Boxes**: `[x1, y1, x2, y2]` absolute pixel coordinates
        """,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
        openapi_tags=[
            {
                "name": "Authentication & RBAC",
                "description": "JWT authentication, token refresh rotation, and role-based access control.",
            },
            {
                "name": "Sites & Locations",
                "description": "Physical sites, warehouses, stores, and site membership management.",
            },
            {
                "name": "Media & File Upload",
                "description": "Upload, stream, annotate, and manage inspection media and evidence.",
            },
            {
                "name": "Job Status & Processing",
                "description": "Asynchronous background ingestion, inference, and reporting job execution tracking.",
            },
            {
                "name": "Inspections & Evidence",
                "description": "Site visits, media evidence, detections, document extractions, and findings.",
            },
            {
                "name": "Compliance Findings",
                "description": "Compliance evaluation outcomes, severity classification, and defect tracking.",
            },
            {
                "name": "Intelligence Chat",
                "description": "Conversational assistant with multimodal query handling and grounded policy citations.",
            },
            {
                "name": "Human Review Queue",
                "description": "Human-in-the-loop verification for low-confidence detections, extractions, and findings.",
            },
            {
                "name": "Inspection Reports",
                "description": "Official inspection compliance reports compilation, export, and download.",
            },
            {
                "name": "Admin & System Audit",
                "description": "User provisioning, site assignments, system audit logs, and platform metrics.",
            },
            {
                "name": "Compliance Rules",
                "description": "Machine-readable compliance rules evaluating detections against company policies.",
            },
            {
                "name": "Zone Engine & Geometries",
                "description": "Spatial polygon clear zones and counting line configurations.",
            },
            {
                "name": "Tickets & Approvals",
                "description": "Remediation tickets with human-in-the-loop approval workflows.",
            },
            {
                "name": "Health & Diagnostics",
                "description": "System health, database connectivity checks, and readiness probes.",
            },
            {
                "name": "Platform Modules",
                "description": "Integration and orchestration status across modules M1 through M8.",
            },
        ],
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request correlation & logging middleware
    app.add_middleware(RequestLoggingMiddleware)

    # Register centralized exception handlers
    register_exception_handlers(app)

    # Mount API v1 router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Home API page — Default opening page
    @app.get("/", response_class=PlainTextResponse, include_in_schema=False)
    def home_page():
        return "welcome to sitesense"

    return app


app = create_application()
