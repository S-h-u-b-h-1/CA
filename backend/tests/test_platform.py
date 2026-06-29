import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime

from app.core.database import Base
from app.models.models import Organization, User, RawDocument, ProcessedDocument, StructuredInvoiceData, StructuredNoticeData
from app.services.deduplication import DeduplicationEngine, compute_simhash, get_hamming_distance
from app.services.parsers import ParserRegistry, InvoiceParser, NoticeParser, BalanceSheetParser
from app.services.pipeline import DocumentPipelineOrchestrator

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


def test_simhash_similarity():
    """Verify that SimHash calculates Hamming distances accurately for text similarity"""
    text1 = "This is a standard tax invoice from XYZ Corp for services rendered."
    text2 = "This is a standard tax invoice from XYZ Corp for services rendered."
    text3 = "Notice under Section 143(1) of the Income Tax Act, 1961 for Assessment Year 2025-26."
    
    hash1 = compute_simhash(text1)
    hash2 = compute_simhash(text2)
    hash3 = compute_simhash(text3)
    
    assert hash1 == hash2
    
    dist_same = get_hamming_distance(hash1, hash2)
    dist_diff = get_hamming_distance(hash1, hash3)
    
    assert dist_same == 0
    assert dist_diff > 5  # Distinct texts should have high bit difference


def test_deduplication_engine():
    """Verify hashes extraction and duplicate checks inside an organization"""
    db = TestingSessionLocal()
    
    # Setup mock org and document
    org = Organization(organization_name="Test Firm", firm_type="Partnership", contact_email="test@firm.com")
    db.add(org)
    db.commit()
    db.refresh(org)
    
    file_content = b"GSTIN: 27AAAAA1111A1Z1\nVendor Legal Name: Acme Corp\nInvoice Number: INV-99\nTotal Amount: INR 45,000"
    hashes = DeduplicationEngine.calculate_file_hashes(file_content)
    
    assert hashes["sha256"] is not None
    assert hashes["md5"] is not None
    assert hashes["similarity_hash"] is not None
    assert "sz_" in hashes["file_fingerprint"]

    # Save initial raw document
    raw_doc = RawDocument(
        organization_id=org.id,
        name="invoice.pdf",
        file_path="/mock/storage/invoice.pdf",
        file_size=len(file_content),
        mime_type="application/pdf",
        sha256_hash=hashes["sha256"],
        md5_hash=hashes["md5"],
        similarity_hash=hashes["similarity_hash"],
        file_fingerprint=hashes["file_fingerprint"],
        version=1,
        status="ACTIVE"
    )
    db.add(raw_doc)
    db.commit()

    # Check duplicate detection
    duplicate = DeduplicationEngine.check_duplicate_by_sha256(db, org.id, hashes["sha256"])
    assert duplicate is not None
    assert duplicate.id == raw_doc.id

    # Create new version
    version_log = DeduplicationEngine.create_document_version(
        db, org.id, raw_doc, "/mock/storage/invoice_v2.pdf", "Updated file uploaded"
    )
    assert raw_doc.version == 2
    assert version_log.version_number == 1
    assert version_log.raw_document_id == raw_doc.id

    db.close()


def test_parsers():
    """Verify Invoice and Notice parsers regex extraction logic"""
    invoice_text = "Legal Name: Apex Solutions Ltd\nGSTIN: 27ABCDE1234F1Z5\nInvoice No: INV-2026-908\nTaxable Value: 10,000.00\nIntegrated Tax: 1,800.00\nTotal Amount: 11,800.00"
    notice_text = "Notice under Section 148 of the Income Tax Act\nAssessment Year: 2025-26\nDIN: DIN/IT/2026/0018\nOutstanding Tax Demand: INR 1,50,000\nDue Date: 2026-07-31"

    # Test Invoice Parser
    inv_parser = InvoiceParser()
    inv_facts = inv_parser.parse(invoice_text)
    assert inv_facts["GSTIN"] == "27ABCDE1234F1Z5"
    assert inv_facts["invoice_number"] == "INV-2026-908"
    assert inv_facts["vendor_name"] == "Apex Solutions Ltd"
    assert inv_facts["taxable_value"] == 10000.0
    assert inv_facts["igst"] == 1800.0
    assert inv_facts["total_amount"] == 11800.0

    # Test Notice Parser
    notice_parser = NoticeParser()
    notice_facts = notice_parser.parse(notice_text)
    assert notice_facts["assessment_year"] == "2025-26"
    assert notice_facts["section"] == "Section 148"
    assert notice_facts["din"] == "DIN/IT/2026/0018"
    assert notice_facts["tax_demand_amount"] == 150000.0


def test_pipeline_execution():
    """Verify full step-by-step pipeline execution and table population"""
    db = TestingSessionLocal()

    # 1. Setup Organization
    org = Organization(organization_name="Ingestion Lab", firm_type="LLP", contact_email="lab@ingest.com")
    db.add(org)
    db.commit()
    db.refresh(org)

    # 2. Setup mock file in Storage falling back to local fallback
    file_text = "Legal Name: Apex Supplies\nGSTIN: 27ABCDE1234F1Z5\nInvoice No: INV-101\nTotal Amount: INR 5,000"
    hashes = DeduplicationEngine.calculate_file_hashes(file_text.encode("utf-8"))
    
    # Save a physical file in local storage path mapped to settings upload dir
    from app.services.storage import get_storage_provider
    storage = get_storage_provider()
    file_path = storage.save_file("test_pipeline_invoice.txt", file_text.encode("utf-8"))

    raw_doc = RawDocument(
        organization_id=org.id,
        name="test_pipeline_invoice.txt",
        file_path=file_path,
        file_size=len(file_text),
        mime_type="text/plain",
        sha256_hash=hashes["sha256"],
        md5_hash=hashes["md5"],
        similarity_hash=hashes["similarity_hash"],
        file_fingerprint=hashes["file_fingerprint"],
        version=1,
        status="ACTIVE"
    )
    db.add(raw_doc)
    db.commit()
    db.refresh(raw_doc)

    # 3. Run Pipeline Orchestrator
    success = DocumentPipelineOrchestrator.process_document(db, raw_doc.id)
    assert success is True

    # 4. Verify DB Records
    proc_doc = db.query(ProcessedDocument).filter_by(raw_document_id=raw_doc.id).first()
    assert proc_doc is not None
    assert "Apex Supplies" in proc_doc.ocr_text

    inv_data = db.query(StructuredInvoiceData).filter_by(raw_document_id=raw_doc.id).first()
    assert inv_data is not None
    assert inv_data.vendor_name == "Apex Supplies"
    assert inv_data.invoice_number == "INV-101"
    assert inv_data.GSTIN == "27ABCDE1234F1Z5"

    db.close()
