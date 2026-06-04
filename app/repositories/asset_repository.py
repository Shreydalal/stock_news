import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.asset import Asset
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

DEFAULT_ASSETS = [
    {"symbol": "^NSEI", "asset_type": "stock"},       # NIFTY 50
    {"symbol": "^NSEBANK", "asset_type": "stock"},    # BANKNIFTY
    {"symbol": "^BSESN", "asset_type": "stock"},      # SENSEX
    {"symbol": "GC=F", "asset_type": "commodity"},    # Gold
    {"symbol": "SI=F", "asset_type": "commodity"},    # Silver
    {"symbol": "BTC-USD", "asset_type": "crypto"},    # Bitcoin
    {"symbol": "ETH-USD", "asset_type": "crypto"}     # Ethereum
]

class AssetRepository(BaseRepository[Asset]):
    def __init__(self, db: Session):
        super().__init__(Asset, db)

    def get_by_symbol(self, symbol: str) -> Optional[Asset]:
        return self.db.query(self.model).filter(self.model.symbol == symbol).first()

    def seed_default_assets(self) -> List[Asset]:
        """Seeds the default tracked assets if the assets table is empty."""
        existing_count = self.db.query(Asset).count()
        if existing_count > 0:
            logger.info("Assets table already seeded.")
            return self.db.query(Asset).all()

        logger.info("Seeding default assets...")
        seeded_assets = []
        for asset_data in DEFAULT_ASSETS:
            asset = Asset(
                symbol=asset_data["symbol"],
                asset_type=asset_data["asset_type"]
            )
            self.db.add(asset)
            seeded_assets.append(asset)
        
        try:
            self.db.commit()
            for asset in seeded_assets:
                self.db.refresh(asset)
            logger.info(f"Successfully seeded {len(seeded_assets)} default assets.")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error seeding default assets: {e}")
            raise e

        return seeded_assets
