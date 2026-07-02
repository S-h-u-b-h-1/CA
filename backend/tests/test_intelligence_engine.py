import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta

from app.core.database import Base
from app.models.models import (
    Organization, Client, ComplianceProfile, ComplianceTask, Suggestion,
    Form26ASEntry, AISEntry, TISEntry, Document,
    GovernmentSource, GovernmentUpdate,
)
from app.services.intelligence import engine
from app.services.intelligence.core import EvidenceItem, derive_confidence
from app.services.intelligence import rules_tax, rules_compliance, rules_documents, rules_authority_updates
from app.services.intelligence.registry import list_rules

SQLALCHEMY_DATABASE_URL = "sqlite://"
sa_engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sa_engine)


@pytest.fixture(autouse=True)
def run_around_tests():
    Base.metadata.create_all(bind=sa_engine)
    yield
    Base.metadata.drop_all(bind=sa_engine)


def _make_org_and_client(db):
    org = Organization(organization_name="Intel Test Co", firm_type="Company", contact_email="i@test.com")
    db.add(org)
    db.commit()
    db.refresh(org)
    client = Client(organization_id=org.id, client_name="Intel Test Client", client_type="Individual")
    db.add(client)
    db.commit()
    db.refresh(client)
    return org, client


# ---------------------------------------------------------------------------
# Confidence derivation (pure logic, no DB)
# ---------------------------------------------------------------------------

def test_confidence_derivation_two_sources_is_high():
    ev = [EvidenceItem("FORM_26AS", "a"), EvidenceItem("AIS", "b")]
    confidence, reason = derive_confidence(ev)
    assert confidence == "HIGH"
    assert "2 independent data sources" in reason


def test_confidence_derivation_one_source_is_medium():
    ev = [EvidenceItem("AIS", "a"), EvidenceItem("AIS", "b")]  # same type twice
    confidence, reason = derive_confidence(ev)
    assert confidence == "MEDIUM"


def test_confidence_derivation_no_evidence_is_low():
    confidence, reason = derive_confidence([])
    assert confidence == "LOW"


# ---------------------------------------------------------------------------
# Tax rules
# ---------------------------------------------------------------------------

def test_tax_pan_mismatch_rule_fires_on_real_conflicting_entries():
    db = TestingSessionLocal()
    org, client = _make_org_and_client(db)

    db.add(Form26ASEntry(organization_id=org.id, client_id=client.id, document_id="doc1",
                          pan="AAAAA1111A", assessment_year="2025-26", tax_deposited=1000.0))
    db.add(AISEntry(organization_id=org.id, client_id=client.id, document_id="doc2",
                     pan="BBBBB2222B", assessment_year="2025-26", information_category="Salary", reported_value=50000.0))
    db.commit()

    candidates = rules_tax.evaluate(db, client)
    pan_mismatches = [c for c in candidates if c.rule_key == "TAX_PAN_MISMATCH"]
    assert len(pan_mismatches) == 1
    assert pan_mismatches[0].severity == "CRITICAL"
    confidence, _ = derive_confidence(pan_mismatches[0].evidence)
    assert confidence == "HIGH"  # two distinct source types: FORM_26AS + AIS
    db.close()


def test_tax_rules_silent_when_pans_agree():
    db = TestingSessionLocal()
    org, client = _make_org_and_client(db)
    db.add(Form26ASEntry(organization_id=org.id, client_id=client.id, document_id="doc1",
                          pan="AAAAA1111A", assessment_year="2025-26", tax_deposited=1000.0))
    db.add(AISEntry(organization_id=org.id, client_id=client.id, document_id="doc2",
                     pan="AAAAA1111A", assessment_year="2025-26", information_category="Salary", reported_value=50000.0))
    db.commit()

    candidates = rules_tax.evaluate(db, client)
    assert not any(c.rule_key == "TAX_PAN_MISMATCH" for c in candidates)
    db.close()


