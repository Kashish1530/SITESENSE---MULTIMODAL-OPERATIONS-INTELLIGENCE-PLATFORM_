import contextvars
import logging
import sys
from typing import Optional

# Context variable to propagate request correlation ID through async calls
correlation_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)


class StructuredFormatter(logging.Formatter):
    """Custom logging formatter that attaches correlation IDs and timestamps."""

    def format(self, record: logging.LogRecord) -> str:
        corr_id = correlation_id_ctx.get()
        record.correlation_id = f"[{corr_id}] " if corr_id else ""
        return super().format(record)


def setup_logging(log_level: str = "INFO") -> None:
    """Configure root and application loggers."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    log_format = "%(asctime)s | %(levelname)-7s | %(name)s | %(correlation_id)s%(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    formatter = StructuredFormatter(log_format, date_format)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid duplicate handlers on reloads
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)
    else:
        root_logger.handlers = [console_handler]

    # Silence overly verbose external libraries
    logging.getLogger("uvicorn.access").handlers = [console_handler]
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a standard logger instance with given name."""
    return logging.getLogger(name)
