import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Text, JSON
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