def test_tax_refund_available_rule_reproducible():
    db = TestingSessionLocal()
    org, client = _make_org_and_client(db)
    db.add(Form26ASEntry(organization_id=org.id, client_id=client.id, document_id="doc1",
                          pan="AAAAA1111A", assessment_year="2025-26", tax_deposited=5000.0, refund=1200.0))
    db.commit()

    run1 = rules_tax.evaluate(db, client)
    run2 = rules_tax.evaluate(db, client)
    refund1 = [c for c in run1 if c.rule_key == "TAX_REFUND_AVAILABLE"]
    refund2 = [c for c in run2 if c.rule_key == "TAX_REFUND_AVAILABLE"]
    assert len(refund1) == 1 and len(refund2) == 1
    assert refund1[0].dedup_suffix == refund2[0].dedup_suffix  # same inputs -> same identity, every time
    db.close()


def test_tax_excess_tds_rule():
    db = TestingSessionLocal()
    org, client = _make_org_and_client(db)
    db.add(Form26ASEntry(organization_id=org.id, client_id=client.id, document_id="doc1",
                          assessment_year="2025-26", tax_deposited=90000.0))
    db.add(AISEntry(organization_id=org.id, client_id=client.id, document_id="doc2",
                     assessment_year="2025-26", information_category="Salary", reported_value=10000.0))
    db.commit()

    candidates = rules_tax.evaluate(db, client)
    excess = [c for c in candidates if c.rule_key == "TAX_EXCESS_TDS"]
    assert len(excess) == 1
    assert "90,000" in excess[0].explanation or "90000" in excess[0].explanation
    db.close()


# ---------------------------------------------------------------------------
# Compliance rules
# ---------------------------------------------------------------------------

def test_compliance_missing_profile_rule():
    db = TestingSessionLocal()
    org, client = _make_org_and_client(db)
    candidates = rules_compliance.evaluate(db, client)
    assert len(candidates) == 1
    assert candidates[0].rule_key == "COMPLIANCE_MISSING_PROFILE"
    assert candidates[0].severity == "HIGH"
    db.close()


def test_compliance_overdue_task_escalates_past_30_days():
    db = TestingSessionLocal()
    org, client = _make_org_and_client(db)
    profile = ComplianceProfile(organization_id=org.id, client_id=client.id, compliance_type="GST", frequency="MONTHLY", due_day=20)
    db.add(profile)
    db.commit()
    db.refresh(profile)

    recent_overdue = ComplianceTask(organization_id=org.id, client_id=client.id, profile_id=profile.id,
                                     task_name="File GST - recent", due_date=datetime.utcnow() - timedelta(days=5), status="PENDING")
    old_overdue = ComplianceTask(organization_id=org.id, client_id=client.id, profile_id=profile.id,
                                  task_name="File GST - old", due_date=datetime.utcnow() - timedelta(days=45), status="PENDING")
    db.add_all([recent_overdue, old_overdue])
    db.commit()

    candidates = rules_compliance.evaluate(db, client)
    overdue = {c.dedup_suffix: c for c in candidates if c.rule_key == "COMPLIANCE_OVERDUE_TASK"}
    assert overdue[recent_overdue.id].severity == "HIGH"
    assert overdue[old_overdue.id].severity == "CRITICAL"
    db.close()


def test_compliance_high_risk_client_requires_both_risk_and_multiple_overdue():
    db = TestingSessionLocal()
    org, client = _make_org_and_client(db)
    profile = ComplianceProfile(organization_id=org.id, client_id=client.id, compliance_type="TDS",
                                 frequency="MONTHLY", due_day=7, risk_level="HIGH")
    db.add(profile)
    db.commit()
    db.refresh(profile)

    for i in range(2):
        db.add(ComplianceTask(organization_id=org.id, client_id=client.id, profile_id=profile.id,
                               task_name=f"Task {i}", due_date=datetime.utcnow() - timedelta(days=10 + i), status="PENDING"))
    db.commit()

    candidates = rules_compliance.evaluate(db, client)
    assert any(c.rule_key == "COMPLIANCE_HIGH_RISK_CLIENT" for c in candidates)
    db.close()


