import pytest
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import date
import pandas as pd

from app.scheduler.scheduler import run_daily_pipeline, run_weekly_pipeline, run_monthly_pipeline
from app.models.market_data import MarketData
from app.models.indicator import Indicator
from app.models.report import Report

@patch("yfinance.Ticker")
@patch("app.services.git_service.subprocess.run")
@patch("httpx.post")
@patch("smtplib.SMTP")
def test_run_daily_pipeline(mock_smtp, mock_httpx, mock_git, mock_ticker, db_session):
    # Mock yfinance ticker data to yield 250 daily points (covering SMA 200)
    dates = pd.date_range(start="2026-01-01", periods=250, freq="D")
    mock_df = pd.DataFrame({
        "Open": [100.0] * 250,
        "High": [105.0] * 250,
        "Low": [95.0] * 250,
        "Close": [100.0] * 250,
        "Volume": [1000] * 250
    }, index=dates)
    
    mock_ticker_instance = MagicMock()
    mock_ticker_instance.history.return_value = mock_df
    mock_ticker.return_value = mock_ticker_instance

    # Mock subprocess runs for Git
    mock_git_instance = MagicMock()
    mock_git_instance.returncode = 0
    mock_git_instance.stdout = "Everything up to date"
    mock_git.return_value = mock_git_instance

    # Mock Telegram alert http client post
    mock_httpx_resp = MagicMock()
    mock_httpx_resp.status_code = 200
    mock_httpx.return_value = mock_httpx_resp

    # Mock SMTP mail client sessions
    mock_smtp_instance = MagicMock()
    mock_smtp.return_value = mock_smtp_instance

    # Run the daily, weekly, and monthly pipelines using transactional test db connection
    with patch("app.scheduler.scheduler.SessionLocal", return_value=db_session):
        success = run_daily_pipeline()
        weekly_success = run_weekly_pipeline()
        monthly_success = run_monthly_pipeline()
        
    assert success is True
    assert weekly_success is True
    assert monthly_success is True

    # Assert report was created and stored in Database
    reports = db_session.query(Report).all()
    assert len(reports) == 1
    assert reports[0].report_date == date.today()

    # Assert prices and indicator tables have rows populated
    assert db_session.query(MarketData).count() > 0
    assert db_session.query(Indicator).count() > 0

    # Clean up generated test report files from disk
    workspace_root = Path(__file__).resolve().parent.parent
    
    # Clean up daily report dir
    reports_dir = workspace_root / "reports" / str(date.today().year)
    if reports_dir.exists():
        try:
            shutil.rmtree(reports_dir)
        except Exception:
            pass
            
    # Clean up weekly report dir
    weekly_dir = workspace_root / "reports" / "weekly"
    if weekly_dir.exists():
        try:
            shutil.rmtree(weekly_dir)
        except Exception:
            pass
            
    # Clean up monthly report dir
    monthly_dir = workspace_root / "reports" / "monthly"
    if monthly_dir.exists():
        try:
            shutil.rmtree(monthly_dir)
        except Exception:
            pass
