import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.models import (
    Organization, User, Client, RawDocument, ProcessedDocument,
    ComplianceSource, GovernmentSource, GovernmentUpdate,
    KnowledgeGraphNode, KnowledgeGraphEdge, Entity, EntityAlias, Citation
)
from app.services.graph import GraphService

# In-memory SQLite for testing
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
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)

def get_token_for(email: str):
    from jose import jwt
    from app.core.config import settings
    token_data = {"sub": email}
    return jwt.encode(token_data, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def setup_mock_org_and_users(db):
    org = Organization(id="org-a", organization_name="Firm A", firm_type="Partnership", contact_email="admin-a@firm.com")
    db.add(org)
    
    admin = User(
        id="user-admin-a",
        organization_id="org-a",
        email="admin-a@firm.com",
        hashed_password="fakehashpwd123",
        first_name="Admin",
        last_name="A",
        role="FIRM_ADMIN",
        is_active=True
    )
    db.add(admin)
    
    employee = User(
        id="user-emp-a",
        organization_id="org-a",
        email="emp-a@firm.com",
        hashed_password="fakehashpwd123",
        first_name="Employee",
        last_name="A",
        role="EMPLOYEE",
        is_active=True
    )
    db.add(employee)
    
    org_b = Organization(id="org-b", organization_name="Firm B", firm_type="Partnership", contact_email="admin-b@firm.com")
    db.add(org_b)
    
    admin_b = User(
        id="user-admin-b",
        organization_id="org-b",
        email="admin-b@firm.com",
        hashed_password="fakehashpwd123",
        first_name="Admin",
        last_name="B",
        role="FIRM_ADMIN",
        is_active=True
    )
    db.add(admin_b)
    
    db.commit()

# ==========================================
# 1. AUTHENTICATION & MULTI-TENANCY ISOLATION
# ==========================================
def test_auth_and_profile():
    # Test Register
    res = client.post("/api/v1/auth/register", json={
        "organization_name": "New Firm",
        "firm_type": "Partnership",
        "contact_email": "new@firm.com",
        "admin_first_name": "New",
        "admin_last_name": "Admin",
        "admin_email": "new@firm.com",
        "admin_password": "securepwd123"
    })
    assert res.status_code == 201
    assert "access_token" in res.json()
    
    # Test Login
    res_login = client.post("/api/v1/auth/login", json={
        "email": "new@firm.com",
        "password": "securepwd123"
    })
    assert res_login.status_code == 200
    token = res_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test Me
    res_me = client.get("/api/v1/auth/me", headers=headers)
    assert res_me.status_code == 200
    assert res_me.json()["email"] == "new@firm.com"
    
    # Test Profile update
    res_prof = client.put("/api/v1/organizations/profile", json={
        "organization_name": "Updated New Firm",
        "phone": "+91-8888888888"
    }, headers=headers)
    assert res_prof.status_code == 200
    assert res_prof.json()["organization_name"] == "Updated New Firm"

def test_rbac_and_tenant_isolation():
    db = TestingSessionLocal()
    setup_mock_org_and_users(db)
    db.close()
    
    token_admin_a = get_token_for("admin-a@firm.com")
    token_emp_a = get_token_for("emp-a@firm.com")
    token_admin_b = get_token_for("admin-b@firm.com")
    
    # Verify RBAC Profile update (Employee should be Forbidden)
    res_update_emp = client.put("/api/v1/organizations/profile", json={"organization_name": "Hacked"}, headers={"Authorization": f"Bearer {token_emp_a}"})
    assert res_update_emp.status_code == 403
    
    # Verify Admin A can create a client
    res_client_create = client.post("/api/v1/clients", json={
        "client_name": "Client of A",
        "client_type": "Corporate",
        "GSTIN": "27ABCDE1234A1Z1"
    }, headers={"Authorization": f"Bearer {token_admin_a}"})
    assert res_client_create.status_code == 201
    client_id = res_client_create.json()["id"]
    
    # Verify Admin B cannot retrieve Client of A (Tenant Isolation)
    res_get_b = client.get(f"/api/v1/clients/{client_id}", headers={"Authorization": f"Bearer {token_admin_b}"})
    assert res_get_b.status_code == 404
    
    # Verify Admin B lists zero clients (Tenant Isolation)
    res_list_b = client.get("/api/v1/clients", headers={"Authorization": f"Bearer {token_admin_b}"})
    assert len(res_list_b.json()) == 0

# ==========================================
# 2. CLIENTS CRUD & PAGINATION
# ==========================================
def test_clients_crud():
    db = TestingSessionLocal()
    setup_mock_org_and_users(db)
    db.close()
    
    token = get_token_for("admin-a@firm.com")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create
    res = client.post("/api/v1/clients", json={
        "client_name": "Tata Steel",
        "client_type": "Corporate",
        "PAN": "TATA1234S",
        "GSTIN": "27TATA1234S1Z9"
    }, headers=headers)
    assert res.status_code == 201
    client_id = res.json()["id"]
    
    # Retrieve
    res_get = client.get(f"/api/v1/clients/{client_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["client_name"] == "Tata Steel"
    
    # Update
    res_up = client.put(f"/api/v1/clients/{client_id}", json={
        "contact_person": "Ratan Tata"
    }, headers=headers)
    assert res_up.status_code == 200
    assert res_up.json()["contact_person"] == "Ratan Tata"
    
    # Pagination seeding
    for i in range(5):
        client.post("/api/v1/clients", json={
            "client_name": f"Bulk Client {i}",
            "client_type": "Individual"
        }, headers=headers)
        
    res_all = client.get("/api/v1/clients?limit=3&skip=2", headers=headers)
    assert len(res_all.json()) == 3

# ==========================================
# 3. DOCUMENTS, MAGIC BYTES & PIPELINE
# ==========================================
def test_documents_and_pipeline():
    db = TestingSessionLocal()
    setup_mock_org_and_users(db)
    db.close()
    
    token = get_token_for("admin-a@firm.com")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Upload valid PDF
    pdf_bytes = io.BytesIO(b"%PDF-1.4\n%mock pdf content")
    res_pdf = client.post("/api/v1/documents/upload",
        data={"category": "GST_RETURN"},
        files={"file": ("tax_return.pdf", pdf_bytes, "application/pdf")},
        headers=headers
    )
    assert res_pdf.status_code == 201
    doc_id = res_pdf.json()["id"]
    
    # Upload invalid file disguised as PDF (should fail signature check)
    bad_pdf = io.BytesIO(b"Fake content, not a PDF signature")
    res_bad = client.post("/api/v1/documents/upload",
        data={"category": "GST_RETURN"},
        files={"file": ("tax_return.pdf", bad_pdf, "application/pdf")},
        headers=headers
    )
    assert res_bad.status_code == 400
    
    # List and Retrieve
    res_list = client.get("/api/v1/documents", headers=headers)
    assert len(res_list.json()) == 1
    
    res_get = client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert res_get.status_code == 200

# ==========================================
# 4. COMPLIANCE & CONNECTORS
# ==========================================
def test_compliance_sources_and_connectors():
    db = TestingSessionLocal()
    setup_mock_org_and_users(db)
    
    # Seed GovernmentSource
    gov_src = GovernmentSource(
        source_name="IT Department",
        category="Income Tax",
        official_url="https://gov.in/it",
        requires_auth=False,
        sync_frequency="Daily",
        connector_status="RUNNING"
    )
    db.add(gov_src)
    db.commit()
    db.refresh(gov_src)
    gov_id = gov_src.id
    db.close()
    
    token = get_token_for("admin-a@firm.com")
    headers = {"Authorization": f"Bearer {token}"}
    
    # List official compliance sources
    res_sources = client.get("/api/v1/compliance/sources", headers=headers)
    assert res_sources.status_code == 200
    
    # List government connectors
    res_connectors = client.get("/api/v1/compliance/connectors", headers=headers)
    assert res_connectors.status_code == 200
    
    # Pause, Resume, and Sync
    res_pause = client.post(f"/api/v1/compliance/connectors/{gov_id}/pause", headers=headers)
    assert res_pause.status_code == 200
    
    res_resume = client.post(f"/api/v1/compliance/connectors/{gov_id}/resume", headers=headers)
    assert res_resume.status_code == 200
    
    res_sync = client.post(f"/api/v1/compliance/connectors/{gov_id}/sync", headers=headers)
    assert res_sync.status_code == 200

# ==========================================
# 5. KNOWLEDGE GRAPH & ENTITY MERGE
# ==========================================
def test_knowledge_graph_operations():
    db = TestingSessionLocal()
    setup_mock_org_and_users(db)
    
    # Seed Entities using GraphService.resolve_entity
    e1 = GraphService.resolve_entity(db, "org-a", "Company", "Reliance Industries Limited")
    e2 = GraphService.resolve_entity(db, "org-a", "Company", "RIL Pvt Ltd")
    
    e1_id = e1.id
    e2_id = e2.id
    db.close()
    
    token = get_token_for("admin-a@firm.com")
    headers = {"Authorization": f"Bearer {token}"}
    
    # List nodes and edges
    res_nodes = client.get("/api/v1/graph/nodes", headers=headers)
    assert res_nodes.status_code == 200
    
    # Search nodes
    res_search = client.get("/api/v1/graph/search?q=Reliance", headers=headers)
    assert res_search.status_code == 200
    
    # Create alias
    res_alias = client.post("/api/v1/graph/entities/alias", json={
        "entity_id": e1_id,
        "alias_text": "Reliance Ind",
        "alias_type": "Acro"
    }, headers=headers)
    assert res_alias.status_code == 200
    
    # Merge entities
    res_merge = client.post("/api/v1/graph/entities/merge", json={
        "primary_entity_id": e1_id,
        "secondary_entity_id": e2_id
    }, headers=headers)
    assert res_merge.status_code == 200

# ==========================================
# 6. CITATIONS, SEARCH & INTEGRATIONS
# ==========================================
def test_citations_search_and_integrations():
    db = TestingSessionLocal()
    setup_mock_org_and_users(db)
    db.close()
    
    token = get_token_for("admin-a@firm.com")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create Citation
    res_cite = client.post("/api/v1/citations", json={
        "source_type": "GST_NOTICE",
        "quote_text": "Tax amount short paid in July",
        "section_reference": "Section 74",
        "act_reference": "CGST Act"
    }, headers=headers)
    assert res_cite.status_code == 200
    citation_id = res_cite.json()["id"]
    
    # List & Search
    res_list = client.get("/api/v1/citations", headers=headers)
    assert len(res_list.json()) == 1
    
    res_search = client.get(f"/api/v1/citations/search?q=short", headers=headers)
    assert len(res_search.json()) == 1
    
    # Universal Search
    res_univ = client.get("/api/v1/search?q=Tax", headers=headers)
    assert res_univ.status_code == 200
    assert "citations" in res_univ.json()
    
    # AKKC Integrations
    res_connect = client.post("/api/v1/integrations/akkc/connect", json={
        "base_url": "https://akkc-mock.vercel.app/api",
        "api_key": "akkckey123"
    }, headers=headers)
    assert res_connect.status_code == 200
    
    res_status = client.get("/api/v1/integrations/akkc/status", headers=headers)
    assert res_status.json()["connected"] is True
    
    res_sync_c = client.post("/api/v1/integrations/akkc/sync/clients", headers=headers)
    assert res_sync_c.status_code == 200
    
    res_sync_t = client.post("/api/v1/integrations/akkc/sync/tasks", headers=headers)
    assert res_sync_t.status_code == 200
    
    res_sync_b = client.post("/api/v1/integrations/akkc/sync/bills", headers=headers)
    assert res_sync_b.status_code == 200

# ==========================================
# 7. OBSERVABILITY CONFIG ROUTE
# ==========================================
def test_observability_endpoints():
    db = TestingSessionLocal()
    setup_mock_org_and_users(db)
    db.close()
    
    token = get_token_for("admin-a@firm.com")
    headers = {"Authorization": f"Bearer {token}"}
    
    res_stats = client.get("/api/v1/observability/stats", headers=headers)
    assert res_stats.status_code == 200
    
    res_config = client.get("/api/v1/observability/config", headers=headers)
    assert res_config.status_code == 200
    assert "llm_provider" in res_config.json()
