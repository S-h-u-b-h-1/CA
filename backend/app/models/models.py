import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Text, JSON, Float
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_name = Column(String(255), nullable=False)
    firm_type = Column(String(100), nullable=False)
    GSTIN = Column(String(15), nullable=True)
    PAN = Column(String(10), nullable=True)
    address = Column(Text, nullable=True)
    contact_email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    subscription_plan = Column(String(50), default="Free")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    users = relationship("User", back_populates="organization")
    clients = relationship("Client", back_populates="organization")
    documents = relationship("Document", back_populates="organization")
    notes = relationship("Note", back_populates="organization")
    external_systems = relationship("ExternalSystem", back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False)  # SUPER_ADMIN, FIRM_ADMIN, PARTNER, MANAGER, EMPLOYEE, ARTICLE_ASSISTANT, CLIENT_USER
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="users")
    notes = relationship("Note", back_populates="author")


class Client(Base):
    __tablename__ = "clients"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    client_name = Column(String(255), nullable=False)
    client_type = Column(String(50), nullable=False)  # Individual / Proprietorship / Partnership / LLP / Company / Trust / HUF / Other
    PAN = Column(String(10), nullable=True, index=True)
    GSTIN = Column(String(15), nullable=True, index=True)
    CIN_LLPIN = Column(String(21), nullable=True)
    TAN = Column(String(10), nullable=True, index=True)
    registered_address = Column(Text, nullable=True)
    contact_person = Column(String(100), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    industry = Column(String(100), nullable=True)
    status = Column(String(50), default="ACTIVE")  # ACTIVE / INACTIVE / ARCHIVED
    assigned_manager = Column(String(255), nullable=True)
    assigned_partner = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="clients")
    documents = relationship("Document", back_populates="client")
    notes = relationship("Note", back_populates="client")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id"), nullable=True)
    name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    category = Column(String(100), nullable=False)  # Income Tax Return, Form 16, etc.
    processing_status = Column(String(50), default="PENDING")  # PENDING, PROCESSING, COMPLETED, FAILED
    extracted_text = Column(Text, nullable=True)
    embedding_status = Column(String(50), default="PENDING")  # PENDING, COMPLETED, FAILED
    classification = Column(String(100), nullable=True)
    ocr_provider = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="documents")
    client = relationship("Client", back_populates="documents")
    chunks = relationship("DocumentTextChunk", back_populates="document", cascade="all, delete-orphan")
    jobs = relationship("DocumentProcessingJob", back_populates="document", cascade="all, delete-orphan")


class DocumentProcessingJob(Base):
    __tablename__ = "document_processing_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    job_type = Column(String(50), nullable=False)  # OCR, EMBEDDING, INDEX
    status = Column(String(50), default="PENDING")  # PENDING, PROCESSING, SUCCESS, FAILED
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    document = relationship("Document", back_populates="jobs")


class DocumentTextChunk(Base):
    __tablename__ = "document_text_chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text_content = Column(Text, nullable=False)
    embedding_vector = Column(JSON, nullable=True)  # Store vector float list
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")


class ComplianceSource(Base):
    __tablename__ = "compliance_sources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)  # Income Tax, GST, MCA / ROC, etc.
    official_url = Column(String(512), nullable=False)
    access_type = Column(String(50), nullable=False)  # API / RSS / Scraping / Manual Upload / Paid API / GSP / ERI
    requires_auth = Column(Boolean, default=False)
    update_frequency = Column(String(100), nullable=False)
    last_checked_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="ACTIVE")  # ACTIVE / INACTIVE
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)


class Note(Base):
    __tablename__ = "notes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id"), nullable=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    tags = Column(String(255), nullable=True)
    is_pinned = Column(Boolean, default=False)
    attachments_json = Column(JSON, nullable=True)
    mentions_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    organization = relationship("Organization", back_populates="notes")
    client = relationship("Client", back_populates="notes")
    author = relationship("User", back_populates="notes")


class ExternalSystem(Base):
    __tablename__ = "external_systems"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    name = Column(String(100), nullable=False)  # e.g., AKKC
    base_url = Column(String(255), nullable=False)
    status = Column(String(50), default="ACTIVE")  # ACTIVE / INACTIVE
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    organization = relationship("Organization", back_populates="external_systems")
    tokens = relationship("IntegrationToken", back_populates="external_system", cascade="all, delete-orphan")
    sync_logs = relationship("SyncLog", back_populates="external_system", cascade="all, delete-orphan")


