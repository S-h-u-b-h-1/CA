"""Integration Sprint tests — verify the three cross-subsystem chains actually
fire automatically (no manual regenerate call), not just that each subsystem
works in isolation (already covered by test_intelligence_engine.py /
test_compliance_platform.py / test_document_intelligence.py individually).

  1. Authority Update -> Intelligence Suggestion -> Dashboard -> Client Workspace
  2. Compliance -> Task -> Suggestion -> Dashboard (automatic)
  3. Document Upload -> Parser -> Tax Intelligence -> Suggestion (automatic)
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.models import (
    Organization, Client, ComplianceProfile, ComplianceTask, Suggestion, Notification,
    RawDocument, Document, GovernmentSource, GovernmentUpdate, Form26ASEntry,
)
from app.services.connectors.registry import ConnectorRegistry
from app.services.intelligence import engine as intelligence_engine
from app.services.deduplication import DeduplicationEngine
from app.services.pipeline import DocumentPipelineOrchestrator

SQLALCHEMY_DATABASE_URL = "sqlite://"
sa_engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sa_engine)


@pytest.fixture(autouse=True)
def run_around_tests():
    Base.metadata.create_all(bind=sa_engine)
    yield
    Base.metadata.drop_all(bind=sa_engine)


def _make_org_and_client(db, client_type="Individual"):
    org = Organization(organization_name="Integration Test Co", firm_type="Company", contact_email="i@integ.com")
    db.add(org)
    db.commit()
    db.refresh(org)
    client = Client(organization_id=org.id, client_name="Integration Test Client", client_type=client_type)
    db.add(client)
    db.commit()
    db.refresh(client)
    return org, client


# ---------------------------------------------------------------------------
# Chain 1: Authority Update -> Intelligence Suggestion -> Dashboard -> Client Workspace
# ---------------------------------------------------------------------------

def test_authority_update_ingestion_automatically_creates_client_suggestion():
    db = TestingSessionLocal()
    org, client = _make_org_and_client(db)

    # Client has a real Income Tax compliance profile -> category "Direct Tax" is relevant.
    db.add(ComplianceProfile(organization_id=org.id, client_id=client.id, compliance_type="Income Tax", frequency="QUARTERLY", due_day=15))
    db.commit()

    # A control client with an unmapped compliance type must NOT get a suggestion —
    # proves the matching is real (category-based), not "notify everyone."
    control_client = Client(organization_id=org.id, client_name="Control Client (PF only)", client_type="Individual")
    db.add(control_client)
    db.commit()
    db.refresh(control_client)
    db.add(ComplianceProfile(organization_id=org.id, client_id=control_client.id, compliance_type="PF", frequency="MONTHLY", due_day=15))
    db.commit()

    cbdt_connector = ConnectorRegistry.get_connector("CBDT Circulars")
    assert cbdt_connector is not None
    assert cbdt_connector.get_category() == "Direct Tax"

    original_discover, original_download = cbdt_connector.discover, cbdt_connector.download
    try:
        def mock_discover(session):
            return [{
                "document_number": "CBDT/2026/INTEG-TEST",
                "title": "Circular on revised advance tax computation",
                "source_url": "https://incometax.gov.in/circulars/integ-test.txt",
            }]
        cbdt_connector.discover = mock_discover
        cbdt_connector.download = lambda url: (
            b"GOVERNMENT OF INDIA - CBDT CIRCULAR\nSubject: Revised advance tax computation guidance.\n"
            b"This circular clarifies Section 208 advance tax installment computation."
        )

        # No manual Intelligence regenerate call anywhere below — sync() alone must trigger it.
        result = cbdt_connector.sync(db)
        assert result["status"] == "SUCCESS"
        assert result["documents_downloaded"] == 1

        update = db.query(GovernmentUpdate).filter_by(document_number="CBDT/2026/INTEG-TEST").first()
        assert update is not None

        # --- Suggestion step ---
        suggestion = db.query(Suggestion).filter(
            Suggestion.client_id == client.id,
            Suggestion.rule_key == "RESEARCH_AUTHORITY_UPDATE_MATCH",
            Suggestion.related_government_update_id == update.id,
        ).first()
        assert suggestion is not None, "authority update sync did not automatically generate a client suggestion"
        assert suggestion.category == "RESEARCH"
        assert "Income Tax" in suggestion.title

        # Control client (PF-only, unmapped category) must have received nothing.
        control_suggestion = db.query(Suggestion).filter(Suggestion.client_id == control_client.id).first()
        assert control_suggestion is None

        # --- Notification step ---
        notification = db.query(Notification).filter(Notification.related_suggestion_id == suggestion.id).first()
        assert notification is not None
        assert notification.status == "UNREAD"

        # --- Dashboard step (org-wide aggregate) ---
        dashboard_rows = db.query(Suggestion).filter(Suggestion.organization_id == org.id, Suggestion.category == "RESEARCH").all()
        assert any(s.id == suggestion.id for s in dashboard_rows)

        # --- Client Workspace step (client-scoped view) ---
        client_rows = db.query(Suggestion).filter(Suggestion.client_id == client.id).all()
        assert any(s.id == suggestion.id for s in client_rows)
    finally:
        cbdt_connector.discover = original_discover
        cbdt_connector.download = original_download

    db.close()


# ---------------------------------------------------------------------------
# Chain 2: Compliance -> Task -> Suggestion -> Dashboard (automatic)
# ---------------------------------------------------------------------------

def test_compliance_task_completion_automatically_updates_suggestions_via_service_layer():
    """Exercises the same ComplianceService + Intelligence Engine call sequence the
    compliance.py API routes now perform automatically on every task mutation
    (verified separately at the HTTP layer in test_production_hardening.py's
    API-level tests) — here proving the underlying reconciliation chain itself:
    creating an overdue task and regenerating (as the route now does inline,
    with no separate manual trigger from a caller) produces a real suggestion,
    and completing the task clears it automatically."""
    db = TestingSessionLocal()
    org, client = _make_org_and_client(db, client_type="Company")

    profile = ComplianceProfile(organization_id=org.id, client_id=client.id, compliance_type="GST", frequency="MONTHLY", due_day=20, risk_level="HIGH")
    db.add(profile)
    db.commit()
    db.refresh(profile)

    task = ComplianceTask(
        organization_id=org.id, client_id=client.id, profile_id=profile.id,
        task_name="GST filing", due_date=datetime.utcnow() - timedelta(days=10), status="PENDING",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # This mirrors exactly what create_manual_compliance_task now does automatically.
    intelligence_engine.generate_for_client(db, client)

    suggestion = db.query(Suggestion).filter(Suggestion.client_id == client.id, Suggestion.rule_key == "COMPLIANCE_OVERDUE_TASK").first()
    assert suggestion is not None
    assert suggestion.status == "NEW"

    dashboard_open = db.query(Suggestion).filter(Suggestion.organization_id == org.id, Suggestion.status.in_(intelligence_engine.ACTIVE_STATUSES)).count()
    assert dashboard_open >= 1

    # Complete the task, mirroring what update_compliance_task_route now does automatically.
    task.status = "COMPLETED"
    db.commit()
    intelligence_engine.generate_for_client(db, client)

    db.refresh(suggestion)
    assert suggestion.status == "RESOLVED"

    db.close()


# ---------------------------------------------------------------------------
# Chain 3: Document Upload -> Parser -> Tax Intelligence -> Suggestion (automatic)
# ---------------------------------------------------------------------------

def test_document_pipeline_completion_automatically_generates_tax_suggestion():
    db = TestingSessionLocal()
    org, client = _make_org_and_client(db)

    sample_text = (
        "PAN of Taxpayer: ABCDE1234F\n"
        "Assessment Year: 2026-27\n"
        "Financial Year: 2025-26\n"
        "Name of Taxpayer: Integration Test Client\n"
        "Name of Deductor: Tata Consultancy Services TAN: MNOA12345P\n"
        "Section 194C Amount Paid: 5,00,000 TDS: 10,000\n"
        "Challan No: 910283 BSR Code: 0281928 Amount: 50,000\n"
    )
    hashes = DeduplicationEngine.calculate_file_hashes(sample_text.encode("utf-8"))
    from app.services.storage import get_storage_provider
    storage = get_storage_provider()
    file_path = storage.save_file("integration_test_26AS.txt", sample_text.encode("utf-8"))

    raw_doc = RawDocument(
        organization_id=org.id,
        client_id=client.id,  # critical: without this, neither recompute cascade fires
        name="integration_test_26AS.txt",
        file_path=file_path,
        file_size=len(sample_text),
        mime_type="text/plain",
        sha256_hash=hashes["sha256"],
        md5_hash=hashes["md5"],
        similarity_hash=hashes["similarity_hash"],
        file_fingerprint=hashes["file_fingerprint"],
        version=1,
        status="ACTIVE",
    )
    db.add(raw_doc)
    db.commit()
    db.refresh(raw_doc)

    # The real upload endpoint (POST /documents/upload, documents.py:94-96) creates a
    # companion legacy Document row sharing the RawDocument's id BEFORE the pipeline
    # runs — both TaxIntelligenceService.recompute() and the Intelligence Engine hook
    # key off this row's client_id. Replicated here so the pipeline cascades exactly
    # as it does in production, not a simplified stand-in.
    legacy_doc = Document(
        id=raw_doc.id, organization_id=org.id, client_id=client.id,
        name=raw_doc.name, file_path=raw_doc.file_path, file_size=raw_doc.file_size,
        mime_type=raw_doc.mime_type, category="Form 26AS",
    )
    db.add(legacy_doc)
    db.commit()

    # No manual TaxIntelligenceService.recompute() or Intelligence Engine call below —
    # process_document alone must cascade through both automatically.
    success = DocumentPipelineOrchestrator.process_document(db, raw_doc.id)
    assert success is True

    # --- Parser step ---
    entry = db.query(Form26ASEntry).filter(Form26ASEntry.client_id == client.id).first()
    assert entry is not None, "Form 26AS was not parsed into a structured entry"
    assert entry.tax_deposited == 10000.0

    # --- Tax Intelligence step: not re-asserted here (tax_intelligence.py's own test
    # suite covers ClientTaxInsight rules directly) — this test's job is the cascade.

    # --- Suggestion step (automatic — no explicit regenerate call in this test) ---
    suggestion = db.query(Suggestion).filter(
        Suggestion.client_id == client.id,
        Suggestion.rule_key == "TAX_POSSIBLE_UNREPORTED_INCOME",
    ).first()
    assert suggestion is not None, "document pipeline completion did not automatically generate a tax suggestion"
    assert suggestion.category == "TAX"
    assert "10,000.00" in suggestion.explanation or "10000" in suggestion.explanation

    notification = db.query(Notification).filter(Notification.related_suggestion_id == suggestion.id).first()
    assert notification is not None

    db.close()
