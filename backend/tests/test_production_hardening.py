import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import io

import app.core.database as database_module
from app.main import app
from app.core.database import Base, get_db
from app.models.models import Organization, User, Client, Document, ComplianceSource, Citation, GovernmentUpdate
from app.services.connectors.registry import ConnectorRegistry
from app.core.security import hash_password
from app.services.citation import CitationEngine

# Setup SQLite in-memory test database
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
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
def run_around_tests():
    # Setup: re-assert this module's override on every test, since app.dependency_overrides
    # is a single dict shared across every test module importing the same `app` singleton -
    # whichever module set it last (at import time or in another module's fixture) otherwise wins.
    app.dependency_overrides[get_db] = override_get_db
    # Document upload triggers a background pipeline task that imports app.core.database.SessionLocal
    # directly (bypassing FastAPI's dependency-injection override) - patch it too so background
    # processing during this test hits the same in-memory test DB, not the real configured one.
    original_session_local = database_module.SessionLocal
    database_module.SessionLocal = TestingSessionLocal
    # Setup: Create tables
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    # Seed compliance sources for test environment
    from app.core.seeds import seed_compliance_sources
    seed_compliance_sources(db)
    db.close()
    yield
    # Teardown: Drop all tables and overrides
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()
    database_module.SessionLocal = original_session_local
    app.dependency_overrides[get_db] = override_get_db

def create_test_auth_headers():
    # Register Organization & Admin
    reg_payload = {
        "organization_name": "Test Firm",
        "firm_type": "Proprietorship",
        "GSTIN": "27TESTF1234A1Z0",
        "PAN": "TESTF1234A",
        "address": "Mumbai",
        "contact_email": "admin@testfirm.com",
        "phone": "+91-9876543210",
        "admin_first_name": "Test",
        "admin_last_name": "Admin",
        "admin_email": "admin@testfirm.com",
        "admin_password": "securepassword123"
    }
    reg_response = client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_clients_pagination():
    headers = create_test_auth_headers()
    
    # Create 5 test clients
    for i in range(5):
        client.post("/api/v1/clients", json={
            "client_name": f"Client {i}",
            "client_type": "Corporate",
            "GSTIN": f"27ABCDE123{i}A1Z0",
            "PAN": f"ABCDE123{i}A",
            "TAN": f"MUMA1234{i}A",
            "email": f"client{i}@test.com",
            "phone": "+91-9999999999"
        }, headers=headers)
        
    # Get all clients
    res_all = client.get("/api/v1/clients", headers=headers)
    assert res_all.status_code == 200
    assert len(res_all.json()) == 5
    
    # Get limited clients
    res_limit = client.get("/api/v1/clients?limit=2", headers=headers)
    assert res_limit.status_code == 200
    assert len(res_limit.json()) == 2
    
    # Get paginated skip
    res_skip = client.get("/api/v1/clients?skip=3&limit=2", headers=headers)
    assert res_skip.status_code == 200
    assert len(res_skip.json()) == 2
    assert res_skip.json()[0]["client_name"] == "Client 3"
    assert res_skip.json()[1]["client_name"] == "Client 4"

def test_compliance_sources_pagination():
    headers = create_test_auth_headers()
    
    res_all = client.get("/api/v1/compliance/sources", headers=headers)
    assert res_all.status_code == 200
    total_sources = len(res_all.json())
    assert total_sources > 0
    
    res_limit = client.get(f"/api/v1/compliance/sources?limit=2", headers=headers)
    assert res_limit.status_code == 200
    assert len(res_limit.json()) == 2

def test_citation_deduplication():
    headers = create_test_auth_headers()
    db = TestingSessionLocal()
    
    # Query to fetch an organization ID
    user = db.query(User).filter(User.email == "admin@testfirm.com").first()
    org_id = user.organization_id
    
    # Create citation 1
    cit1 = CitationEngine.create_citation(
        db=db,
        organization_id=org_id,
        source_type="GST_NOTICE",
        paragraph_number=12,
        section_reference="Section 73",
        act_reference="CGST Act",
        quote_text="Tax short paid"
    )
    
    # Create identical citation
    cit2 = CitationEngine.create_citation(
        db=db,
        organization_id=org_id,
        source_type="GST_NOTICE",
        paragraph_number=12,
        section_reference="Section 73",
        act_reference="CGST Act",
        quote_text="Tax short paid"
    )
    
    # Verify that the returned objects are identical (duplicate prevention)
    assert cit1.id == cit2.id
    
    # Check total citations count in db is 1
    count = db.query(Citation).filter(Citation.organization_id == org_id).count()
    assert count == 1
    db.close()

def test_file_signature_validation():
    headers = create_test_auth_headers()
    
    # Create a dummy client
    c_res = client.post("/api/v1/clients", json={
        "client_name": "Test Client",
        "client_type": "Corporate",
        "GSTIN": "27ABCDE1234A1Z0",
        "PAN": "ABCDE1234A",
        "email": "test@client.com",
        "phone": "+91-9999999999"
    }, headers=headers)
    client_id = c_res.json()["id"]

    # 1. Invalid PDF file upload (no PDF header magic bytes)
    bad_pdf = io.BytesIO(b"Hello World, this is not a PDF")
    res_bad_pdf = client.post(
        "/api/v1/documents/upload",
        data={"category": "NOTICE", "client_id": client_id},
        files={"file": ("fake.pdf", bad_pdf, "application/pdf")},
        headers=headers
    )
    assert res_bad_pdf.status_code == 400
    assert "does not match PDF format" in res_bad_pdf.json()["detail"]

    # 2. Valid PDF upload (starts with %PDF-)
    good_pdf = io.BytesIO(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj")
    res_good_pdf = client.post(
        "/api/v1/documents/upload",
        data={"category": "NOTICE", "client_id": client_id},
        files={"file": ("real.pdf", good_pdf, "application/pdf")},
        headers=headers
    )
    assert res_good_pdf.status_code == 201
    assert res_good_pdf.json()["name"] == "real.pdf"

    # 3. Invalid PNG upload
    bad_png = io.BytesIO(b"Fake PNG content")
    res_bad_png = client.post(
        "/api/v1/documents/upload",
        data={"category": "INVOICE", "client_id": client_id},
        files={"file": ("fake.png", bad_png, "image/png")},
        headers=headers
    )
    assert res_bad_png.status_code == 400
    assert "does not match PNG format" in res_bad_png.json()["detail"]

def test_telemetry_config_route():
    headers = create_test_auth_headers()

    response = client.get("/api/v1/observability/config", headers=headers)
    assert response.status_code == 200
    config_data = response.json()
    assert "llm_provider" in config_data
    assert "ocr_provider" in config_data
    assert "embedding_provider" in config_data
    assert "storage_provider" in config_data
    assert "env" in config_data


def test_archive_government_document():
    headers = create_test_auth_headers()

    db = TestingSessionLocal()
    egazette = ConnectorRegistry.get_connector("e-Gazette")
    result = egazette.sync(db)
    assert result["status"] == "SUCCESS"
    doc = db.query(GovernmentUpdate).filter_by(document_number="Gazette No. DL-33/2026").first()
    assert doc is not None
    doc_id = doc.id
    db.close()

    res = client.delete(f"/api/v1/compliance/connectors/documents/{doc_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    search_res = client.get("/api/v1/compliance/connectors/documents", headers=headers)
    assert search_res.status_code == 200
    assert all(d["id"] != doc_id for d in search_res.json())

    missing_res = client.delete("/api/v1/compliance/connectors/documents/not-a-real-id", headers=headers)
    assert missing_res.status_code == 404