class IntegrationToken(Base):
    __tablename__ = "integration_tokens"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    external_system_id = Column(String(36), ForeignKey("external_systems.id"), nullable=False)
    token_type = Column(String(50), nullable=False)  # API_KEY, OAUTH_BEARER
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    external_system = relationship("ExternalSystem", back_populates="tokens")


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    external_system_id = Column(String(36), ForeignKey("external_systems.id"), nullable=False)
    entity_type = Column(String(100), nullable=False)  # CLIENTS, EMPLOYEES, TASKS, BILLS
    sync_status = Column(String(50), nullable=False)  # SUCCESS, FAILED
    records_synced = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    external_system = relationship("ExternalSystem", back_populates="sync_logs")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)  # USER_LOGIN, DOCUMENT_UPLOAD, etc.
    entity_type = Column(String(100), nullable=True)
    entity_id = Column(String(36), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ==============================================================================
# PHASE 2 MODELS: ENTERPRISE DATA PLATFORM & KNOWLEDGE ENGINE
# ==============================================================================

class RawDocument(Base):
    __tablename__ = "raw_documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    client_id = Column(String(36), ForeignKey("clients.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    sha256_hash = Column(String(64), nullable=False, index=True)
    md5_hash = Column(String(32), nullable=False)
    similarity_hash = Column(String(64), nullable=True)
    file_fingerprint = Column(String(255), nullable=True)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    classification = Column(String(100), nullable=True)
    ocr_provider = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)


