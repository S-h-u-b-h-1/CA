import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime

from app.core.database import Base
from app.models.models import (
    Organization, User, GovernmentSource, GovernmentUpdate, GovernmentUpdateVersion, ConnectorSyncLog,
    Client, ComplianceProfile, ComplianceTask
)
from app.services.connectors.registry import ConnectorRegistry
from app.services.scheduler import ConnectorScheduler
from app.services.versioning import VersioningEngine
from app.services.compliance_service import ComplianceService


# Setup SQLite in-memory test database
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def run_around_tests():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_connector_registry_and_initial_sources():
    """Verify that all 18 connectors are successfully registered"""
    all_connectors = ConnectorRegistry.list_all()
    assert len(all_connectors) == 18
    
    cbdt = ConnectorRegistry.get_connector("CBDT Circulars")
    assert cbdt is not None
    assert cbdt.get_authority() == "Central Board of Direct Taxes (CBDT)"
    assert cbdt.get_category() == "Direct Tax"


def test_versioning_diff_engine():
    """Verify paragraph-level comparisons and section alterations detection"""
    old_text = "Paragraph One: Original directive.\n\nParagraph Two: Rules on Section 143."
    new_text = "Paragraph One: Original directive.\n\nParagraph Two: Rules on Section 143.\n\nParagraph Three: New Section 194Q details."
    
    diff = VersioningEngine.compare_texts(old_text, new_text)
    
    assert len(diff["added_paragraphs"]) == 1
    assert "Paragraph Three" in diff["added_paragraphs"][0]
    assert len(diff["removed_paragraphs"]) == 0
    assert "194q" in [s.lower() for s in diff["changed_sections"]["added_sections"]]


def test_scheduler_state_management():
    """Verify scheduler pausing, resuming, and initialization"""
    db = TestingSessionLocal()
    
    # Pre-seed GovernmentSource
    src = GovernmentSource(
        source_name="CBDT Circulars",
        category="Direct Tax",
        official_url="https://cbdt.gov.in",
        requires_auth=False,
        sync_frequency="DAILY",
        connector_status="RUNNING"
    )
    db.add(src)
    db.commit()

    # Initialize schedules
    ConnectorScheduler.initialize_schedules(db)
    schedules = ConnectorScheduler.get_schedules()
    assert len(schedules) == 18
    
    cbdt_sched = next(s for s in schedules if s["connector_name"] == "CBDT Circulars")
    assert cbdt_sched["status"] == "RUNNING"

    # Pause schedule
    success = ConnectorScheduler.pause_schedule("CBDT Circulars", db)
    assert success is True
    assert cbdt_sched["status"] == "PAUSED"
    
    # Refresh and assert DB
    db.refresh(src)
    assert src.connector_status == "PAUSED"

    # Resume schedule
    success = ConnectorScheduler.resume_schedule("CBDT Circulars", db)
    assert success is True
    assert cbdt_sched["status"] == "RUNNING"
    
    db.refresh(src)
    assert src.connector_status == "RUNNING"

    db.close()


def test_connector_sync_and_versioning_lifecycle():
    """Verify that running sync twice with changes triggers new versions creation.

    Uses the e-Gazette connector (still a BaseMockConnector placeholder - out of
    scope for the real-data connector work) purely to exercise the generic
    sync/versioning mechanics via monkeypatched discover/download. CBIC/MCA were
    deliberately switched to an honest "no real source" connector that reports
    health_check() == DOWN, so they can no longer serve as a stand-in "always
    succeeds" mock for this kind of test.
    """
    db = TestingSessionLocal()

    # 1. Initialize connector
    egazette_connector = ConnectorRegistry.get_connector("e-Gazette")
    assert egazette_connector is not None

    # First sync run
    result1 = egazette_connector.sync(db)
    assert result1["status"] == "SUCCESS"
    assert result1["documents_downloaded"] == 1

    # Verify document and initial version created
    doc = db.query(GovernmentUpdate).filter_by(document_number="Gazette No. DL-33/2026").first()
    assert doc is not None
    assert doc.version == 1

    v1_log = db.query(GovernmentUpdateVersion).filter_by(government_update_id=doc.id, version_number=1).first()
    assert v1_log is not None

    # 2. Modify discover outputs to simulate a revision/new version of the same document number
    original_discover = egazette_connector.discover

    try:
        # Mock discover to return the same document number but we will mock downloading different text content
        def mock_discover(session):
            return [{
                "document_number": "Gazette No. DL-33/2026",
                "title": "Notification of the Insolvency Code Amendment Act (REVISED)",
                "source_url": "https://egazette.nic.in/publications/Gazette_DL_33_2026_revised.txt"
            }]
        egazette_connector.discover = mock_discover

        # Override download method temporarily to return different text for the revised url
        original_download = egazette_connector.download
        def mock_download(url):
            # Matches BaseMockConnector.download()'s exact template (used by the
            # unmocked first sync) plus one genuinely new paragraph, so the diff
            # engine detects only the intended addition.
            return (
                "GOVERNMENT OF INDIA - OFFICIAL NOTIFICATION PORTAL\n"
                f"Source Authority: {egazette_connector.get_authority()}\n"
                f"Category: {egazette_connector.get_category()}\n"
                "Ingestion URL: " + url + "\n\n"
                "Subject: Official directive guidelines for compliance.\n"
                "Pursuant to the powers conferred by Section 143 and Section 148 of the Income-tax Act, 1961, "
                "and Rule 12 of the GST Rules, the governing body hereby clarifies the following:\n\n"
                "1. Paragraph One: Compliance dates are extended for the respective filing assessment cycle.\n"
                "2. Paragraph Two: All filings must include validated GSTIN and PAN identifiers.\n"
                "3. Paragraph Three: Failure to reconcile records under Section 119 will trigger interest liabilities.\n\n"
                "4. Paragraph Four: New amendment under Section 154 introduced."
            ).encode("utf-8")
        egazette_connector.download = mock_download

        # Run Second Sync
        result2 = egazette_connector.sync(db)
        assert result2["status"] == "SUCCESS"
        assert result2["documents_downloaded"] == 1

        # Check version updated
        db.refresh(doc)
        assert doc.version == 2

        # Check version 2 diff log
        v2_log = db.query(GovernmentUpdateVersion).filter_by(government_update_id=doc.id, version_number=2).first()
        assert v2_log is not None
        assert len(v2_log.added_paragraphs) == 2
        assert any("Paragraph Four" in p for p in v2_log.added_paragraphs)
        assert "154" in v2_log.changed_sections["added_sections"]

    finally:
        # Restore mock overrides
        egazette_connector.discover = original_discover
        egazette_connector.download = original_download

    db.close()


