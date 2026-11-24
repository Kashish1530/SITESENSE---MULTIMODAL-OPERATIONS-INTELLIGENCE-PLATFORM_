from fastapi import APIRouter
from app.api.v1.endpoints import (
    admin,
    auth,
    chat,
    findings,
    health,
    inspections,
    jobs,
    media,
    modules,
    reports,
    reviews,
    rules,
    sites,
    tickets,
    zones,
)

api_router = APIRouter()

# Core diagnostic and module registration
api_router.include_router(health.router, prefix="/health", tags=["Health & Diagnostics"])
api_router.include_router(modules.router, prefix="/modules", tags=["Platform Modules"])

# Authentication & Access Control (Component 3)
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & RBAC"])

# REST API Layer (Core Specification Surface)
api_router.include_router(sites.router, prefix="/sites", tags=["Sites & Locations"])
api_router.include_router(media.router, prefix="/media", tags=["Media & File Upload"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Job Status & Processing"])
api_router.include_router(inspections.router, prefix="/inspections", tags=["Inspections & Evidence"])
api_router.include_router(findings.router, prefix="/findings", tags=["Compliance Findings"])
api_router.include_router(chat.router, prefix="/chat", tags=["Intelligence Chat"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["Human Review Queue"])
api_router.include_router(reports.router, prefix="/reports", tags=["Inspection Reports"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin & System Audit"])

# Domain & Orchestration Engines
api_router.include_router(rules.router, prefix="/rules", tags=["Compliance Rules"])
api_router.include_router(zones.router, prefix="/zones", tags=["Zone Engine & Geometries"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["Tickets & Approvals"])
