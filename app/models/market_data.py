from sqlalchemy import Column, Integer, Float, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class MarketData(Base):
    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=True)  # Volume can be large or null (some commodities)
    change_percent = Column(Float, nullable=False)  # Daily change percent
    recorded_at = Column(DateTime, index=True, nullable=False)

    # Relationships
    asset = relationship("Asset", back_populates="market_data")