class ProcessedDocument(Base):
    __tablename__ = "processed_documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    raw_document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False, index=True)
    ocr_text = Column(Text, nullable=True)
    cleaned_tables_json = Column(JSON, nullable=True)
    normalized_text = Column(Text, nullable=True)
    language = Column(String(10), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StructuredDocument(Base):
    __tablename__ = "structured_documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    raw_document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False, index=True)
    parser_name = Column(String(100), nullable=False)
    extraction_date = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StructuredInvoiceData(Base):
    __tablename__ = "structured_invoice_data"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    raw_document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False, index=True)
    GSTIN = Column(String(15), nullable=True, index=True)
    vendor_name = Column(String(255), nullable=True)
    invoice_number = Column(String(100), nullable=True)
    invoice_date = Column(DateTime, nullable=True)
    hsn_code = Column(String(20), nullable=True)
    taxable_value = Column(Float, nullable=True)
    cgst = Column(Float, nullable=True)
    sgst = Column(Float, nullable=True)
    igst = Column(Float, nullable=True)
    cess = Column(Float, nullable=True)
    total_amount = Column(Float, nullable=True)
    currency = Column(String(10), default="INR", nullable=False)
    place_of_supply = Column(String(100), nullable=True)
    payment_status = Column(String(50), default="PENDING", nullable=False)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StructuredNoticeData(Base):
    __tablename__ = "structured_notice_data"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    raw_document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False, index=True)
    assessment_year = Column(String(10), nullable=True)
    section = Column(String(100), nullable=True)
    din = Column(String(100), nullable=True)
    issuing_authority = Column(String(255), nullable=True)
    tax_demand_amount = Column(Float, nullable=True)
    due_date = Column(DateTime, nullable=True)
    issues_identified = Column(JSON, nullable=True)
    response_deadline = Column(DateTime, nullable=True)
    reply_draft = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StructuredReturnData(Base):
    __tablename__ = "structured_return_data"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    raw_document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False)
    return_type = Column(String(50), nullable=False)  # GSTR-1, GSTR-3B, ITR-1, ITR-4, etc.
    filing_date = Column(DateTime, nullable=True)
    tax_period = Column(String(20), nullable=True)
    total_tax_payable = Column(Float, nullable=True)
    total_itc_claimed = Column(Float, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StructuredBankStatement(Base):
    __tablename__ = "structured_bank_statement"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    raw_document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False)
    bank_name = Column(String(255), nullable=True)
    account_number = Column(String(100), nullable=True)
    transaction_date = Column(DateTime, nullable=True)
    particulars = Column(Text, nullable=True)
    transaction_type = Column(String(10), nullable=True)  # DEBIT / CREDIT
    amount = Column(Float, nullable=True)
    balance = Column(Float, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    processed_document_id = Column(String(36), ForeignKey("processed_documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    text_content = Column(Text, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    knowledge_chunk_id = Column(String(36), ForeignKey("knowledge_chunks.id"), nullable=False, index=True)
    embedding_vector = Column(JSON, nullable=False)  # Stores float vector list
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Entity(Base):
    __tablename__ = "entities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False, index=True)  # PAN, GSTIN, TAN, DIN, CIN, LLPIN, Name, Address, Company, Person, Court, Act, Section, Rule
    value = Column(String(512), nullable=False, index=True)
    metadata_json = Column(JSON, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EntityRelationship(Base):
    __tablename__ = "entity_relationships"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    source_entity_id = Column(String(36), ForeignKey("entities.id"), nullable=False, index=True)
    target_entity_id = Column(String(36), ForeignKey("entities.id"), nullable=False, index=True)
    relationship_type = Column(String(100), nullable=False)  # Issued By, Belongs To, Director Of, References, Mentions, Appeal Against, etc.
    properties_json = Column(JSON, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Citation(Base):
    __tablename__ = "citations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    source_document_id = Column(String(36), nullable=True, index=True)  # Can reference raw_documents or government_updates
    target_entity_id = Column(String(36), ForeignKey("entities.id"), nullable=True, index=True)
    text_reference = Column(Text, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Phase 4 extensions
    source_type = Column(String(50), nullable=True, index=True)  # CLIENT_DOCUMENT, GOVERNMENT_UPDATE, etc.
    government_update_id = Column(String(36), nullable=True, index=True)
    client_id = Column(String(36), nullable=True, index=True)
    page_number = Column(Integer, nullable=True)
    paragraph_number = Column(Integer, nullable=True)
    line_start = Column(Integer, nullable=True)
    line_end = Column(Integer, nullable=True)
    section_reference = Column(String(255), nullable=True)
    act_reference = Column(String(255), nullable=True)
    rule_reference = Column(String(255), nullable=True)
    circular_number = Column(String(255), nullable=True)
    notification_number = Column(String(255), nullable=True)
    judgment_reference = Column(String(255), nullable=True)
    quote_text = Column(Text, nullable=True)
    normalized_text = Column(Text, nullable=True)
    source_url = Column(String(512), nullable=True)
    confidence_score = Column(Float, default=1.0, nullable=True)



class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    raw_document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    file_path = Column(String(512), nullable=False)
    change_summary = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProcessingPipeline(Base):
    __tablename__ = "processing_pipeline"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    raw_document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False, index=True)
    current_step = Column(String(50), nullable=False)  # UPLOAD, OCR, PARSE, ENTITIES, EMBEDDINGS, KNOWLEDGE, COMPLETE
    status = Column(String(50), default="PENDING", nullable=False)  # PENDING, PROCESSING, SUCCESS, FAILED
    retries = Column(Integer, default=0, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProcessingError(Base):
    __tablename__ = "processing_errors"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    pipeline_id = Column(String(36), ForeignKey("processing_pipeline.id"), nullable=False, index=True)
    step_name = Column(String(50), nullable=False)
    error_message = Column(Text, nullable=False)
    stack_trace = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KnowledgeGraphNode(Base):
    __tablename__ = "knowledge_graph_nodes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    node_type = Column(String(50), nullable=False, index=True)  # Client, Firm, Employee, Notice, Act, Section, Circular, Case, Court, Assessment, Invoice, Return, Bank, Vendor, Director, Company
    label = Column(String(255), nullable=False)
    properties_json = Column(JSON, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KnowledgeGraphEdge(Base):
    __tablename__ = "knowledge_graph_edges"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    source_node_id = Column(String(36), ForeignKey("knowledge_graph_nodes.id"), nullable=False, index=True)
    target_node_id = Column(String(36), ForeignKey("knowledge_graph_nodes.id"), nullable=False, index=True)
    relationship = Column(String(100), nullable=False)  # Issued, Belongs To, Filed By, References, Depends On, Supersedes, Related To, Mentions, Against, Appealed, Supports, Conflicts
    properties_json = Column(JSON, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GovernmentSource(Base):
    __tablename__ = "government_sources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=False)  # Income Tax, GST, MCA, CBIC, CBDT, ICAI, SEBI, RBI
    official_url = Column(String(512), nullable=False)
    requires_auth = Column(Boolean, default=False, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Phase 3 Fields
    health = Column(String(50), default="HEALTHY", nullable=False)
    sync_frequency = Column(String(100), default="DAILY", nullable=False)
    last_success = Column(DateTime, nullable=True)
    last_failure = Column(DateTime, nullable=True)
    average_response_time = Column(Float, default=0.0, nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    total_documents_count = Column(Integer, default=0, nullable=False)
    version_count = Column(Integer, default=0, nullable=False)
    rate_limits = Column(String(100), default="60/minute", nullable=False)
    connector_status = Column(String(50), default="RUNNING", nullable=False)
    auth_requirements = Column(String(255), default="NONE", nullable=False)


class GovernmentUpdate(Base):
    __tablename__ = "government_updates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_id = Column(String(36), ForeignKey("government_sources.id"), nullable=False)
    title = Column(String(512), nullable=False)
    issuing_authority = Column(String(255), nullable=True)
    issue_date = Column(DateTime, nullable=True)
    effective_date = Column(DateTime, nullable=True)
    source_url = Column(String(512), nullable=True)
    document_number = Column(String(100), nullable=True, index=True)
    version = Column(Integer, default=1, nullable=False)
    superseded_by = Column(String(36), nullable=True)
    related_acts = Column(JSON, nullable=True)
    referenced_sections = Column(JSON, nullable=True)
    keywords = Column(JSON, nullable=True)
    summary = Column(Text, nullable=True)
    raw_file_path = Column(String(512), nullable=True)
    html_content = Column(Text, nullable=True)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ParserRegistry(Base):
    __tablename__ = "parser_registry"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    parser_name = Column(String(100), nullable=False)
    parser_class = Column(String(255), nullable=False)
    supported_categories = Column(JSON, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AIJob(Base):
    __tablename__ = "ai_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    job_type = Column(String(50), nullable=False)  # OCR, EMBEDDING, PARSE
    status = Column(String(50), default="PENDING", nullable=False)  # PENDING, PROCESSING, COMPLETED, FAILED
    payload_json = Column(JSON, nullable=True)
    result_json = Column(JSON, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==============================================================================
# PHASE 3 MODELS: GOVERNMENT KNOWLEDGE ACQUISITION PLATFORM
# ==============================================================================

class GovernmentUpdateVersion(Base):
    __tablename__ = "government_update_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    government_update_id = Column(String(36), ForeignKey("government_updates.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    raw_file_path = Column(String(512), nullable=True)
    html_content = Column(Text, nullable=True)
    markdown_content = Column(Text, nullable=True)
    checksum = Column(String(64), nullable=False)
    added_paragraphs = Column(JSON, nullable=True)
    removed_paragraphs = Column(JSON, nullable=True)
    changed_sections = Column(JSON, nullable=True)
    effective_date = Column(DateTime, nullable=True)
    structured_differences = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ConnectorSyncLog(Base):
    __tablename__ = "connector_sync_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_id = Column(String(36), ForeignKey("government_sources.id"), nullable=False)
    sync_time = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), nullable=False)  # SUCCESS, FAILED
    documents_downloaded = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, default=0, nullable=False)


class CitationVerification(Base):
    __tablename__ = "citation_verifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    citation_id = Column(String(36), ForeignKey("citations.id"), nullable=False)
    status = Column(String(50), default="PENDING", nullable=False)  # VERIFIED, PARTIALLY_VERIFIED, FAILED, PENDING
    details_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EntityAlias(Base):
    __tablename__ = "entity_aliases"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    entity_id = Column(String(36), ForeignKey("entities.id"), nullable=False)
    alias_text = Column(String(512), nullable=False)
    alias_type = Column(String(100), default="EXACT", nullable=False)  # EXACT, NORMALIZED, FUZZY, IDENTIFIER
    confidence_score = Column(Float, default=1.0, nullable=False)
    created_by = Column(String(100), default="SYSTEM", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GraphBuildJob(Base):
    __tablename__ = "graph_build_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    source_type = Column(String(50), nullable=False)  # DOCUMENT, GOVERNMENT_UPDATE
    source_id = Column(String(36), nullable=False)
    status = Column(String(50), default="PENDING", nullable=False)  # PENDING, PROCESSING, SUCCESS, FAILED
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LegalReference(Base):
    __tablename__ = "legal_references"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    reference_type = Column(String(50), nullable=False)  # SECTION, RULE, CIRCULAR, NOTIFICATION, etc.
    value = Column(String(255), nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SourceClaim(Base):
    __tablename__ = "source_claims"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    claim_text = Column(Text, nullable=False)
    citation_id = Column(String(36), ForeignKey("citations.id"), nullable=False)
    verification_status = Column(String(50), default="PENDING", nullable=False)  # VERIFIED, PARTIALLY_VERIFIED, FAILED, PENDING
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Form26ASEntry(Base):
    __tablename__ = "form26as_entries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id"), nullable=True)
    document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False, index=True)
    pan = Column(String(10), nullable=True)
    assessment_year = Column(String(10), nullable=True)
    financial_year = Column(String(10), nullable=True)
    taxpayer_name = Column(String(255), nullable=True)
    deductor_name = Column(String(255), nullable=True)
    deductor_tan = Column(String(10), nullable=True)
    section = Column(String(50), nullable=True)
    section_code = Column(String(50), nullable=True)
    amount_paid = Column(Float, nullable=True)
    amount_credited = Column(Float, nullable=True)
    tax_deducted = Column(Float, nullable=True)
    tax_deposited = Column(Float, nullable=True)
    refund = Column(Float, nullable=True)
    interest = Column(Float, nullable=True)
    demand = Column(Float, nullable=True)
    raw_row_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AISEntry(Base):
    __tablename__ = "ais_entries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id"), nullable=True)
    document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False, index=True)
    pan = Column(String(10), nullable=True)
    taxpayer_name = Column(String(255), nullable=True)
    assessment_year = Column(String(10), nullable=True)
    financial_year = Column(String(10), nullable=True)
    information_category = Column(String(100), nullable=True)
    information_source = Column(String(100), nullable=True)
    source_name = Column(String(255), nullable=True)
    reported_value = Column(Float, nullable=True)
    processed_value = Column(Float, nullable=True)
    accepted_value = Column(Float, nullable=True)
    derived_value = Column(Float, nullable=True)
    transaction_type = Column(String(50), nullable=True)
    raw_row_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class GSTNoticeEntry(Base):
    __tablename__ = "gst_notice_entries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False, index=True)
    gstin = Column(String(15), nullable=True)
    notice_number = Column(String(100), nullable=True)
    issue_date = Column(DateTime, nullable=True)
    reply_due_date = Column(DateTime, nullable=True)
    section = Column(String(100), nullable=True)
    authority = Column(String(255), nullable=True)
    tax_period = Column(String(50), nullable=True)
    amount = Column(Float, nullable=True)
    penalty = Column(Float, nullable=True)
    interest = Column(Float, nullable=True)
    reason = Column(Text, nullable=True)
    risk_level = Column(String(50), nullable=True)
    referenced_sections = Column(Text, nullable=True)
    referenced_notifications = Column(Text, nullable=True)
    referenced_circulars = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BankStatementTransaction(Base):
    __tablename__ = "bank_statement_transactions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False, index=True)
    account_holder = Column(String(255), nullable=True)
    bank_name = Column(String(255), nullable=True)
    account_number = Column(String(100), nullable=True)
    ifsc = Column(String(20), nullable=True)
    opening_balance = Column(Float, nullable=True)
    closing_balance = Column(Float, nullable=True)
    transaction_date = Column(DateTime, nullable=True)
    particulars = Column(Text, nullable=True)
    transaction_type = Column(String(10), nullable=True)  # DEBIT / CREDIT
    amount = Column(Float, nullable=True)
    balance = Column(Float, nullable=True)
    upi_ref = Column(String(100), nullable=True)
    neft_rtgs_ref = Column(String(100), nullable=True)
    cheque_number = Column(String(50), nullable=True)
    narration = Column(Text, nullable=True)
    running_balance = Column(Float, nullable=True)
    monthly_summary = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BalanceSheetItem(Base):
    __tablename__ = "balance_sheet_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False, index=True)
    financial_year = Column(String(10), nullable=True)
    assets = Column(Float, nullable=True)
    liabilities = Column(Float, nullable=True)
    equity = Column(Float, nullable=True)
    current_assets = Column(Float, nullable=True)
    current_liabilities = Column(Float, nullable=True)
    non_current_assets = Column(Float, nullable=True)
    fixed_assets = Column(Float, nullable=True)
    loans = Column(Float, nullable=True)
    reserves = Column(Float, nullable=True)
    capital = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class FinancialRatio(Base):
    __tablename__ = "financial_ratios"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False, index=True)
    current_ratio = Column(Float, nullable=True)
    quick_ratio = Column(Float, nullable=True)
    debt_to_equity = Column(Float, nullable=True)
    return_on_equity = Column(Float, nullable=True)
    working_capital = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TaxSummary(Base):
    __tablename__ = "tax_summaries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False, index=True)
    total_taxable_income = Column(Float, nullable=True)
    total_tax_paid = Column(Float, nullable=True)
    refund_claimed = Column(Float, nullable=True)
    interest_payable = Column(Float, nullable=True)
    outstanding_demand = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ChallanEntry(Base):
    __tablename__ = "challan_entries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False, index=True)
    challan_number = Column(String(50), nullable=True)
    bsr_code = Column(String(20), nullable=True)
    date_of_deposit = Column(DateTime, nullable=True)
    amount = Column(Float, nullable=True)
    tax_period = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DeductorEntry(Base):
    __tablename__ = "deductor_entries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False, index=True)
    deductor_name = Column(String(255), nullable=True)
    deductor_tan = Column(String(10), nullable=True)
    total_tds = Column(Float, nullable=True)
    total_tcs = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DocumentAISummary(Base):
    __tablename__ = "document_ai_summaries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False, index=True)
    summary_text = Column(Text, nullable=True)
    key_insights = Column(JSON, nullable=True)
    compliance_issues = Column(JSON, nullable=True)
    missing_information = Column(JSON, nullable=True)
    suggested_actions = Column(JSON, nullable=True)
    risk_level = Column(String(50), default="LOW")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ClientTaxProfile(Base):
    __tablename__ = "client_tax_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id"), nullable=False)
    pan = Column(String(10), nullable=True)
    taxpayer_name = Column(String(255), nullable=True)
    assessment_year = Column(String(10), nullable=False)
    financial_year = Column(String(10), nullable=True)
    latest_upload_date = Column(DateTime, nullable=True)
    processing_status = Column(String(50), default="PENDING")
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ClientTaxSummary(Base):
    __tablename__ = "client_tax_summaries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id"), nullable=False)
    assessment_year = Column(String(10), nullable=False)
    financial_year = Column(String(10), nullable=True)
    total_tds = Column(Float, default=0.0)
    total_reported_income = Column(Float, default=0.0)
    interest_income = Column(Float, default=0.0)
    dividend_income = Column(Float, default=0.0)
    salary_income = Column(Float, default=0.0)
    securities_transactions = Column(Float, default=0.0)
    mutual_fund_transactions = Column(Float, default=0.0)
    property_transactions = Column(Float, default=0.0)
    sft_transactions = Column(Float, default=0.0)
    other_income = Column(Float, default=0.0)
    refund_amount = Column(Float, default=0.0)
    demand_amount = Column(Float, default=0.0)
    deductor_count = Column(Integer, default=0)
    ais_category_count = Column(Integer, default=0)
    high_value_transactions = Column(Integer, default=0)
    documents_processed = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ClientTaxInsight(Base):
    __tablename__ = "client_tax_insights"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id"), nullable=False)
    assessment_year = Column(String(10), nullable=False)
    severity = Column(String(50), default="INFO")
    description = Column(Text, nullable=False)
    supporting_documents = Column(JSON, nullable=True)
    supporting_records = Column(JSON, nullable=True)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class DocumentRelationship(Base):
    __tablename__ = "document_relationships"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id"), nullable=False)
    source_document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False)
    target_document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False)
    relationship_type = Column(String(100), default="CORRELATED")
    created_at = Column(DateTime, default=datetime.utcnow)


