from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime


class SuggestionEvidenceSchema(BaseModel):
    id: str
    evidence_type: str
    reference_id: Optional[str] = None
    summary: str
    created_at: datetime

    class Config:
        from_attributes = True


class SuggestionSchema(BaseModel):
    id: str
    client_id: str
    rule_key: str
    category: str
    title: str
    severity: str
    confidence: str
    confidence_reason: Optional[str] = None
    explanation: str
    recommendation: Optional[str] = None
    related_document_ids: Optional[List[str]] = None
    related_government_update_id: Optional[str] = None
    status: str
    acknowledged_at: Optional[datetime] = None
    in_progress_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    dismissed_reason: Optional[str] = None
    generated_at: datetime
    created_at: datetime
    updated_at: datetime
    evidence: List[SuggestionEvidenceSchema] = []
    client_name: Optional[str] = None

    class Config:
        from_attributes = True


# Valid transitions enforced in the service layer:
# NEW -> ACKNOWLEDGED -> IN_PROGRESS -> RESOLVED
# {NEW, ACKNOWLEDGED, IN_PROGRESS} -> DISMISSED
# RESOLVED and DISMISSED are terminal.
class SuggestionStatusUpdate(BaseModel):
    status: str
    reason: Optional[str] = None


class IntelligenceDashboardResponse(BaseModel):
    total_open: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    by_category: Dict[str, int]
    suggestions: List[SuggestionSchema]


class IntelligenceRuleInfo(BaseModel):
    rule_key: str
    category: str
    title: str
    status: str  # ACTIVE | NOT_YET_SUPPORTED
    description: str
    data_sources_used: List[str]
    confidence_basis: str
    limitations: Optional[str] = None


class RegenerateResponse(BaseModel):
    client_id: str
    generated: int
    refreshed: int
    resolved: int
    rules_evaluated: int
