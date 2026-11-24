import time
from typing import Any, Dict, Generator
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from app.config.settings import get_settings
from app.core.logging import get_logger

logger = get_logger("app.db")
settings = get_settings()

# Engine creation supporting PostgreSQL and SQLite
engine_kwargs: Dict[str, Any] = {}
if settings.is_sqlite:
    engine_kwargs["connect_args"] = settings.database_connect_args
else:
    engine_kwargs.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_pre_ping": settings.DB_POOL_PRE_PING,
    })

engine: Engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency provider yielding a database session per request."""
    db: Session = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session rollback due to exception: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def check_database_connection() -> Dict[str, Any]:
    """Execute a test query against the database to confirm connectivity and measure latency."""
    start_time = time.perf_counter()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            "status": "healthy",
            "connected": True,
            "dialect": engine.dialect.name,
            "latency_ms": round(latency_ms, 2),
        }
    except Exception as exc:
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        logger.error(f"Database health check failed: {exc}")
        return {
            "status": "unhealthy",
            "connected": False,
            "dialect": engine.dialect.name,
            "error": str(exc),
            "latency_ms": round(latency_ms, 2),
        }
