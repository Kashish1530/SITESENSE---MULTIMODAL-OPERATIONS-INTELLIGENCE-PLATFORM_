import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from app.core.logging import correlation_id_ctx, get_logger

logger = get_logger("app.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to assign correlation IDs and log all incoming HTTP requests and response times."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.perf_counter()
        
        # Extract or generate X-Request-ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = correlation_id_ctx.set(request_id)

        try:
            response = await call_next(request)
            process_time_ms = (time.perf_counter() - start_time) * 1000.0

            # Attach request id header to outgoing response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time-Ms"] = f"{process_time_ms:.2f}"

            client_ip = request.client.host if request.client else "unknown"
            logger.info(
                f"{request.method} {request.url.path} -> {response.status_code} "
                f"({process_time_ms:.2f}ms) [client={client_ip}]"
            )
            return response
        except Exception:
            process_time_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(
                f"{request.method} {request.url.path} -> FAILED ({process_time_ms:.2f}ms)"
            )
            raise
        finally:
            correlation_id_ctx.reset(token)
