from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime

class ClientWorkspaceOverview(BaseModel):
    client_name: str
    PAN: Optional[str] = None
    GSTIN: Optional[str] = None
    status: str
    assessment_year: str
    financial_year: str
    assigned_manager: Optional[str] = None
    assigned_partner: Optional[str] = None
    created_at: datetime
    last_activity: datetime
    health_score: str  # Excellent, Good, Needs Attention, Critical
    health_score_value: float

class ClientTaskSchema(BaseModel):
    id: str
    task_name: str
    description: Optional[str] = None
    status: str  # PENDING, IN_PROGRESS, COMPLETED, DEFERRED
    linked_to: Optional[str] = None
    linked_id: Optional[str] = None
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ClientTaskCreate(BaseModel):
    task_name: str
    description: Optional[str] = None
    status: Optional[str] = "PENDING"
    linked_to: Optional[str] = None
    linked_id: Optional[str] = None
    due_date: Optional[datetime] = None

class ClientTimelineSchema(BaseModel):
    id: str
    event_type: str
    title: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ClientTimelineCreate(BaseModel):
    event_type: str
    title: str
    description: Optional[str] = None

class ClientNoteSchema(BaseModel):
    id: str
    title: str
    content: str
    created_by: str
    tags: Optional[str] = None
    is_pinned: bool = False
    attachments: Optional[List[str]] = None
    mentions: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ClientNoteCreate(BaseModel):
    title: str
    content: str
    tags: Optional[str] = None
    is_pinned: Optional[bool] = False
    attachments: Optional[List[str]] = None
    mentions: Optional[List[str]] = None

class ClientWorkspaceResponse(BaseModel):
    overview: ClientWorkspaceOverview
    documents: List[Dict[str, Any]]
    tax_intelligence: Dict[str, Any]
    itr_preparation: Dict[str, Any]
    research: Dict[str, Any]
    tasks: List[ClientTaskSchema]
    notes: List[ClientNoteSchema]
    timeline: List[ClientTimelineSchema]
