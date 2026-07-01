import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.models import Organization, User, Client, Document, ComplianceSource
from app.core.security import hash_password

# Setup SQLite in-memory test database
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override database dependency
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
    # Setup: Create tables
    Base.metadata.create_all(bind=engine)
    # Seed compliance sources for test environment
    db = TestingSessionLocal()
    from app.core.seeds import seed_compliance_sources
    seed_compliance_sources(db)
    db.close()
    
    yield
    
    # Teardown: Drop tables
    Base.metadata.drop_all(bind=engine)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_auth_registration_and_login():
    # Register Organization & Admin
    reg_payload = {
        "organization_name": "Goenka & Associates",
        "firm_type": "Partnership",
        "GSTIN": "27GOENK1234A1Z0",
        "PAN": "GOENK1234A",
        "address": "Nariman Point, Mumbai",
        "contact_email": "admin@goenkaca.com",
        "phone": "+91-9876543210",
        "admin_first_name": "Anil",
        "admin_last_name": "Goenka",
        "admin_email": "anil@goenkaca.com",
        "admin_password": "securepassword123"
    }
    
    reg_response = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_response.status_code == 201
    reg_data = reg_response.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == "anil@goenkaca.com"
    assert reg_data["user"]["role"] == "FIRM_ADMIN"
    
    # Log in
    login_payload = {
        "email": "anil@goenkaca.com",
        "password": "securepassword123"
    }
    login_response = client.post("/api/v1/auth/login", json=login_payload)
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert "access_token" in login_data
    
    # Get Profile Profile
    headers = {"Authorization": f"Bearer {login_data['access_token']}"}
    me_response = client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "anil@goenkaca.com"


def test_multi_tenancy_isolation():
    # 1. Register Organization A
    org_a = client.post("/api/v1/auth/register", json={
        "organization_name": "Firm A", "firm_type": "LLP", "contact_email": "admin@firma.com",
        "admin_first_name": "A", "admin_last_name": "User", "admin_email": "admin@firma.com", "admin_password": "pwd"
    }).json()
    
    # 2. Register Organization B
    org_b = client.post("/api/v1/auth/register", json={
        "organization_name": "Firm B", "firm_type": "LLP", "contact_email": "admin@firmb.com",
        "admin_first_name": "B", "admin_last_name": "User", "admin_email": "admin@firmb.com", "admin_password": "pwd"
    }).json()

    headers_a = {"Authorization": f"Bearer {org_a['access_token']}"}
    headers_b = {"Authorization": f"Bearer {org_b['access_token']}"}

    # 3. Create client under Org A
    client_a = client.post("/api/v1/clients", headers=headers_a, json={
        "client_name": "Client of A",
        "client_type": "Individual"
    }).json()

    # 4. List clients as Org B - should be empty!
    clients_of_b = client.get("/api/v1/clients", headers=headers_b).json()
    assert len(clients_of_b) == 0

    # 5. Access Org A's client ID directly as Org B - should return 404
    direct_fetch = client.get(f"/api/v1/clients/{client_a['id']}", headers=headers_b)
    assert direct_fetch.status_code == 404


def test_client_crud():
    # Register and login
    user_data = client.post("/api/v1/auth/register", json={
        "organization_name": "CA Firm", "firm_type": "Individual", "contact_email": "test@ca.com",
        "admin_first_name": "Test", "admin_last_name": "Admin", "admin_email": "test@ca.com", "admin_password": "pwd"
    }).json()
    headers = {"Authorization": f"Bearer {user_data['access_token']}"}

    # Create
    new_client = client.post("/api/v1/clients", headers=headers, json={
        "client_name": "Ram Prasad HUF",
        "client_type": "HUF",
        "PAN": "RAMP1234H"
    }).json()
    assert new_client["client_name"] == "Ram Prasad HUF"

    # List
    client_list = client.get("/api/v1/clients", headers=headers).json()
    assert len(client_list) == 1

    # Update
    updated = client.put(f"/api/v1/clients/{new_client['id']}", headers=headers, json={
        "contact_phone": "9999888877"
    }).json()
    assert updated["contact_phone"] == "9999888877"

    # Delete
    delete_res = client.delete(f"/api/v1/clients/{new_client['id']}", headers=headers)
    assert delete_res.status_code == 204

    # Verify 404 on fetch
    fetch_deleted = client.get(f"/api/v1/clients/{new_client['id']}", headers=headers)
    assert fetch_deleted.status_code == 404


def test_compliance_sources():
    user_data = client.post("/api/v1/auth/register", json={
        "organization_name": "CA Firm", "firm_type": "Individual", "contact_email": "test@ca.com",
        "admin_first_name": "Test", "admin_last_name": "Admin", "admin_email": "test@ca.com", "admin_password": "pwd"
    }).json()
    headers = {"Authorization": f"Bearer {user_data['access_token']}"}

    sources = client.get("/api/v1/compliance/sources", headers=headers).json()
    # Should contain seeded compliance registry sources
    assert len(sources) > 0
    assert any(s["source_name"] == "Income Tax e-Filing API" for s in sources)


def test_akkc_integration_mocks():
    user_data = client.post("/api/v1/auth/register", json={
        "organization_name": "CA Firm", "firm_type": "Individual", "contact_email": "test@ca.com",
        "admin_first_name": "Test", "admin_last_name": "Admin", "admin_email": "test@ca.com", "admin_password": "pwd"
    }).json()
    headers = {"Authorization": f"Bearer {user_data['access_token']}"}

    # Verify mock connect
    connect_payload = {
        "api_key": "akkc-test-api-key",
        "base_url": "https://akkc-eight.vercel.app/api"
    }
    conn_res = client.post("/api/v1/integrations/akkc/connect", headers=headers, json=connect_payload)
    assert conn_res.status_code == 200
    assert conn_res.json()["connected"] is True

    # Verify status
    status_res = client.get("/api/v1/integrations/akkc/status", headers=headers).json()
    assert status_res["connected"] is True
    assert status_res["base_url"] == "https://akkc-eight.vercel.app/api"

    # Verify sync clients
    sync_clients = client.post("/api/v1/integrations/akkc/sync/clients", headers=headers)
    assert sync_clients.status_code == 200
    assert sync_clients.json()["status"] == "success"
    assert sync_clients.json()["synced_count"] > 0
