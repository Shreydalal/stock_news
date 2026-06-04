from sqlalchemy import Column, Integer, String, Date, DateTime, func
from app.core.database import Base

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    report_date = Column(Date, unique=True, index=True, nullable=False)
    report_path = Column(String(500), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
