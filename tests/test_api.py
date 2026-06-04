import pytest
from datetime import date, datetime
from app.models.asset import Asset
from app.models.market_data import MarketData
from app.models.indicator import Indicator
from app.models.report import Report

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"]["status"] == "connected"

def test_get_assets_endpoint(client):
    response = client.get("/assets")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 7
    symbols = [item["symbol"] for item in data]
    assert "^NSEI" in symbols
    assert "BTC-USD" in symbols

def test_get_market_data_empty(client):
    response = client.get("/market-data")
    assert response.status_code == 200
    assert response.json() == []

def test_fetch_market_data_trigger(client):
    response = client.post("/fetch-market-data")
    assert response.status_code == 200
    assert "triggered in background" in response.json()["message"]

def test_generate_report_trigger(client):
    response = client.post("/generate-report?report_type=daily")
    assert response.status_code == 200
    assert "triggered in the background" in response.json()["message"]

def test_get_reports_flow(client, db_session):
    # Insert a dummy report index
    report = Report(
        report_date=date(2026, 8, 15),
        report_path="reports/2026/08/15/report.md"
    )
    db_session.add(report)
    db_session.commit()

    # List reports
    response = client.get("/reports")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["report_path"] == "reports/2026/08/15/report.md"

def test_get_latest_market_data(client, db_session):
    # Setup some test assets data and indicators
    asset = db_session.query(Asset).filter(Asset.symbol == "^NSEI").first()
    
    md = MarketData(
        asset_id=asset.id,
        open=20000.0,
        high=20100.0,
        low=19900.0,
        close=20050.0,
        volume=500000,
        change_percent=0.25,
        recorded_at=datetime.utcnow()
    )
    db_session.add(md)
    
    ind = Indicator(
        asset_id=asset.id,
        sma20=20000.0,
        sma50=19800.0,
        sma200=19000.0,
        rsi=60.0,
        macd=50.0,
        bollinger_upper=20200.0,
        bollinger_lower=19800.0,
        support=19500.0,
        resistance=20500.0,
        created_at=datetime.utcnow()
    )
    db_session.add(ind)
    db_session.commit()

    response = client.get("/market-data/latest")
    assert response.status_code == 200
    data = response.json()
    nifty = [item for item in data if item["symbol"] == "^NSEI"][0]
    assert nifty["price_data"]["close"] == 20050.0
    assert nifty["indicators"]["rsi"] == 60.0

def test_get_chart_data(client, db_session):
    asset = db_session.query(Asset).filter(Asset.symbol == "^NSEI").first()
    
    md = MarketData(
        asset_id=asset.id,
        open=20000.0,
        high=20100.0,
        low=19900.0,
        close=20050.0,
        volume=500000,
        change_percent=0.25,
        recorded_at=datetime.utcnow()
    )
    db_session.add(md)
    db_session.commit()

    response = client.get("/market-data/charts?symbol=^NSEI&days=10")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "^NSEI"
    assert len(data["prices"]) == 1
    assert data["prices"][0] == 20050.0

def test_get_report_detail_and_latest(client, db_session):
    # Create the report folder and file
    from pathlib import Path
    report_dir = Path("./reports/2026/08/15")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / "report.md"
    report_file.write_text("# Test Daily Report Content", encoding="utf-8")

    report = Report(
        report_date=date(2026, 8, 15),
        report_path="reports/2026/08/15/report.md"
    )
    db_session.add(report)
    db_session.commit()

    # Test latest report
    response = client.get("/reports/latest")
    assert response.status_code == 200
    data = response.json()
    assert data["report_date"] == "2026-08-15"
    assert "Test Daily Report Content" in data["content"]

    # Test report by date
    response = client.get("/reports/2026-08-15")
    assert response.status_code == 200
    data = response.json()
    assert "Test Daily Report Content" in data["content"]

    # Clean up file
    try:
        report_file.unlink()
        report_dir.rmdir()
        report_dir.parent.rmdir()
        report_dir.parent.parent.rmdir()
    except Exception:
        pass

