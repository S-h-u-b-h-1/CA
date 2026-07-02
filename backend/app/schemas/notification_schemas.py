from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class NotificationSchema(BaseModel):
    id: str
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    source: str
    title: str
    body: Optional[str] = None
    related_suggestion_id: Optional[str] = None
    related_government_update_id: Optional[str] = None
    related_compliance_task_id: Optional[str] = None
    status: str
    read_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationStatusUpdate(BaseModel):
    status: str  # READ | ARCHIVED
