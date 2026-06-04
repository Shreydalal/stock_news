from typing import Optional, List
from datetime import datetime
from sqlalchemy import desc
from sqlalchemy.orm import Session
from app.models.market_data import MarketData
from app.repositories.base import BaseRepository

class MarketDataRepository(BaseRepository[MarketData]):
    def __init__(self, db: Session):
        super().__init__(MarketData, db)

    def get_latest_for_asset(self, asset_id: int) -> Optional[MarketData]:
        """Gets the most recent market data point for a specific asset."""
        return (
            self.db.query(self.model)
            .filter(self.model.asset_id == asset_id)
            .order_by(desc(self.model.recorded_at))
            .first()
        )

    def get_history_for_asset(self, asset_id: int, limit: int = 250) -> List[MarketData]:
        """Gets the historical market data for a specific asset, sorted oldest to newest for calculations."""
        records = (
            self.db.query(self.model)
            .filter(self.model.asset_id == asset_id)
            .order_by(desc(self.model.recorded_at))
            .limit(limit)
            .all()
        )
        # Reverse the list so it is in chronological order (oldest first)
        records.reverse()
        return records

    def save_or_update(self, asset_id: int, date: datetime, open_val: float, high: float, low: float, close: float, volume: Optional[int], change_pct: float) -> MarketData:
        """Saves a daily record, or updates it if one already exists for that asset on that exact day."""
        # Check if record exists for this day (ignoring time if we store daily resolution)
        # Since it is recorded daily, we check matching date (same year, month, day)
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # In SQL, check recorded_at date
        existing = (
            self.db.query(self.model)
            .filter(self.model.asset_id == asset_id)
            .filter(self.model.recorded_at >= start_of_day)
            .order_by(desc(self.model.recorded_at))
            .first()
        )

        if existing:
            # Update existing
            existing.open = open_val
            existing.high = high
            existing.low = low
            existing.close = close
            existing.volume = volume
            existing.change_percent = change_pct
            existing.recorded_at = date
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new
            new_record = MarketData(
                asset_id=asset_id,
                open=open_val,
                high=high,
                low=low,
                close=close,
                volume=volume,
                change_percent=change_pct,
                recorded_at=date
            )
            return self.create(new_record)
