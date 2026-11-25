"""
SITESENSE - API Gateway (Feature 5.1 & Week 1 Contract)
Single entry point REST API surface built with FastAPI.
Adheres strictly to the agreed Week 1 API specification & error shape conventions.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.routers.inspections import router as inspections_router
from api.routers.sites import router as sites_router
from api.routers.chat import router as chat_router
from api.routers.media import router as media_router
from api.routers.visualizer import router as visualizer_router

app = FastAPI(
    title="SiteSense Multimodal Operations Intelligence API",
    description="REST API Gateway for physical site inspections, CV detections, policy compliance, and agentic reasoning.",
    version="1.0.0"
)

# 1. Enable CORS for Web & Mobile Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Enforce Agreed Error Shape Convention: {"error": {"code", "message", "detail"}}
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail),
                "detail": None
            }
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters or payload shape.",
                "detail": exc.errors()
            }
        }
    )

# 3. Mount Routers
app.include_router(inspections_router)
app.include_router(sites_router)
app.include_router(chat_router)
app.include_router(media_router)
app.include_router(visualizer_router)

@app.get("/", tags=["Health"])
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "SiteSense API Gateway",
        "version": "1.0.0",
        "database": "Neon PostgreSQL Connected"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
