import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta
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


def test_compliance_types_registry():
    headers = create_test_auth_headers()
    res = client.get("/api/v1/compliance/types", headers=headers)
    assert res.status_code == 200
    types = res.json()
    keys = {t["key"] for t in types}
    assert keys == {"GST", "Income Tax", "TDS", "TCS", "MCA/ROC", "PF", "ESI", "Professional Tax"}

    tds = next(t for t in types if t["key"] == "TDS")
    assert tds["is_nationally_uniform"] is True
    assert tds["default_frequency"] == "MONTHLY"
    assert tds["default_due_day"] == 7

    prof_tax = next(t for t in types if t["key"] == "Professional Tax")
    assert prof_tax["is_nationally_uniform"] is False
    assert prof_tax["default_due_day"] is None
    assert "state" in prof_tax["limitations"].lower()


def test_compliance_profile_create_applies_registry_default():
    headers = create_test_auth_headers()
    c_res = client.post("/api/v1/clients", json={"client_name": "Registry Default Co", "client_type": "Corporate"}, headers=headers)
    client_id = c_res.json()["id"]

    # No frequency/due_day supplied - should pick up TDS's real registry default (MONTHLY, 7th)
    res = client.post("/api/v1/compliance/profile", json={
        "client_id": client_id,
        "compliance_type": "TDS",
    }, headers=headers)
    assert res.status_code == 200
    profile = res.json()
    assert profile["frequency"] == "MONTHLY"
    assert profile["due_day"] == 7


def test_compliance_profile_update():
    headers = create_test_auth_headers()
    c_res = client.post("/api/v1/clients", json={"client_name": "Profile Update Co", "client_type": "Corporate"}, headers=headers)
    client_id = c_res.json()["id"]

    create_res = client.post("/api/v1/compliance/profile", json={
        "client_id": client_id,
        "compliance_type": "GST",
        "frequency": "MONTHLY",
        "due_day": 20,
    }, headers=headers)
    profile_id = create_res.json()["id"]

    update_res = client.put(f"/api/v1/compliance/profile/{profile_id}", json={
        "frequency": "QUARTERLY",
        "due_day": 22,
        "risk_level": "HIGH",
    }, headers=headers)
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["frequency"] == "QUARTERLY"
    assert updated["due_day"] == 22
    assert updated["risk_level"] == "HIGH"
    # Unspecified fields are left untouched
    assert updated["compliance_type"] == "GST"

    missing_res = client.put("/api/v1/compliance/profile/not-a-real-id", json={"due_day": 5}, headers=headers)
    assert missing_res.status_code == 404


def test_compliance_task_ownership_validation():
    headers_a = create_test_auth_headers()

    # A second, separate organization/user
    reg_b = client.post("/api/v1/auth/register", json={
        "organization_name": "Other Firm",
        "firm_type": "Proprietorship",
        "GSTIN": "27OTHRF1234A1Z0",
        "PAN": "OTHRF1234A",
        "address": "Delhi",
        "contact_email": "admin@otherfirm.com",
        "phone": "+91-9000000000",
        "admin_first_name": "Other",
        "admin_last_name": "Admin",
        "admin_email": "admin@otherfirm.com",
        "admin_password": "securepassword123"
    })
    headers_b = {"Authorization": f"Bearer {reg_b.json()['access_token']}"}

    # Org A creates a real client + compliance profile
    c_res = client.post("/api/v1/clients", json={"client_name": "Org A Client", "client_type": "Corporate"}, headers=headers_a)
    client_id_a = c_res.json()["id"]
    p_res = client.post("/api/v1/compliance/profile", json={
        "client_id": client_id_a, "compliance_type": "GST", "frequency": "MONTHLY", "due_day": 20
    }, headers=headers_a)
    profile_id_a = p_res.json()["id"]

    # Org B tries to create a manual task against Org A's client/profile - must be rejected
    task_res = client.post("/api/v1/compliance/task", json={
        "client_id": client_id_a,
        "profile_id": profile_id_a,
        "task_name": "Malicious cross-tenant task",
        "due_date": "2026-08-01T00:00:00",
    }, headers=headers_b)
    assert task_res.status_code == 404