def test_quarterly_task_labels_match_their_actual_filing_period():
    """Regression test for a real labeling bug: Q3 (Oct-Dec) is due 31-Jan of
    the FOLLOWING calendar year, but the label must reflect the year of the
    Oct-Dec period itself, not the year of the due date. Verified as an
    invariant (not a fixed date) so this holds regardless of when tests run."""
    db = TestingSessionLocal()
    org = Organization(organization_name="Quarter Label Co", firm_type="Partnership", contact_email="q@label.com")
    db.add(org)
    db.commit()
    db.refresh(org)

    client_row = Client(organization_id=org.id, client_name="Quarter Client", client_type="Corporate")
    db.add(client_row)
    db.commit()
    db.refresh(client_row)

    profile = ComplianceProfile(
        organization_id=org.id,
        client_id=client_row.id,
        compliance_type="GST",
        frequency="QUARTERLY",
        due_day=20,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    tasks = ComplianceService.generate_recurring_tasks(db, profile)
    assert len(tasks) == 4

    for task in tasks:
        if "Q3 (Oct-Dec)" in task.task_name:
            label_year = int(task.task_name.rsplit(" ", 1)[-1])
            # Q3's due date is always 31 Jan of (period_year + 1) by construction.
            assert task.due_date.month == 1 and task.due_date.day == 31
            assert task.due_date.year == label_year + 1
        elif "Q4 (Jan-Mar)" in task.task_name:
            label_year = int(task.task_name.rsplit(" ", 1)[-1])
            # Q4's due date (31 May) is always the same calendar year as the label.
            assert task.due_date.month == 5 and task.due_date.day == 31
            assert task.due_date.year == label_year

    # All 4 due dates must be in the future and chronologically distinct.
    due_dates = sorted(t.due_date for t in tasks)
    assert all(d > datetime.utcnow() for d in due_dates)
    assert len(set(due_dates)) == 4

    db.close()


def test_sync_falls_back_to_now_when_extract_metadata_finds_no_date():
    """Regression test: a connector's extract_metadata() legitimately returns
    {"issue_date": None, ...} when the source content has no parseable date
    (a real, expected case, not a malformed response). base.py previously used
    `meta.get("issue_date", datetime.utcnow())`, which only falls back when the
    key is ABSENT — a present-but-None value silently stored issue_date=NULL,
    permanently hiding the update from date-filtered queries (e.g. the
    Intelligence Engine's authority-update lookback window)."""
    db = TestingSessionLocal()

    connector = ConnectorRegistry.get_connector("CBDT Circulars")
    assert connector is not None

    original_discover, original_download = connector.discover, connector.download
    try:
        connector.discover = lambda session: [{
            "document_number": "CBDT/NO-DATE-TEST", "title": "Circular with no parseable date",
            "source_url": "https://incometax.gov.in/nodatetest.txt",
        }]
        # Content deliberately has no date pattern the extractor can match.
        connector.download = lambda url: b"GOVERNMENT OF INDIA - CBDT CIRCULAR\nSubject: undated test content."

        result = connector.sync(db)
        assert result["status"] == "SUCCESS"

        update = db.query(GovernmentUpdate).filter_by(document_number="CBDT/NO-DATE-TEST").first()
        assert update is not None
        assert update.issue_date is not None, "issue_date must fall back to now(), not silently stay NULL"
        assert (datetime.utcnow() - update.issue_date).total_seconds() < 60
    finally:
        connector.discover = original_discover
        connector.download = original_download

    db.close()
