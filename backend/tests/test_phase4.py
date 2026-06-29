import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.models import Organization, User, Client, RawDocument, ProcessedDocument, Entity, EntityAlias, Citation, GovernmentUpdate
from app.services.extractor import LegalReferenceExtractor
from app.services.citation import CitationEngine
from app.services.graph import GraphService, normalize_entity_name
from app.services.verification import SourceVerificationEngine

# Setup SQLite in-memory test database
SQL_TEST_URL = "sqlite://"
engine = create_engine(
    SQL_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Seed Organization and User
    org = Organization(id="org-test-id", organization_name="Test Firm", firm_type="Partnership", contact_email="test@firm.com")
    user = User(
        id="user-test-id",
        organization_id="org-test-id",
        email="test@firm.com",
        hashed_password="fakehashpwd123",
        first_name="Jane",
        last_name="Doe",
        role="FIRM_ADMIN",
        is_active=True
    )
    db.add(org)
    db.add(user)
    db.commit()
    db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)

def get_auth_token():
    # Helper to generate JWT token payload
    from jose import jwt
    from app.core.config import settings
    token_data = {"sub": "test@firm.com"}
    return jwt.encode(token_data, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

# ==========================================
# 1. REFERENCE EXTRACTION TESTS
# ==========================================
def test_legal_reference_extractor():
    text = (
        "Under Section 139(1) of the Income Tax Act, every person must file GSTR-1. "
        "Also refer to Rule 37A and Notification No. 12/2024. "
        "Assessment Year 2024-25 is active. Client PAN is ABCDE1234F, GSTIN is 27ABCDE1234F1Z1."
    )
    extracted = LegalReferenceExtractor.extract_all(text)
    
    assert "139(1)" in extracted["SECTION"]
    assert "37A" in extracted["RULE"]
    assert "12/2024" in extracted["NOTIFICATION"]
    assert "2024-25" in extracted["ASSESSMENT_YEAR"]
    assert "ABCDE1234F" in extracted["PAN"]
    assert "27ABCDE1234F1Z1" in extracted["GSTIN"]
    assert "GSTR-1" in extracted["FORM"]

# ==========================================
# 2. CITATION & VERIFICATION TESTS
# ==========================================
def test_citation_creation_and_verification():
    db = TestingSessionLocal()
    org_id = "org-test-id"
    
    # Create Raw & Processed Document
    raw = RawDocument(id="doc-123", organization_id=org_id, name="Notice.txt", file_path="uploads/Notice.txt", file_size=100, mime_type="text/plain", sha256_hash="fakesha256hash", md5_hash="fakemd5hash")
    db.add(raw)
    db.commit()
    
    proc = ProcessedDocument(
        organization_id=org_id,
        raw_document_id="doc-123",
        ocr_text="Notice regarding Section 148 under Assessment Year 2023-24. Please comply.",
        normalized_text="Notice regarding Section 148 under Assessment Year 2023-24. Please comply."
    )
    db.add(proc)
    db.commit()

    # Generate Citations
    citations = CitationEngine.extract_and_create_citations(
        db=db,
        organization_id=org_id,
        text=proc.ocr_text,
        source_type="CLIENT_DOCUMENT",
        source_document_id="doc-123"
    )
    
    assert len(citations) > 0
    citation_id = citations[0].id
    
    # Run claim verification
    res = SourceVerificationEngine.verify_citation(db, org_id, citation_id)
    assert res["status"] in ["VERIFIED", "PARTIALLY_VERIFIED"]
    assert res["score"] > 0.5
    
    db.close()

# ==========================================
# 3. ENTITY RESOLUTION TESTS
# ==========================================
def test_entity_resolution_and_merge():
    db = TestingSessionLocal()
    org_id = "org-test-id"
    
    # Normalize name helper check
    assert normalize_entity_name("A. K. Kataruka & Co. Ltd.") == "akkataruka"
    
    # Resolve entity matching
    e1 = GraphService.resolve_entity(db, org_id, "Company", "A K Kataruka & Co")
    e2 = GraphService.resolve_entity(db, org_id, "Company", "A.K. Kataruka and Company")
    
    # Should resolve to the same primary entity due to normalized name matching
    assert e1.id == e2.id
    
    # Test manual merge
    e3 = GraphService.resolve_entity(db, org_id, "Company", "Different Company Name")
    assert e1.id != e3.id
    
    success = GraphService.merge_entities(db, org_id, e1.id, e3.id)
    assert success is True
    
    # Verify entity aliases
    alias = db.query(EntityAlias).filter(EntityAlias.alias_text == "Different Company Name").first()
    assert alias is not None
    assert alias.entity_id == e1.id
    
    db.close()

# ==========================================
# 4. API ROUTER TESTS
# ==========================================
def test_citation_router_endpoints():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # List citations
    res = client.get("/api/v1/citations", headers=headers)
    assert res.status_code == 200
    
    # Create manual citation
    payload = {
        "source_type": "CLIENT_DOCUMENT",
        "quote_text": "Section 143(1) intimation",
        "section_reference": "143(1)",
        "act_reference": "Income Tax Act"
    }
    res = client.post("/api/v1/citations", json=payload, headers=headers)
    assert res.status_code == 200
    citation_id = res.json()["id"]
    
    # Get citation details
    res = client.get(f"/api/v1/citations/{citation_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["section_reference"] == "143(1)"

def test_graph_router_endpoints():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # List nodes
    res = client.get("/api/v1/graph/nodes", headers=headers)
    assert res.status_code == 200
    
    # List edges
    res = client.get("/api/v1/graph/edges", headers=headers)
    assert res.status_code == 200
    
    # Search nodes
    res = client.get("/api/v1/graph/search?q=test", headers=headers)
    assert res.status_code == 200