def test_compliance_dashboard_due_date_buckets():
    headers = create_test_auth_headers()
    c_res = client.post("/api/v1/clients", json={"client_name": "Bucket Co", "client_type": "Corporate"}, headers=headers)
    client_id = c_res.json()["id"]

    # Creating a MONTHLY profile auto-generates 12 real recurring tasks
    # (see ComplianceService.generate_recurring_tasks) spread across the next
    # year - real, non-hardcoded due dates to bucket against.
    p_res = client.post("/api/v1/compliance/profile", json={
        "client_id": client_id,
        "compliance_type": "GST",
        "frequency": "MONTHLY",
        "due_day": 20,
    }, headers=headers)
    profile_id = p_res.json()["id"]

    # A handful of manual tasks with tightly controlled offsets guarantee
    # real, non-zero coverage of the overdue/today/week buckets regardless
    # of which day the suite happens to run on.
    now = datetime.utcnow()
    manual_offsets_hours = [-24, 2, 72]
    for i, h in enumerate(manual_offsets_hours):
        res = client.post("/api/v1/compliance/task", json={
            "client_id": client_id,
            "profile_id": profile_id,
            "task_name": f"Manual Bucket Task {i}",
            "due_date": (now + timedelta(hours=h)).isoformat(),
        }, headers=headers)
        assert res.status_code == 200

    # Pull every real task back out and independently recompute the expected
    # bucket counts from their live due_date values - not hardcoded numbers.
    cal_res = client.get("/api/v1/compliance/calendar", headers=headers)
    assert cal_res.status_code == 200
    all_tasks = [t for t in cal_res.json() if t["client_id"] == client_id]
    assert len(all_tasks) >= 12 + len(manual_offsets_hours)

    now2 = datetime.utcnow()
    today_start = datetime(now2.year, now2.month, now2.day)
    tomorrow_start = today_start + timedelta(days=1)
    week_end = today_start + timedelta(days=7 - now2.weekday())
    month_end = datetime(now2.year + 1, 1, 1) if now2.month == 12 else datetime(now2.year, now2.month + 1, 1)

    pending_dues = [datetime.fromisoformat(t["due_date"]) for t in all_tasks if t["status"] != "COMPLETED"]
    expected_overdue = sum(1 for d in pending_dues if d < now2)
    expected_today = sum(1 for d in pending_dues if now2 <= d < tomorrow_start)
    expected_week = sum(1 for d in pending_dues if now2 <= d < week_end)
    expected_month = sum(1 for d in pending_dues if now2 <= d < month_end)

    dash_res = client.get("/api/v1/compliance/dashboard", headers=headers)
    assert dash_res.status_code == 200
    dash = dash_res.json()

    assert dash["total_returns_overdue"] == expected_overdue
    assert dash["due_today"] == expected_today
    assert dash["due_this_week"] == expected_week
    assert dash["due_this_month"] == expected_month

    # Sanity: the manually crafted offsets guarantee non-trivial coverage.
    assert expected_overdue >= 1
    assert expected_today >= 1
    assert dash["due_today"] <= dash["due_this_week"] <= dash["due_this_month"]


def test_intelligence_rules_registry_endpoint():
    headers = create_test_auth_headers()
    res = client.get("/api/v1/intelligence/rules", headers=headers)
    assert res.status_code == 200
    rules = res.json()
    keys = {r["rule_key"] for r in rules}
    assert "COMPLIANCE_OVERDUE_TASK" in keys
    assert "TAX_MISSING_DEDUCTIONS" in keys
    not_yet = next(r for r in rules if r["rule_key"] == "TAX_MISSING_DEDUCTIONS")
    assert not_yet["status"] == "NOT_YET_SUPPORTED"
    assert not_yet["limitations"]


def test_intelligence_regenerate_and_dashboard_end_to_end():
    """Full API round-trip through the actual response_model boundary - this is the
    layer a pure service-level unit test can't exercise, and where a real field-name
    mismatch (RegenerateResponse.unchanged vs the engine's actual `refreshed` key)
    was caught during manual browser verification. Guards against a regression."""
    headers = create_test_auth_headers()
    c_res = client.post("/api/v1/clients", json={"client_name": "Intel API Co", "client_type": "Company"}, headers=headers)
    client_id = c_res.json()["id"]

    regen_res = client.post(f"/api/v1/intelligence/regenerate/{client_id}", headers=headers)
    assert regen_res.status_code == 200, regen_res.text
    regen = regen_res.json()
    assert regen["client_id"] == client_id
    assert regen["generated"] >= 1  # a brand-new client with no compliance profile and no documents

    dash_res = client.get("/api/v1/intelligence/dashboard", headers=headers)
    assert dash_res.status_code == 200
    dash = dash_res.json()
    assert dash["total_open"] >= 1
    matching = [s for s in dash["suggestions"] if s["client_id"] == client_id]
    assert any(s["rule_key"] == "COMPLIANCE_MISSING_PROFILE" for s in matching)

    # Client-scoped listing endpoint returns the same suggestions.
    client_suggestions_res = client.get(f"/api/v1/intelligence/clients/{client_id}", headers=headers)
    assert client_suggestions_res.status_code == 200
    assert len(client_suggestions_res.json()) >= 1


def test_intelligence_suggestion_status_lifecycle_via_api():
    headers = create_test_auth_headers()
    c_res = client.post("/api/v1/clients", json={"client_name": "Intel Lifecycle Co", "client_type": "Company"}, headers=headers)
    client_id = c_res.json()["id"]
    client.post(f"/api/v1/intelligence/regenerate/{client_id}", headers=headers)

    suggestions = client.get(f"/api/v1/intelligence/clients/{client_id}", headers=headers).json()
    suggestion_id = suggestions[0]["id"]

    # Cannot skip straight to RESOLVED from NEW.
    bad = client.put(f"/api/v1/intelligence/{suggestion_id}/status", json={"status": "RESOLVED"}, headers=headers)
    assert bad.status_code == 400

    ack = client.put(f"/api/v1/intelligence/{suggestion_id}/status", json={"status": "ACKNOWLEDGED"}, headers=headers)
    assert ack.status_code == 200
    assert ack.json()["status"] == "ACKNOWLEDGED"
    assert ack.json()["acknowledged_at"] is not None


def test_intelligence_regenerate_rejects_other_organizations_client():
    headers_a = create_test_auth_headers()
    c_res = client.post("/api/v1/clients", json={"client_name": "Org A Client", "client_type": "Company"}, headers=headers_a)
    client_id = c_res.json()["id"]

    reg_b = client.post("/api/v1/auth/register", json={
        "organization_name": "Other Intel Firm", "firm_type": "Partnership",
        "contact_email": "b@otherintel.com", "admin_first_name": "Org", "admin_last_name": "B",
        "admin_email": "b@otherintel.com", "admin_password": "otherpassword123",
    })
    token_b = reg_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    res = client.post(f"/api/v1/intelligence/regenerate/{client_id}", headers=headers_b)
    assert res.status_code == 404
