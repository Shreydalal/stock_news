import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from app.services.market_data_service import MarketDataService
from app.models.market_data import MarketData

@patch("yfinance.Ticker")
def test_fetch_and_store_all(mock_ticker, db_session):
    # Setup Mock DataFrame
    dates = pd.date_range(start="2026-05-01", periods=5, freq="D")
    mock_df = pd.DataFrame({
        "Open": [100.0, 101.0, 102.0, 103.0, 104.0],
        "High": [102.0, 103.0, 104.0, 105.0, 106.0],
        "Low": [99.0, 100.0, 101.0, 102.0, 103.0],
        "Close": [101.0, 102.0, 103.0, 104.0, 105.0],
        "Volume": [1000, 1100, 1200, 1300, 1400]
    }, index=dates)

    # Mock Ticker Instance
    mock_ticker_instance = MagicMock()
    mock_ticker_instance.history.return_value = mock_df
    mock_ticker.return_value = mock_ticker_instance

    # Initialize Service
    service = MarketDataService(db_session)
    results = service.fetch_and_store_all()

    # Check results dictionary
    assert "^NSEI" in results
    assert "Stored 5 points" in results["^NSEI"]

    # Check database rows
    stored_points = db_session.query(MarketData).all()
    # 7 assets * 5 points each = 35 records
    assert len(stored_points) == 35

    # Check first record contents
    first_record = stored_points[0]
    assert first_record.open == 100.0
    assert first_record.close == 101.0
    assert first_record.volume == 1000
