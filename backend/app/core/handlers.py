from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger("app.handlers")


def register_exception_handlers(app: FastAPI) -> None:
    """Register uniform error handlers for all exceptions in accordance with SiteSense API spec:
    { "error": { "code": str, "message": str, "detail": Any } }
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        logger.warning(
            f"AppException: {exc.code} - {exc.message} on {request.method} {request.url.path}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "detail": exc.detail,
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            422: "UNPROCESSABLE_ENTITY",
            500: "INTERNAL_SERVER_ERROR",
            502: "BAD_GATEWAY",
            503: "SERVICE_UNAVAILABLE",
        }
        code = code_map.get(exc.status_code, "HTTP_ERROR")
        detail = exc.detail if isinstance(exc.detail, (dict, list)) else None
        message = str(exc.detail) if not detail else "HTTP Error"

        logger.warning(f"HTTPException: {code} - {message} on {request.method} {request.url.path}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "detail": detail,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Simplify validation error messages for clean client consumption
        errors = []
        for err in exc.errors():
            loc = " -> ".join([str(loc_part) for loc_part in err.get("loc", []) if loc_part != "body"])
            msg = err.get("msg", "Invalid input")
            errors.append({"field": loc or "payload", "issue": msg, "type": err.get("type")})

        logger.info(f"Validation error on {request.method} {request.url.path}: {errors}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Input validation failed. Please check the requested fields.",
                    "detail": errors,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected server error occurred. Please contact the administrator.",
                    "detail": None,
                }
            },
        )