def test_compliance_high_risk_does_not_fire_with_only_one_overdue():
    db = TestingSessionLocal()
    org, client = _make_org_and_client(db)
    profile = ComplianceProfile(organization_id=org.id, client_id=client.id, compliance_type="TDS",
                                 frequency="MONTHLY", due_day=7, risk_level="HIGH")
    db.add(profile)
    db.commit()
    db.refresh(profile)
    db.add(ComplianceTask(organization_id=org.id, client_id=client.id, profile_id=profile.id,
                           task_name="Task", due_date=datetime.utcnow() - timedelta(days=10), status="PENDING"))
    db.commit()

    candidates = rules_compliance.evaluate(db, client)
    assert not any(c.rule_key == "COMPLIANCE_HIGH_RISK_CLIENT" for c in candidates)
    db.close()


# ---------------------------------------------------------------------------
# Document rules
# ---------------------------------------------------------------------------

def test_document_missing_bank_statement_flagged_for_bare_client():
    db = TestingSessionLocal()
    org, client = _make_org_and_client(db)
    candidates = rules_documents.evaluate(db, client)
    assert any(c.dedup_suffix == "Bank Statement" for c in candidates)
    db.close()


def test_document_missing_not_flagged_once_uploaded():
    db = TestingSessionLocal()
    org, client = _make_org_and_client(db)
    db.add(Document(organization_id=org.id, client_id=client.id, name="stmt.pdf", file_path="/x", file_size=1,
                     mime_type="application/pdf", category="Bank Statement", classification="Bank Statement"))
    db.commit()

    candidates = rules_documents.evaluate(db, client)
    assert not any(c.dedup_suffix == "Bank Statement" for c in candidates)
    db.close()


def test_document_gst_return_only_expected_when_gst_profile_exists():
    db = TestingSessionLocal()
    org, client = _make_org_and_client(db)
    candidates_without_profile = rules_documents.evaluate(db, client)
    assert not any(c.dedup_suffix == "GSTR-3B" for c in candidates_without_profile)

    db.add(ComplianceProfile(organization_id=org.id, client_id=client.id, compliance_type="GST", frequency="MONTHLY", due_day=20))
    db.commit()

    candidates_with_profile = rules_documents.evaluate(db, client)
    assert any(c.dedup_suffix == "GSTR-3B" for c in candidates_with_profile)
    db.close()


# ---------------------------------------------------------------------------
# Authority update matching
# ---------------------------------------------------------------------------

def test_authority_update_matches_gst_profile_with_medium_confidence():
    db = TestingSessionLocal()
    org, client = _make_org_and_client(db)
    db.add(ComplianceProfile(organization_id=org.id, client_id=client.id, compliance_type="GST", frequency="MONTHLY", due_day=20))
    source = GovernmentSource(source_name="GST Council", category="Indirect Tax", official_url="https://gst.gov.in")
    db.add(source)
    db.commit()
    db.refresh(source)
    db.add(GovernmentUpdate(source_id=source.id, title="New GSTR-3B validation rules", issuing_authority="GST Council",
                             issue_date=datetime.utcnow() - timedelta(days=2)))
    db.commit()

    candidates = rules_authority_updates.evaluate(db, client)
    assert len(candidates) == 1
    assert candidates[0].severity == "HIGH"  # issued within 7 days
    assert candidates[0].confidence_override == "MEDIUM"  # always pinned, never auto-escalated to HIGH
    db.close()


