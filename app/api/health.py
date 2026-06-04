import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.scheduler.scheduler import scheduler

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/health", tags=["System"])
def health_check(db: Session = Depends(get_db)):
    """
    Returns the system health status.
    Verifies connection to the database and background scheduler state.
    """
    logger.info("Received health check request.")
    
    # Check Database
    db_ok = False
    db_message = ""
    try:
        # Execute basic query
        db.execute(text("SELECT 1"))
        db_ok = True
        db_message = "Connected successfully"
    except Exception as e:
        logger.error(f"Health check: Database connection error: {e}")
        db_message = str(e)

    # Check Scheduler
    scheduler_ok = scheduler.running

    status = "healthy" if db_ok and scheduler_ok else "degraded"
    
    response_data = {
        "status": status,
        "database": {
            "status": "connected" if db_ok else "disconnected",
            "details": db_message
        },
        "scheduler": {
            "status": "running" if scheduler_ok else "stopped"
        }
    }

    if status == "degraded":
        raise HTTPException(status_code=503, detail=response_data)
        
    return response_data
