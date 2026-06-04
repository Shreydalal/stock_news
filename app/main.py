import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.utils.logger import setup_logging
from app.repositories.asset_repository import AssetRepository
from app.scheduler.scheduler import start_scheduler, shutdown_scheduler
from app.api import health, market_data, reports

# Setup logging before anything else
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup Actions ---
    logger.info("Initializing application startup...")
    
    # 1. Create database tables if they do not exist
    try:
        logger.info("Verifying database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified.")
    except Exception as e:
        logger.critical(f"Failed to initialize database tables: {e}", exc_info=True)
        raise e

    # 2. Seed default assets
    db = SessionLocal()
    try:
        asset_repo = AssetRepository(db)
        asset_repo.seed_default_assets()
    except Exception as e:
        logger.error(f"Failed to seed initial assets on startup: {e}")
    finally:
        db.close()

    # 3. Start APScheduler background jobs
    try:
        start_scheduler()
    except Exception as e:
        logger.error(f"Failed to start scheduler on startup: {e}")

    yield

    # --- Shutdown Actions ---
    logger.info("Initializing application shutdown...")
    try:
        shutdown_scheduler()
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {e}")
    logger.info("Application shutdown complete.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Automated financial market data collector, technical indicator analyzer, and AI report writer.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes exactly matching specs (no prefix needed as requested)
app.include_router(health.router)
app.include_router(market_data.router)
app.include_router(reports.router)

@app.get("/", include_in_schema=False)
def index_redirect():
    """Redirect root to OpenAPI interactive documentation."""
    return RedirectResponse(url="/docs")
