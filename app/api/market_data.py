import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.repositories.asset_repository import AssetRepository
from app.repositories.market_data_repository import MarketDataRepository
from app.repositories.indicator_repository import IndicatorRepository
from app.schemas.asset import AssetResponse
from app.schemas.market_data import MarketDataResponse, MarketDataLatestResponse
from app.services.market_data_service import MarketDataService
from app.services.indicator_service import IndicatorService
from app.models import MarketData, Indicator

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/assets", response_model=List[AssetResponse], tags=["Market Data"])
def get_assets(db: Session = Depends(get_db)):
    """Retrieves list of all tracked assets."""
    asset_repo = AssetRepository(db)
    # Ensure database is seeded
    asset_repo.seed_default_assets()
    return asset_repo.list()

@router.get("/market-data", response_model=List[MarketDataResponse], tags=["Market Data"])
def get_market_data(
    symbol: Optional[str] = Query(None, description="Filter by asset symbol (e.g. ^NSEI, BTC-USD)"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: Session = Depends(get_db)
):
    """Retrieves historical raw market data rows."""
    market_repo = MarketDataRepository(db)
    if symbol:
        asset_repo = AssetRepository(db)
        asset = asset_repo.get_by_symbol(symbol)
        if not asset:
            raise HTTPException(status_code=404, detail=f"Asset symbol '{symbol}' not found")
        # Return history chronologically reversed (descending)
        records = db.query(market_repo.model).filter(market_repo.model.asset_id == asset.id).order_by(market_repo.model.recorded_at.desc()).limit(limit).all()
        return records
    return market_repo.list(limit=limit)

@router.get("/market-data/latest", tags=["Market Data"])
def get_latest_market_data(db: Session = Depends(get_db)):
    """
    Returns the latest daily summary for all assets,
    including Close, Daily Change %, SMA, RSI, Bollinger Bands, and Support/Resistance levels.
    """
    asset_repo = AssetRepository(db)
    market_repo = MarketDataRepository(db)
    indicator_repo = IndicatorRepository(db)
    
    assets = asset_repo.list()
    # Seeding fallback
    if not assets:
        assets = asset_repo.seed_default_assets()

    output = []
    for asset in assets:
        latest_data = market_repo.get_latest_for_asset(asset.id)
        latest_ind = indicator_repo.get_latest_for_asset(asset.id)
        
        output.append({
            "symbol": asset.symbol,
            "asset_type": asset.asset_type,
            "price_data": {
                "open": latest_data.open if latest_data else None,
                "high": latest_data.high if latest_data else None,
                "low": latest_data.low if latest_data else None,
                "close": latest_data.close if latest_data else None,
                "volume": latest_data.volume if latest_data else None,
                "change_percent": latest_data.change_percent if latest_data else None,
                "recorded_at": latest_data.recorded_at if latest_data else None,
            },
            "indicators": {
                "sma20": latest_ind.sma20 if latest_ind else None,
                "sma50": latest_ind.sma50 if latest_ind else None,
                "sma200": latest_ind.sma200 if latest_ind else None,
                "rsi": latest_ind.rsi if latest_ind else None,
                "macd": latest_ind.macd if latest_ind else None,
                "bollinger_upper": latest_ind.bollinger_upper if latest_ind else None,
                "bollinger_lower": latest_ind.bollinger_lower if latest_ind else None,
                "support": latest_ind.support if latest_ind else None,
                "resistance": latest_ind.resistance if latest_ind else None,
                "calculated_at": latest_ind.created_at if latest_ind else None,
            }
        })
    return output

@router.get("/market-data/charts", tags=["Market Data"])
def get_chart_data(
    symbol: str = Query(..., description="Asset symbol (e.g. ^NSEI, BTC-USD)"),
    days: int = Query(30, ge=5, le=250, description="Number of historical days to pull"),
    db: Session = Depends(get_db)
):
    """
    Returns chart-ready JSON history for a specific asset,
    containing synchronized lists of prices and indicators.
    """
    asset_repo = AssetRepository(db)
    asset = asset_repo.get_by_symbol(symbol)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset symbol '{symbol}' not found")

    # Get market history (oldest first)
    market_repo = MarketDataRepository(db)
    history = market_repo.get_history_for_asset(asset.id, limit=days)
    
    if not history:
        raise HTTPException(status_code=404, detail=f"No market data history available for '{symbol}'")

    dates = []
    prices = []
    change_pcts = []
    sma20 = []
    sma50 = []
    sma200 = []
    rsi = []
    macd = []
    b_upper = []
    b_lower = []
    support = []
    resistance = []

    # Correlate indicators by date
    # To do this efficiently, we can fetch matching indicator entries
    indicator_repo = IndicatorRepository(db)
    # Loop and look up indicators for each date or retrieve bulk
    # Since it is a small query, lookup in loop or do bulk join
    # A join query is cleaner. Let's do a join query sorted chronologically
    from sqlalchemy import func
    records = (
        db.query(MarketData, Indicator)
        .outerjoin(
            Indicator,
            (Indicator.asset_id == MarketData.asset_id) &
            (func.date(Indicator.created_at) == func.date(MarketData.recorded_at))
        )
        .filter(MarketData.asset_id == asset.id)
        .order_by(MarketData.recorded_at.desc())
        .limit(days)
        .all()
    )
    records.reverse() # Oldest first for charts

    for md, ind in records:
        dates.append(md.recorded_at.strftime("%Y-%m-%d"))
        prices.append(md.close)
        change_pcts.append(md.change_percent)
        
        if ind:
            sma20.append(ind.sma20)
            sma50.append(ind.sma50)
            sma200.append(ind.sma200)
            rsi.append(ind.rsi)
            macd.append(ind.macd)
            b_upper.append(ind.bollinger_upper)
            b_lower.append(ind.bollinger_lower)
            support.append(ind.support)
            resistance.append(ind.resistance)
        else:
            for list_obj in [sma20, sma50, sma200, rsi, macd, b_upper, b_lower, support, resistance]:
                list_obj.append(None)

    return {
        "symbol": symbol,
        "asset_type": asset.asset_type,
        "dates": dates,
        "prices": prices,
        "change_percent": change_pcts,
        "sma20": sma20,
        "sma50": sma50,
        "sma200": sma200,
        "rsi": rsi,
        "macd": macd,
        "bollinger_upper": b_upper,
        "bollinger_lower": b_lower,
        "support": support,
        "resistance": resistance
    }

@router.post("/fetch-market-data", tags=["Market Data"])
def trigger_fetch_market_data(
    background_tasks: BackgroundTasks,
    force_backfill: bool = Query(False, description="Force a full 1-year backfill for all symbols"),
    db: Session = Depends(get_db)
):
    """
    Manually triggers market data collection from Yahoo Finance and technical indicator computations.
    Can be run synchronously (blocking) or asynchronously in the background.
    """
    logger.info("Manual market data fetch triggered.")
    
    # We define a function to run the process
    def fetch_and_calc_process():
        # Create a new DB session for background task
        bg_db = SessionLocal()
        try:
            md_service = MarketDataService(bg_db)
            md_service.fetch_and_store_all(force_backfill=force_backfill)
            
            ind_service = IndicatorService(bg_db)
            ind_service.calculate_and_store_all()
            logger.info("Background market data fetch and calculation finished.")
        except Exception as e:
            logger.error(f"Error in background fetch task: {e}")
        finally:
            bg_db.close()

    # Add as background task to respond instantly
    background_tasks.add_task(fetch_and_calc_process)
    
    return {"message": "Market data fetch and indicator computation triggered in background tasks."}
