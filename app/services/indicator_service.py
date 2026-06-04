import logging
import pandas as pd
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.asset import Asset
from app.models.market_data import MarketData
from app.models.indicator import Indicator
from app.repositories.asset_repository import AssetRepository
from app.repositories.market_data_repository import MarketDataRepository
from app.repositories.indicator_repository import IndicatorRepository

logger = logging.getLogger(__name__)

class IndicatorService:
    def __init__(self, db: Session):
        self.db = db
        self.asset_repo = AssetRepository(db)
        self.market_data_repo = MarketDataRepository(db)
        self.indicator_repo = IndicatorRepository(db)

    def calculate_and_store_all(self) -> Dict[str, Any]:
        """Calculates indicators for all assets and stores the latest day's calculations in the DB."""
        assets = self.asset_repo.list()
        results = {}

        for asset in assets:
            try:
                # Fetch history (we need up to 250 points for SMA 200)
                history = self.market_data_repo.get_history_for_asset(asset.id, limit=250)
                if len(history) < 20:  # Need at least 20 points for SMA 20 and Bollinger Bands
                    logger.warning(f"Not enough market data to calculate indicators for {asset.symbol} (count: {len(history)})")
                    results[asset.symbol] = f"Insufficient data: {len(history)} points"
                    continue

                # Load into DataFrame
                data = [
                    {
                        "recorded_at": r.recorded_at,
                        "open": r.open,
                        "high": r.high,
                        "low": r.low,
                        "close": r.close,
                        "volume": r.volume
                    }
                    for r in history
                ]
                df = pd.DataFrame(data)
                df.set_index("recorded_at", inplace=True)

                # Compute Indicators
                df = self.compute_indicators(df)

                # Get the latest row
                latest_row = df.iloc[-1]
                latest_time = df.index[-1]

                # Check if indicator already exists for this asset and day
                # Since it is daily, check for same date
                start_of_day = latest_time.replace(hour=0, minute=0, second=0, microsecond=0)
                existing = (
                    self.db.query(Indicator)
                    .filter(Indicator.asset_id == asset.id)
                    .filter(Indicator.created_at >= start_of_day)
                    .order_by(desc(Indicator.created_at))
                    .first()
                )

                # Convert values to float or None if NaN
                def clean_val(val) -> Optional[float]:
                    return None if pd.isna(val) else float(val)

                if existing:
                    # Update existing record
                    existing.sma20 = clean_val(latest_row.get("sma20"))
                    existing.sma50 = clean_val(latest_row.get("sma50"))
                    existing.sma200 = clean_val(latest_row.get("sma200"))
                    existing.rsi = clean_val(latest_row.get("rsi"))
                    existing.macd = clean_val(latest_row.get("macd"))
                    existing.bollinger_upper = clean_val(latest_row.get("bollinger_upper"))
                    existing.bollinger_lower = clean_val(latest_row.get("bollinger_lower"))
                    existing.support = clean_val(latest_row.get("support"))
                    existing.resistance = clean_val(latest_row.get("resistance"))
                    existing.created_at = latest_time
                    self.db.commit()
                    self.db.refresh(existing)
                    logger.info(f"Updated indicator data for {asset.symbol} at {latest_time}")
                else:
                    # Create new record
                    new_ind = Indicator(
                        asset_id=asset.id,
                        sma20=clean_val(latest_row.get("sma20")),
                        sma50=clean_val(latest_row.get("sma50")),
                        sma200=clean_val(latest_row.get("sma200")),
                        rsi=clean_val(latest_row.get("rsi")),
                        macd=clean_val(latest_row.get("macd")),
                        bollinger_upper=clean_val(latest_row.get("bollinger_upper")),
                        bollinger_lower=clean_val(latest_row.get("bollinger_lower")),
                        support=clean_val(latest_row.get("support")),
                        resistance=clean_val(latest_row.get("resistance")),
                        created_at=latest_time
                    )
                    self.db.add(new_ind)
                    self.db.commit()
                    logger.info(f"Created indicator data for {asset.symbol} at {latest_time}")

                results[asset.symbol] = "Success"

            except Exception as e:
                logger.error(f"Error calculating indicators for {asset.symbol}: {e}", exc_info=True)
                results[asset.symbol] = f"Error: {str(e)}"

        return results

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Applies financial indicator calculations on a historical close/high/low DataFrame."""
        # Simple Moving Averages
        df["sma20"] = df["close"].rolling(window=20).mean()
        df["sma50"] = df["close"].rolling(window=50).mean()
        df["sma200"] = df["close"].rolling(window=200).mean()

        # Momentum: RSI 14 (Wilder's Smoothing)
        change = df["close"].diff()
        gain = change.mask(change < 0, 0.0)
        loss = -change.mask(change > 0, -0.0)
        
        # We use adjust=False to match classic Wilder formulas exactly
        avg_gain = gain.ewm(com=13, adjust=False).mean()
        avg_loss = loss.ewm(com=13, adjust=False).mean()
        
        rs = avg_gain / avg_loss.replace(0, 1e-10) # Avoid divide by zero
        df["rsi"] = 100 - (100 / (1 + rs))

        # Trend: MACD Line (EMA 12 - EMA 26)
        ema12 = df["close"].ewm(span=12, adjust=False).mean()
        ema26 = df["close"].ewm(span=26, adjust=False).mean()
        df["macd"] = ema12 - ema26

        # Volatility: Bollinger Bands (20-day SMA + 2 Std Dev)
        std20 = df["close"].rolling(window=20).std()
        df["bollinger_upper"] = df["sma20"] + (2 * std20)
        df["bollinger_lower"] = df["sma20"] - (2 * std20)

        # Support & Resistance (Last 30-day Low & High)
        df["support"] = df["low"].rolling(window=30).min()
        df["resistance"] = df["high"].rolling(window=30).max()

        return df
