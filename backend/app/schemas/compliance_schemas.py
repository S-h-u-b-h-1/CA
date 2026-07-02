from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime

class ComplianceProfileCreate(BaseModel):
    client_id: str
    compliance_type: str
    registration_number: Optional[str] = None
    # None = "not specified by the caller" - the API applies the compliance
    # type's real registry default (where one safely exists) rather than a
    # hardcoded guess. Explicitly passing a value always overrides it.
    frequency: Optional[str] = None
    due_day: Optional[int] = None
    assigned_manager: Optional[str] = None
    assigned_partner: Optional[str] = None
    risk_level: Optional[str] = "LOW"


class ComplianceProfileUpdate(BaseModel):
    compliance_type: Optional[str] = None
    registration_number: Optional[str] = None
    frequency: Optional[str] = None
    due_day: Optional[int] = None
    assigned_manager: Optional[str] = None
    assigned_partner: Optional[str] = None
    risk_level: Optional[str] = None

class ComplianceProfileSchema(BaseModel):
    id: str
    client_id: str
    compliance_type: str
    registration_number: Optional[str] = None
    frequency: str
    due_day: int
    assigned_manager: Optional[str] = None
    assigned_partner: Optional[str] = None
    risk_level: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ComplianceTaskCreate(BaseModel):
    client_id: str
    profile_id: str
    task_name: str
    due_date: datetime
    priority: Optional[str] = "MEDIUM"
    status: Optional[str] = "PENDING"
    assigned_user_id: Optional[str] = None
    notes: Optional[str] = None

class ComplianceTaskSchema(BaseModel):
    id: str
    client_id: str
    profile_id: str
    task_name: str
    due_date: datetime
    priority: str
    status: str
    assigned_user_id: Optional[str] = None
    document_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ComplianceHistoryCreate(BaseModel):
    task_id: str
    acknowledgement_number: Optional[str] = None
    notes: Optional[str] = None

class ComplianceHistorySchema(BaseModel):
    id: str
    client_id: str
    task_id: str
    filing_date: datetime
    acknowledgement_number: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ComplianceAlertSchema(BaseModel):
    id: str
    client_id: str
    task_id: Optional[str] = None
    alert_type: str
    message: str
    is_resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ComplianceDashboardResponse(BaseModel):
    health_score: str
    health_score_value: float
    on_time_filing_percentage: float
    total_returns_completed: int
    total_returns_pending: int
    total_returns_overdue: int
    upcoming_deadlines: List[ComplianceTaskSchema]
    recent_alerts: List[ComplianceAlertSchema]
