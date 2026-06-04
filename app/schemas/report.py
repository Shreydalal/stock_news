from datetime import date, datetime
from pydantic import BaseModel, ConfigDict

class ReportBase(BaseModel):
    report_date: date
    report_path: str

class ReportCreate(ReportBase):
    pass

class ReportResponse(ReportBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime

class ReportDetailResponse(ReportResponse):
    content: str
