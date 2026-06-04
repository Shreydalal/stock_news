from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class IndicatorBase(BaseModel):
    sma20: Optional[float] = None
    sma50: Optional[float] = None
    sma200: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None
    support: Optional[float] = None
    resistance: Optional[float] = None
    created_at: datetime

class IndicatorCreate(IndicatorBase):
    asset_id: int

class IndicatorResponse(IndicatorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