def test_authority_update_does_not_match_unmapped_pf_type():
    db = TestingSessionLocal()
    org, client = _make_org_and_client(db)
    db.add(ComplianceProfile(organization_id=org.id, client_id=client.id, compliance_type="PF", frequency="MONTHLY", due_day=15))
    source = GovernmentSource(source_name="RBI", category="Banking Regulation", official_url="https://rbi.org.in")
    db.add(source)
    db.commit()
    db.refresh(source)
    db.add(GovernmentUpdate(source_id=source.id, title="Unrelated banking circular", issuing_authority="RBI",
                             issue_date=datetime.utcnow() - timedelta(days=1)))
    db.commit()

    candidates = rules_authority_updates.evaluate(db, client)
    assert candidates == []  # PF has no real connector category to match against — must stay silent, not guess
    db.close()


def test_authority_update_ignores_stale_updates_outside_lookback_window():
    db = TestingSessionLocal()
    org, client = _make_org_and_client(db)
    db.add(ComplianceProfile(organization_id=org.id, client_id=client.id, compliance_type="GST", frequency="MONTHLY", due_day=20))
    source = GovernmentSource(source_name="GST Council", category="Indirect Tax", official_url="https://gst.gov.in")
    db.add(source)
    db.commit()
    db.refresh(source)
    db.add(GovernmentUpdate(source_id=source.id, title="Old GST update", issuing_authority="GST Council",
                             issue_date=datetime.utcnow() - timedelta(days=90)))
    db.commit()

    candidates = rules_authority_updates.evaluate(db, client)
    assert candidates == []
    db.close()


# ---------------------------------------------------------------------------
# Engine reconciliation + lifecycle
# ---------------------------------------------------------------------------

def test_engine_generate_creates_and_regeneration_is_idempotent():
    db = TestingSessionLocal()
    org, client = _make_org_and_client(db)

    result1 = engine.generate_for_client(db, client)
    assert result1["generated"] >= 1  # at least COMPLIANCE_MISSING_PROFILE + DOCUMENT_MISSING x N

    count_after_first = db.query(Suggestion).filter(Suggestion.client_id == client.id).count()
    result2 = engine.generate_for_client(db, client)
    count_after_second = db.query(Suggestion).filter(Suggestion.client_id == client.id).count()

    assert result2["generated"] == 0  # nothing new — same conditions
    assert count_after_first == count_after_second  # no duplicate rows created
    db.close()


def test_engine_auto_resolves_when_condition_clears():
    db = TestingSessionLocal()
    org, client = _make_org_and_client(db)
    profile = ComplianceProfile(organization_id=org.id, client_id=client.id, compliance_type="TDS", frequency="MONTHLY", due_day=7)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    task = ComplianceTask(organization_id=org.id, client_id=client.id, profile_id=profile.id,
                           task_name="File TDS", due_date=datetime.utcnow() - timedelta(days=3), status="PENDING")
    db.add(task)
    db.commit()
    db.refresh(task)

    engine.generate_for_client(db, client)
    overdue_suggestion = db.query(Suggestion).filter(Suggestion.rule_key == "COMPLIANCE_OVERDUE_TASK", Suggestion.client_id == client.id).first()
    assert overdue_suggestion is not None
    assert overdue_suggestion.status == "NEW"

    # Condition clears: task gets completed
    task.status = "COMPLETED"
    db.commit()

    result = engine.generate_for_client(db, client)
    assert result["resolved"] >= 1
    db.refresh(overdue_suggestion)
    assert overdue_suggestion.status == "RESOLVED"
    assert overdue_suggestion.resolved_at is not None
    db.close()


