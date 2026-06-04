from typing import Optional
from sqlalchemy import desc
from sqlalchemy.orm import Session
from app.models.indicator import Indicator
from app.repositories.base import BaseRepository

class IndicatorRepository(BaseRepository[Indicator]):
    def __init__(self, db: Session):
        super().__init__(Indicator, db)

    def get_latest_for_asset(self, asset_id: int) -> Optional[Indicator]:
        """Gets the most recently calculated indicator set for a specific asset."""
        return (
            self.db.query(self.model)
            .filter(self.model.asset_id == asset_id)
            .order_by(desc(self.model.created_at))
            .first()
        )