class DocumentMatch(Base):
    __tablename__ = "document_matches"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id"), nullable=False)
    assessment_year = Column(String(10), nullable=False)
    match_type = Column(String(100), default="TDS_MATCH")
    description = Column(Text, nullable=False)
    amount = Column(Float, nullable=True)
    source_record_id = Column(String(36), nullable=True)
    target_record_id = Column(String(36), nullable=True)
    status = Column(String(50), default="MATCHED")
    created_at = Column(DateTime, default=datetime.utcnow)


class ITRProfile(Base):
    __tablename__ = "itr_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id"), nullable=False)
    assessment_year = Column(String(10), nullable=False)
    financial_year = Column(String(10), nullable=True)
    itr_status = Column(String(50), default="NOT_STARTED")
    documents_uploaded = Column(JSON, nullable=True)
    data_completeness_score = Column(Float, default=0.0)
    processing_status = Column(String(50), default="PENDING")
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ITRReadiness(Base):
    __tablename__ = "itr_readiness"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id"), nullable=False)
    assessment_year = Column(String(10), nullable=False)
    readiness_score = Column(Float, default=0.0)
    reasons = Column(JSON, nullable=True)
    collected_documents = Column(JSON, nullable=True)
    missing_documents = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ITRActionItem(Base):
    __tablename__ = "itr_action_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id"), nullable=False)
    assessment_year = Column(String(10), nullable=False)
    action_text = Column(Text, nullable=False)
    severity = Column(String(50), default="INFO")
    reference_document = Column(String(255), nullable=True)
    status = Column(String(50), default="PENDING")
    created_at = Column(DateTime, default=datetime.utcnow)


