import logging
from datetime import date, datetime
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.repositories.report_repository import ReportRepository
from app.schemas.report import ReportResponse, ReportDetailResponse
from app.scheduler.scheduler import run_daily_pipeline, run_weekly_pipeline, run_monthly_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()

# Get workspace root path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent

def read_report_content(report_path: str) -> str:
    """Reads the raw markdown report text from its path on disk."""
    full_path = WORKSPACE_ROOT / report_path
    if not full_path.exists():
        logger.warning(f"Report file not found on disk: {full_path}")
        return "Warning: The report file was indexed in the database but could not be located on disk."
    
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading report file {full_path}: {e}")
        return f"Error: Could not read report contents. {e}"

@router.get("/reports", response_model=List[ReportResponse], tags=["Reports"])
def get_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Lists metadata for all generated daily reports."""
    report_repo = ReportRepository(db)
    return report_repo.list(skip=skip, limit=limit)

@router.get("/reports/latest", response_model=ReportDetailResponse, tags=["Reports"])
def get_latest_report(db: Session = Depends(get_db)):
    """Retrieves the latest generated report along with its Markdown text content."""
    report_repo = ReportRepository(db)
    latest = report_repo.get_latest()
    if not latest:
        raise HTTPException(status_code=404, detail="No reports found in the database. Run a fetch and generate pipeline first.")
    
    content = read_report_content(latest.report_path)
    
    return {
        "id": latest.id,
        "report_date": latest.report_date,
        "report_path": latest.report_path,
        "created_at": latest.created_at,
        "content": content
    }

@router.get("/reports/{date_str}", response_model=ReportDetailResponse, tags=["Reports"])
def get_report_by_date(date_str: str, db: Session = Depends(get_db)):
    """
    Retrieves a report for a specific calendar date (e.g. 2026-08-15)
    and returns its full Markdown content.
    """
    try:
        report_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD (e.g. 2026-08-15)")

    report_repo = ReportRepository(db)
    report = report_repo.get_by_date(report_date)
    if not report:
        raise HTTPException(status_code=404, detail=f"No report indexed for date: {date_str}")
        
    content = read_report_content(report.report_path)

    return {
        "id": report.id,
        "report_date": report.report_date,
        "report_path": report.report_path,
        "created_at": report.created_at,
        "content": content
    }

@router.post("/generate-report", tags=["Reports"])
def trigger_generate_report(
    background_tasks: BackgroundTasks,
    report_type: str = Query("daily", description="Type of report to trigger: 'daily', 'weekly', or 'monthly'"),
    db: Session = Depends(get_db)
):
    """
    Manually triggers AI report generation, disk saving, git commits, and communications alerts.
    The task runs asynchronously in the background.
    """
    logger.info(f"Manual generation of report type '{report_type}' triggered.")
    
    if report_type not in ["daily", "weekly", "monthly"]:
        raise HTTPException(status_code=400, detail="Invalid report_type. Choose from 'daily', 'weekly', or 'monthly'.")

    def run_pipeline():
        if report_type == "daily":
            run_daily_pipeline()
        elif report_type == "weekly":
            run_weekly_pipeline()
        elif report_type == "monthly":
            run_monthly_pipeline()

    # Dispatch to background task
    background_tasks.add_task(run_pipeline)

    return {"message": f"Report generation pipeline ({report_type}) triggered in the background."}
