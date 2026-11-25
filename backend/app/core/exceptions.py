from typing import Any, Optional


class AppException(Exception):
    """Base application exception with standardized code and details."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = 500,
        detail: Optional[Any] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.detail = detail


class BadRequestError(AppException):
    def __init__(self, message: str = "Bad Request", detail: Optional[Any] = None):
        super().__init__(
            message=message, code="BAD_REQUEST", status_code=400, detail=detail
        )


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Unauthorized", detail: Optional[Any] = None):
        super().__init__(
            message=message, code="UNAUTHORIZED", status_code=401, detail=detail
        )


class ForbiddenError(AppException):
    def __init__(self, message: str = "Forbidden", detail: Optional[Any] = None):
        super().__init__(
            message=message, code="FORBIDDEN", status_code=403, detail=detail
        )


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource Not Found", detail: Optional[Any] = None):
        super().__init__(
            message=message, code="NOT_FOUND", status_code=404, detail=detail
        )


class ConflictError(AppException):
    def __init__(self, message: str = "Conflict detected", detail: Optional[Any] = None):
        super().__init__(
            message=message, code="CONFLICT", status_code=409, detail=detail
        )


class DatabaseConnectionError(AppException):
    def __init__(
        self, message: str = "Database connection error", detail: Optional[Any] = None
    ):
        super().__init__(
            message=message,
            code="DATABASE_CONNECTION_ERROR",
            status_code=503,
            detail=detail,
        )


class InternalServerError(AppException):
    def __init__(self, message: str = "Internal server error", detail: Optional[Any] = None):
        super().__init__(
            message=message, code="INTERNAL_SERVER_ERROR", status_code=500, detail=detail
        )

