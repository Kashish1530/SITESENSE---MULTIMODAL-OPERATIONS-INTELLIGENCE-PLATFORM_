import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
backend_path = Path(__file__).resolve().parents[1]
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Force SQLite for test execution
os.environ["DATABASE_URL"] = "sqlite:///./test_sitesense.db"
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "False"

from app.main import app
from app.db.base import Base
from app.db.session import engine


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    try:
        engine.dispose()
    except Exception:
        pass
    test_db_file = Path("./test_sitesense.db")
    if test_db_file.exists():
        try:
            test_db_file.unlink()
        except Exception:
            pass


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client
