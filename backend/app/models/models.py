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
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
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
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    client_name = Column(String(255), nullable=False)
    client_type = Column(String(50), nullable=False)  # Individual / Proprietorship / Partnership / LLP / Company / Trust / HUF / Other
    PAN = Column(String(10), nullable=True)
    GSTIN = Column(String(15), nullable=True)
    CIN_LLPIN = Column(String(21), nullable=True)
    TAN = Column(String(10), nullable=True)
    registered_address = Column(Text, nullable=True)
    contact_person = Column(String(100), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    industry = Column(String(100), nullable=True)
    status = Column(String(50), default="ACTIVE")  # ACTIVE / INACTIVE / ARCHIVED
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
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id"), nullable=True)
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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)


class ProcessedDocument(Base):
    __tablename__ = "processed_documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    raw_document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False)
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
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    raw_document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False)
    parser_name = Column(String(100), nullable=False)
    extraction_date = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StructuredInvoiceData(Base):
    __tablename__ = "structured_invoice_data"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    raw_document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False)
    GSTIN = Column(String(15), nullable=True)
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
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    raw_document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False)
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
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    processed_document_id = Column(String(36), ForeignKey("processed_documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text_content = Column(Text, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    knowledge_chunk_id = Column(String(36), ForeignKey("knowledge_chunks.id"), nullable=False)
    embedding_vector = Column(JSON, nullable=False)  # Stores float vector list
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Entity(Base):
    __tablename__ = "entities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    entity_type = Column(String(100), nullable=False)  # PAN, GSTIN, TAN, DIN, CIN, LLPIN, Name, Address, Company, Person, Court, Act, Section, Rule
    value = Column(String(512), nullable=False)
    metadata_json = Column(JSON, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EntityRelationship(Base):
    __tablename__ = "entity_relationships"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    source_entity_id = Column(String(36), ForeignKey("entities.id"), nullable=False)
    target_entity_id = Column(String(36), ForeignKey("entities.id"), nullable=False)
    relationship_type = Column(String(100), nullable=False)  # Issued By, Belongs To, Director Of, References, Mentions, Appeal Against, etc.
    properties_json = Column(JSON, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Citation(Base):
    __tablename__ = "citations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    source_document_id = Column(String(36), nullable=False)  # Can reference raw_documents or government_updates
    target_entity_id = Column(String(36), ForeignKey("entities.id"), nullable=False)
    text_reference = Column(Text, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    raw_document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False)
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
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    raw_document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False)
    current_step = Column(String(50), nullable=False)  # UPLOAD, OCR, PARSE, ENTITIES, EMBEDDINGS, KNOWLEDGE, COMPLETE
    status = Column(String(50), default="PENDING", nullable=False)  # PENDING, PROCESSING, SUCCESS, FAILED
    retries = Column(Integer, default=0, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProcessingError(Base):
    __tablename__ = "processing_errors"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    pipeline_id = Column(String(36), ForeignKey("processing_pipeline.id"), nullable=False)
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
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    node_type = Column(String(50), nullable=False)  # Client, Firm, Employee, Notice, Act, Section, Circular, Case, Court, Assessment, Invoice, Return, Bank, Vendor, Director, Company
    label = Column(String(255), nullable=False)
    properties_json = Column(JSON, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KnowledgeGraphEdge(Base):
    __tablename__ = "knowledge_graph_edges"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    source_node_id = Column(String(36), ForeignKey("knowledge_graph_nodes.id"), nullable=False)
    target_node_id = Column(String(36), ForeignKey("knowledge_graph_nodes.id"), nullable=False)
    relationship = Column(String(100), nullable=False)  # Issued, Belongs To, Filed By, References, Depends On, Supersedes, Related To, Mentions, Against, Appealed, Supports, Conflicts
    properties_json = Column(JSON, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GovernmentSource(Base):
    __tablename__ = "government_sources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)  # Income Tax, GST, MCA, CBIC, CBDT, ICAI, SEBI, RBI
    official_url = Column(String(512), nullable=False)
    requires_auth = Column(Boolean, default=False, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GovernmentUpdate(Base):
    __tablename__ = "government_updates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_id = Column(String(36), ForeignKey("government_sources.id"), nullable=False)
    title = Column(String(512), nullable=False)
    issuing_authority = Column(String(255), nullable=True)
    issue_date = Column(DateTime, nullable=True)
    effective_date = Column(DateTime, nullable=True)
    source_url = Column(String(512), nullable=True)
    document_number = Column(String(100), nullable=True)
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