class ITRVerificationResult(Base):
    __tablename__ = "itr_verification_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id"), nullable=False)
    assessment_year = Column(String(10), nullable=False)
    verification_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(50), default="PASS")
    created_at = Column(DateTime, default=datetime.utcnow)


class TISEntry(Base):
    __tablename__ = "tis_entries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id"), nullable=False)
    document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False, index=True)
    pan = Column(String(10), nullable=True)
    assessment_year = Column(String(10), nullable=False)
    financial_year = Column(String(10), nullable=True)
    category = Column(String(100), nullable=True)
    subcategory = Column(String(100), nullable=True)
    reported_value = Column(Float, default=0.0)
    derived_value = Column(Float, default=0.0)
    feedback_value = Column(Float, default=0.0)
    transaction_type = Column(String(50), default="INCOME")
    raw_row_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ResearchSource(Base):
    __tablename__ = "research_sources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    authority = Column(String(100), nullable=False)
    section = Column(String(100), nullable=True)
    rule_number = Column(String(100), nullable=True)
    circular_number = Column(String(100), nullable=True)
    notification_number = Column(String(100), nullable=True)
    publication_date = Column(DateTime, nullable=True)
    effective_date = Column(DateTime, nullable=True)
    url = Column(String(512), nullable=True)
    category = Column(String(100), nullable=True)
    keywords = Column(Text, nullable=True)
    version = Column(String(50), default="1.0")
    status = Column(String(50), default="ACTIVE")
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ResearchQuery(Base):
    __tablename__ = "research_queries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id"), nullable=True)
    query_text = Column(Text, nullable=False)
    filters_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ResearchResult(Base):
    __tablename__ = "research_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    query_id = Column(String(36), ForeignKey("research_queries.id"), nullable=False)
    summary = Column(Text, nullable=False)
    applicable_law = Column(Text, nullable=True)
    relevant_sections = Column(Text, nullable=True)
    relevant_circulars = Column(Text, nullable=True)
    relevant_notifications = Column(Text, nullable=True)
    considerations = Column(Text, nullable=True)
    risks = Column(Text, nullable=True)
    confidence = Column(Float, default=100.0)
    references_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ResearchBookmark(Base):
    __tablename__ = "research_bookmarks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    source_id = Column(String(36), ForeignKey("research_sources.id"), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ResearchNote(Base):
    __tablename__ = "research_notes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id"), nullable=True)
    assessment_year = Column(String(10), nullable=True)
    document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    section_reference = Column(String(100), nullable=True)
    authority_reference = Column(String(100), nullable=True)
    tags = Column(String(255), nullable=True)
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ClientTask(Base):
    __tablename__ = "client_tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id"), nullable=False)
    task_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="PENDING")  # PENDING, IN_PROGRESS, COMPLETED, DEFERRED
    linked_to = Column(String(50), nullable=True)  # CLIENT, DOCUMENT, RESEARCH, ITR, TAX_INTELLIGENCE
    linked_id = Column(String(36), nullable=True)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ClientTimelineEvent(Base):
    __tablename__ = "client_timeline_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id"), nullable=False)
    event_type = Column(String(100), nullable=False)  # CLIENT_CREATED, DOCUMENT_UPLOADED, etc.
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

