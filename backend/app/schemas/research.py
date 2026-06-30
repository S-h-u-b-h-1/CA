from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ResearchSourceResponse(BaseModel):
    id: str
    title: str
    authority: str
    section: Optional[str] = None
    rule_number: Optional[str] = None
    circular_number: Optional[str] = None
    notification_number: Optional[str] = None
    publication_date: Optional[datetime] = None
    effective_date: Optional[datetime] = None
    url: Optional[str] = None
    category: Optional[str] = None
    keywords: Optional[str] = None
    version: str
    status: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class ResearchQueryRequest(BaseModel):
    query_text: str
    client_id: Optional[str] = None
    assessment_year: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None

class ResearchResultResponse(BaseModel):
    id: str
    summary: str
    applicable_law: Optional[str] = None
    relevant_sections: Optional[str] = None
    relevant_circulars: Optional[str] = None
    relevant_notifications: Optional[str] = None
    considerations: Optional[str] = None
    risks: Optional[str] = None
    confidence: float
    references: List[ResearchSourceResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True

class ResearchNoteRequest(BaseModel):
    client_id: Optional[str] = None
    assessment_year: Optional[str] = None
    document_id: Optional[str] = None
    title: str
    content: str
    section_reference: Optional[str] = None
    authority_reference: Optional[str] = None
    tags: Optional[str] = None
    is_pinned: Optional[bool] = False

class ResearchNoteResponse(BaseModel):
    id: str
    client_id: Optional[str] = None
    assessment_year: Optional[str] = None
    document_id: Optional[str] = None
    title: str
    content: str
    section_reference: Optional[str] = None
    authority_reference: Optional[str] = None
    tags: Optional[str] = None
    is_pinned: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ResearchBookmarkRequest(BaseModel):
    source_id: str
    notes: Optional[str] = None

class ResearchBookmarkResponse(BaseModel):
    id: str
    source_id: str
    source: ResearchSourceResponse
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ResearchHistoryResponse(BaseModel):
    id: str
    query_text: str
    created_at: datetime
    result: Optional[ResearchResultResponse] = None

    class Config:
        from_attributes = True