def test_engine_does_not_resurrect_dismissed_suggestions():
    db = TestingSessionLocal()
    org, client = _make_org_and_client(db)
    # Missing-profile condition is stable across regenerations.
    engine.generate_for_client(db, client)
    suggestion = db.query(Suggestion).filter(Suggestion.rule_key == "COMPLIANCE_MISSING_PROFILE", Suggestion.client_id == client.id).first()
    assert suggestion is not None

    from app.models.models import User
    user = User(organization_id=org.id, email="ca@test.com", hashed_password="x", first_name="A", last_name="B", role="FIRM_ADMIN")
    db.add(user)
    db.commit()
    db.refresh(user)

    engine.transition_status(db, suggestion, "DISMISSED", user.id, reason="Not applicable to this client")
    db.refresh(suggestion)
    assert suggestion.status == "DISMISSED"

    # Condition still holds (still no profile) — regeneration must NOT resurrect it.
    engine.generate_for_client(db, client)
    still_dismissed_count = db.query(Suggestion).filter(
        Suggestion.rule_key == "COMPLIANCE_MISSING_PROFILE", Suggestion.client_id == client.id
    ).count()
    assert still_dismissed_count == 1  # exactly the one dismissed row, no fresh duplicate
    db.refresh(suggestion)
    assert suggestion.status == "DISMISSED"
    db.close()


def test_lifecycle_transitions_enforce_strict_order():
    db = TestingSessionLocal()
    org, client = _make_org_and_client(db)
    engine.generate_for_client(db, client)
    suggestion = db.query(Suggestion).filter(Suggestion.client_id == client.id).first()

    from app.models.models import User
    user = User(organization_id=org.id, email="ca2@test.com", hashed_password="x", first_name="A", last_name="B", role="FIRM_ADMIN")
    db.add(user)
    db.commit()
    db.refresh(user)

    # Cannot skip straight from NEW to RESOLVED.
    with pytest.raises(ValueError):
        engine.transition_status(db, suggestion, "RESOLVED", user.id)

    engine.transition_status(db, suggestion, "ACKNOWLEDGED", user.id)
    assert suggestion.status == "ACKNOWLEDGED"
    assert suggestion.acknowledged_at is not None

    engine.transition_status(db, suggestion, "IN_PROGRESS", user.id)
    assert suggestion.in_progress_at is not None

    engine.transition_status(db, suggestion, "RESOLVED", user.id)
    assert suggestion.resolved_at is not None

    # Terminal state — no further transitions allowed.
    with pytest.raises(ValueError):
        engine.transition_status(db, suggestion, "DISMISSED", user.id)
    db.close()


def test_status_change_is_audited():
    db = TestingSessionLocal()
    org, client = _make_org_and_client(db)
    engine.generate_for_client(db, client)
    suggestion = db.query(Suggestion).filter(Suggestion.client_id == client.id).first()

    from app.models.models import User, AuditLog
    user = User(organization_id=org.id, email="ca3@test.com", hashed_password="x", first_name="A", last_name="B", role="FIRM_ADMIN")
    db.add(user)
    db.commit()
    db.refresh(user)

    engine.transition_status(db, suggestion, "ACKNOWLEDGED", user.id, reason="Reviewing now")
    audit_rows = db.query(AuditLog).filter(AuditLog.entity_type == "Suggestion", AuditLog.entity_id == suggestion.id).all()
    assert len(audit_rows) == 1
    assert "NEW -> ACKNOWLEDGED" in audit_rows[0].details
    assert "Reviewing now" in audit_rows[0].details
    db.close()


# ---------------------------------------------------------------------------
# Registry documents limitations honestly
# ---------------------------------------------------------------------------

def test_registry_documents_not_yet_supported_rules_with_limitations():
    rules = list_rules()
    not_yet = {r["rule_key"]: r for r in rules if r["status"] == "NOT_YET_SUPPORTED"}
    assert "TAX_MISSING_DEDUCTIONS" in not_yet
    assert "DOCUMENT_EXPIRED" in not_yet
    assert all(r.get("limitations") for r in not_yet.values())

    active_keys = {r["rule_key"] for r in rules if r["status"] == "ACTIVE"}
    assert "COMPLIANCE_OVERDUE_TASK" in active_keys
    assert "RESEARCH_AUTHORITY_UPDATE_MATCH" in active_keys
