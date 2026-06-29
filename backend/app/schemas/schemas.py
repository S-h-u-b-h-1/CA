from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# ==========================================
# AUTHENTICATION & USER SCHEMAS
# ==========================================

class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str

class UserCreate(UserBase):
    password: str
    role: str = "EMPLOYEE"  # SUPER_ADMIN, FIRM_ADMIN, PARTNER, MANAGER, EMPLOYEE, ARTICLE_ASSISTANT, CLIENT_USER

class UserResponse(UserBase):
    id: str
    organization_id: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class TokenData(BaseModel):
    email: Optional[str] = None


# ==========================================
# ORGANIZATION SCHEMAS
# ==========================================

class OrganizationBase(BaseModel):
    organization_name: str
    firm_type: str
    GSTIN: Optional[str] = None
    PAN: Optional[str] = None
    address: Optional[str] = None
    contact_email: EmailStr
    phone: Optional[str] = None

class OrganizationCreate(OrganizationBase):
    admin_first_name: str
    admin_last_name: str
    admin_email: EmailStr
    admin_password: str

class OrganizationUpdate(BaseModel):
    organization_name: Optional[str] = None
    firm_type: Optional[str] = None
    GSTIN: Optional[str] = None
    PAN: Optional[str] = None
    address: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    phone: Optional[str] = None
    subscription_plan: Optional[str] = None

class OrganizationResponse(OrganizationBase):
    id: str
    subscription_plan: str
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# CLIENT SCHEMAS
# ==========================================

class ClientBase(BaseModel):
    client_name: str
    client_type: str  # Individual / Proprietorship / Partnership / LLP / Company / Trust / HUF / Other
    PAN: Optional[str] = None
    GSTIN: Optional[str] = None
    CIN_LLPIN: Optional[str] = None
    TAN: Optional[str] = None
    registered_address: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    industry: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class ClientUpdate(BaseModel):
    client_name: Optional[str] = None
    client_type: Optional[str] = None
    PAN: Optional[str] = None
    GSTIN: Optional[str] = None
    CIN_LLPIN: Optional[str] = None
    TAN: Optional[str] = None
    registered_address: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    industry: Optional[str] = None
    status: Optional[str] = None

class ClientResponse(ClientBase):
    id: str
    organization_id: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# DOCUMENT SCHEMAS
# ==========================================

class DocumentResponse(BaseModel):
    id: str
    organization_id: str
    client_id: Optional[str] = None
    name: str
    file_path: str
    file_size: int
    mime_type: str
    category: str
    processing_status: str
    extracted_text: Optional[str] = None
    embedding_status: str
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentUpdate(BaseModel):
    category: Optional[str] = None
    processing_status: Optional[str] = None
    client_id: Optional[str] = None


# ==========================================
# COMPLIANCE SOURCES SCHEMAS
# ==========================================

class ComplianceSourceBase(BaseModel):
    source_name: str
    category: str
    official_url: str
    access_type: str
    requires_auth: bool = False
    update_frequency: str
    notes: Optional[str] = None

class ComplianceSourceCreate(ComplianceSourceBase):
    pass

class ComplianceSourceUpdate(BaseModel):
    source_name: Optional[str] = None
    category: Optional[str] = None
    official_url: Optional[str] = None
    access_type: Optional[str] = None
    requires_auth: Optional[bool] = None
    update_frequency: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class ComplianceSourceResponse(ComplianceSourceBase):
    id: str
    status: str
    last_checked_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# NOTE SCHEMAS
# ==========================================

class NoteCreate(BaseModel):
    client_id: Optional[str] = None
    title: str
    content: str

class NoteResponse(BaseModel):
    id: str
    organization_id: str
    client_id: Optional[str] = None
    title: str
    content: str
    created_by: str
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# INTEGRATION SCHEMAS
# ==========================================

class AKKCConnect(BaseModel):
    api_key: str
    base_url: str = "https://akkc-eight.vercel.app/api"

class AKKCStatusResponse(BaseModel):
    connected: bool
    system_name: str = "AKKC"
    base_url: Optional[str] = None
    last_synced_at: Optional[datetime] = None

class SyncRequest(BaseModel):
    entity_type: str  # CLIENTS, TASKS, BILLS

class SyncResponse(BaseModel):
    status: str
    synced_count: int
    error: Optional[str] = None


# ==========================================
# UNIVERSAL SEARCH SCHEMAS
# ==========================================

class SearchClientResult(BaseModel):
    id: str
    client_name: str
    client_type: str
    PAN: Optional[str] = None
    GSTIN: Optional[str] = None
    status: str

class SearchDocumentResult(BaseModel):
    id: str
    name: str
    category: str
    processing_status: str
    client_id: Optional[str] = None

class SearchNoteResult(BaseModel):
    id: str
    title: str
    content: str
    client_id: Optional[str] = None
    created_at: datetime

class SearchInvoiceResult(BaseModel):
    id: str
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    total_amount: Optional[float] = None
    GSTIN: Optional[str] = None
    created_at: datetime

class SearchNoticeResult(BaseModel):
    id: str
    din: Optional[str] = None
    section: Optional[str] = None
    assessment_year: Optional[str] = None
    tax_demand_amount: Optional[float] = None
    created_at: datetime

class SearchChunkResult(BaseModel):
    id: str
    text_content: str
    chunk_index: int

class SearchGraphNodeResult(BaseModel):
    id: str
    node_type: str
    label: str
    properties: Optional[Dict[str, Any]] = None

class SearchCitationResult(BaseModel):
    id: str
    source_type: str
    quote_text: Optional[str] = None
    section_reference: Optional[str] = None
    act_reference: Optional[str] = None
    text_reference: str
    confidence_score: float

class SearchGraphEdgeResult(BaseModel):
    id: str
    source_node_id: str
    target_node_id: str
    relationship: str

class SearchResult(BaseModel):
    clients: List[SearchClientResult]
    documents: List[SearchDocumentResult]
    notes: List[SearchNoteResult]
    structured_invoices: List[SearchInvoiceResult]
    structured_notices: List[SearchNoticeResult]
    knowledge_chunks: List[SearchChunkResult]
    graph_nodes: List[SearchGraphNodeResult]
    citations: List[SearchCitationResult]
    graph_edges: List[SearchGraphEdgeResult]

