import pytest
from datetime import date, datetime
from app.services.ai_report_service import AIReportService
from app.models.asset import Asset
from app.models.market_data import MarketData
from app.models.indicator import Indicator

def test_generate_report_fallback(db_session):
    # Setup: We need to insert a market data point and indicator for each seeded asset
    assets = db_session.query(Asset).all()
    assert len(assets) > 0

    for asset in assets:
        # Add market data
        md = MarketData(
            asset_id=asset.id,
            open=100.0,
            high=105.0,
            low=95.0,
            close=101.0,
            volume=1000,
            change_percent=1.0,
            recorded_at=datetime.utcnow()
        )
        db_session.add(md)
        db_session.commit()
        db_session.refresh(md)

        # Add indicators
        ind = Indicator(
            asset_id=asset.id,
            sma20=100.0,
            sma50=100.0,
            sma200=100.0,
            rsi=50.0,
            macd=0.0,
            bollinger_upper=102.0,
            bollinger_lower=98.0,
            support=95.0,
            resistance=105.0,
            created_at=datetime.utcnow()
        )
        db_session.add(ind)
        db_session.commit()

    service = AIReportService(db_session)
    report_date = date(2026, 8, 15)
    report_content = service.generate_daily_report(report_date)

    # Assertions: Verify report is generated in markdown format
    assert "# Daily Market Intelligence Report - 2026-08-15" in report_content
    assert "## 1. Executive Summary" in report_content
    assert "## 2. NIFTY Analysis" in report_content
    assert "## 3. BANKNIFTY Analysis" in report_content
    assert "## 4. Gold Analysis" in report_content
    assert "## 5. Silver Analysis" in report_content
    assert "## 6. Bitcoin Analysis" in report_content
    assert "## 7. Ethereum Analysis" in report_content
    assert "## 8. Risk Factors" in report_content
    assert "## 9. Trading Opportunities" in report_content
    assert "## 10. Tomorrow Outlook" in report_content
    
    # Verify values are populated inside sections
    assert "101.00" in report_content # Check closing price is in there
    assert "1.00%" in report_content  # Check change percent is inside
