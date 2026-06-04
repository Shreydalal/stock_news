import os
import sys
from pathlib import Path

# Add project root to path so we can import app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Force SQLite file-based for testing configuration (shared connections support)
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["LOG_LEVEL"] = "WARNING"  # Quieter tests

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.models import Asset, MarketData, Indicator, Report
from app.repositories.asset_repository import AssetRepository

# Setup test DB engine
engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh file-based SQLite database and connection session for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Pre-seed default assets in the test database
    asset_repo = AssetRepository(db)
    asset_repo.seed_default_assets()
    
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        # Clean up database file
        db_file = Path("./test.db")
        if db_file.exists():
            try:
                db_file.unlink()
            except Exception:
                pass


@pytest.fixture(scope="function")
def client(db_session):
    """Override database dependency and yield a FastAPI TestClient."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
