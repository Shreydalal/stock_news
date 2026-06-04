from datetime import date
from typing import Optional
from sqlalchemy import desc
from sqlalchemy.orm import Session
from app.models.report import Report
from app.repositories.base import BaseRepository

class ReportRepository(BaseRepository[Report]):
    def __init__(self, db: Session):
        super().__init__(Report, db)

    def get_by_date(self, report_date: date) -> Optional[Report]:
        """Gets a report for a specific date."""
        return (
            self.db.query(self.model)
            .filter(self.model.report_date == report_date)
            .first()
        )

    def get_latest(self) -> Optional[Report]:
        """Gets the most recently generated report."""
        return (
            self.db.query(self.model)
            .order_by(desc(self.model.report_date))
            .first()
        )

    def save_or_update(self, report_date: date, report_path: str) -> Report:
        """Saves a report or updates its path if it already exists."""
        existing = self.get_by_date(report_date)
        if existing:
            existing.report_path = report_path
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            new_report = Report(
                report_date=report_date,
                report_path=report_path
            )
            return self.create(new_report)
