from datetime import datetime
from pydantic import BaseModel, ConfigDict

class AssetBase(BaseModel):
    symbol: str
    asset_type: str

class AssetCreate(AssetBase):
    pass

class AssetResponse(AssetBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
