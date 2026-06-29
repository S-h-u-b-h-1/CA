import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime

from app.core.database import Base
from app.models.models import Organization, User, GovernmentSource, GovernmentUpdate, GovernmentUpdateVersion, ConnectorSyncLog
from app.services.connectors.registry import ConnectorRegistry
from app.services.scheduler import ConnectorScheduler
from app.services.versioning import VersioningEngine


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
    """Verify that running sync twice with changes triggers new versions creation"""
    db = TestingSessionLocal()
    
    # 1. Initialize connector
    cbic_connector = ConnectorRegistry.get_connector("CBIC Circulars")
    assert cbic_connector is not None

    # First sync run
    result1 = cbic_connector.sync(db)
    assert result1["status"] == "SUCCESS"
    assert result1["documents_downloaded"] == 1

    # Verify document and initial version created
    doc = db.query(GovernmentUpdate).filter_by(document_number="Circular No. 204/2026-GST").first()
    assert doc is not None
    assert doc.version == 1

    v1_log = db.query(GovernmentUpdateVersion).filter_by(government_update_id=doc.id, version_number=1).first()
    assert v1_log is not None

    # 2. Modify discover outputs to simulate a revision/new version of the same document number
    original_discover = cbic_connector.discover
    
    try:
        # Mock discover to return the same document number but we will mock downloading different text content
        def mock_discover(session):
            return [{
                "document_number": "Circular No. 204/2026-GST",
                "title": "Clarification on GST rate liability on corporate guarantees (REVISED)",
                "source_url": "https://cbic.gov.in/circulars/Circular_204_2026_GST_revised.txt"
            }]
        cbic_connector.discover = mock_discover

        # Override download method temporarily to return different text for the revised url
        original_download = cbic_connector.download
        def mock_download(url):
            return (
                "GOVERNMENT OF INDIA - OFFICIAL NOTIFICATION PORTAL\n"
                "Source Authority: Central Board of Indirect Taxes and Customs (CBIC)\n"
                "Category: Indirect Tax\n"
                "Ingestion URL: " + url + "\n\n"
                "Subject: Official directive guidelines for compliance.\n"
                "Pursuant to the powers conferred by Section 143 and Section 148 of the Income-tax Act, 1961, "
                "and Rule 12 of the GST Rules, the governing body hereby clarifies the following:\n\n"
                "1. Paragraph One: Compliance dates are extended for the respective filing assessment cycle.\n"
                "2. Paragraph Two: All filings must include validated GSTIN and PAN identifiers.\n"
                "3. Paragraph Three: Failure to reconcile records under Section 119 will trigger interest liabilities.\n\n"
                "4. Paragraph Four: New amendment under Section 154 introduced."
            ).encode("utf-8")
        cbic_connector.download = mock_download

        # Run Second Sync
        result2 = cbic_connector.sync(db)
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
        cbic_connector.discover = original_discover
        cbic_connector.download = original_download

    db.close()
