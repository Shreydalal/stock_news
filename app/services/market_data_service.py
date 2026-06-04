import logging
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.market_data import MarketData
from app.repositories.asset_repository import AssetRepository
from app.repositories.market_data_repository import MarketDataRepository

logger = logging.getLogger(__name__)

class MarketDataService:
    def __init__(self, db: Session):
        self.db = db
        self.asset_repo = AssetRepository(db)
        self.market_data_repo = MarketDataRepository(db)

    def fetch_and_store_all(self, force_backfill: bool = False) -> Dict[str, Any]:
        """
        Fetches and stores market data for all registered assets.
        If an asset has no history, it performs a 1-year backfill.
        Otherwise, it fetches the last 5 days of data to handle weekend/holiday gaps.
        """
        # Ensure default assets are seeded
        assets = self.asset_repo.seed_default_assets()
        results = {}

        for asset in assets:
            try:
                # Check current database history length
                history_count = self.db.query(MarketData).filter(MarketData.asset_id == asset.id).count()
                
                # Determine period to fetch
                if history_count < 250 or force_backfill:
                    period = "1y"
                    logger.info(f"Backfilling 1 year of data for {asset.symbol} (current count: {history_count})")
                else:
                    period = "5d"
                    logger.info(f"Fetching recent data for {asset.symbol} (current count: {history_count})")

                # Fetch from yfinance
                ticker = yf.Ticker(asset.symbol)
                df = ticker.history(period=period)

                if df.empty:
                    logger.warning(f"No data returned from yfinance for {asset.symbol}")
                    results[asset.symbol] = "No data returned"
                    continue

                # Clean and parse dataframe index (tz-naive)
                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)

                # Calculate percent change from previous close
                # df['Close'].pct_change() returns fractional values, e.g., 0.012 for 1.2%
                df['Change_Pct'] = df['Close'].pct_change() * 100
                # Fallback for the first row to open-to-close change if no previous close exists
                df.loc[df.index[0], 'Change_Pct'] = ((df['Close'].iloc[0] - df['Open'].iloc[0]) / df['Open'].iloc[0]) * 100

                inserted_count = 0
                for timestamp, row in df.iterrows():
                    # Handle NaN values
                    open_val = float(row['Open']) if not pd.isna(row['Open']) else 0.0
                    high_val = float(row['High']) if not pd.isna(row['High']) else 0.0
                    low_val = float(row['Low']) if not pd.isna(row['Low']) else 0.0
                    close_val = float(row['Close']) if not pd.isna(row['Close']) else 0.0
                    volume_val = int(row['Volume']) if not pd.isna(row['Volume']) else 0
                    change_pct = float(row['Change_Pct']) if not pd.isna(row['Change_Pct']) else 0.0

                    self.market_data_repo.save_or_update(
                        asset_id=asset.id,
                        date=timestamp.to_pydatetime(),
                        open_val=open_val,
                        high=high_val,
                        low=low_val,
                        close=close_val,
                        volume=volume_val,
                        change_pct=change_pct
                    )
                    inserted_count += 1

                logger.info(f"Stored {inserted_count} data points for {asset.symbol}")
                results[asset.symbol] = f"Stored {inserted_count} points"

            except Exception as e:
                logger.error(f"Error fetching data for asset {asset.symbol}: {e}", exc_info=True)
                results[asset.symbol] = f"Error: {str(e)}"

        return results
