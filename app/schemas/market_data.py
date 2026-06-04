from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class MarketDataBase(BaseModel):
    open: float
    high: float
    low: float
    close: float
    volume: Optional[int] = None
    change_percent: float
    recorded_at: datetime

class MarketDataCreate(MarketDataBase):
    asset_id: int

class MarketDataResponse(MarketDataBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int

class MarketDataLatestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    asset_type: str
    open: float
    high: float
    low: float
    close: float
    volume: Optional[int] = None
    change_percent: float
    recorded_at: datetime
