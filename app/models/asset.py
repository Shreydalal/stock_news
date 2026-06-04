from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), unique=True, index=True, nullable=False)
    asset_type = Column(String(50), nullable=False)  # stock, commodity, crypto
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    market_data = relationship("MarketData", back_populates="asset", cascade="all, delete-orphan")
    indicators = relationship("Indicator", back_populates="asset", cascade="all, delete-orphan")
