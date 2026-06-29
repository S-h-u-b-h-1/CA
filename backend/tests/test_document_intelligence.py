import pytest
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.models import (
    RawDocument, ProcessedDocument, Form26ASEntry, AISEntry, GSTNoticeEntry,
    BankStatementTransaction, BalanceSheetItem, FinancialRatio, TaxSummary,
    DeductorEntry, ChallanEntry, DocumentAISummary
)
from app.services.parsers import ParserRegistry
from app.services.pipeline import DocumentPipelineOrchestrator

def test_document_classification():
    # Verify classification based on text content and filenames
    c1 = DocumentPipelineOrchestrator.classify_document("Contains Form 26AS tax credits", "Form26AS.pdf")
    assert c1 == "Form 26AS"

    c2 = DocumentPipelineOrchestrator.classify_document("Annual Information Statement interest details", "AIS.pdf")
    assert c2 == "AIS"

    c3 = DocumentPipelineOrchestrator.classify_document("GST demand notice under section 73", "notice.pdf")
    assert c3 == "GST Notice"

    c4 = DocumentPipelineOrchestrator.classify_document("HDFC Bank Account Statement for May", "bank_statement.pdf")
    assert c4 == "Bank Statement"


def test_form26as_parser():
    sample_text = (
        "PAN of Taxpayer: ABCDE1234F\n"
        "Assessment Year: 2026-27\n"
        "Financial Year: 2025-26\n"
        "Name of Taxpayer: Ramesh Kumar\n"
        "Name of Deductor: Tata Consultancy Services TAN: MNOA12345P\n"
        "Section 194C Amount Paid: 5,00,000 TDS: 10,000\n"
        "Challan No: 910283 BSR Code: 0281928 Amount: 50,000\n"
    )
    parser = ParserRegistry.get_parser("Form 26AS")
    assert parser is not None
    facts = parser.parse(sample_text)

    assert facts["pan"] == "ABCDE1234F"
    assert facts["assessment_year"] == "2026-27"
    assert facts["financial_year"] == "2025-26"
    assert facts["total_tds"] == 10000.0
    assert len(facts["deductors"]) == 1
    assert facts["deductors"][0]["deductor_name"] == "Tata Consultancy Services"
    assert facts["deductors"][0]["deductor_tan"] == "MNOA12345P"
    assert len(facts["challan_entries"]) == 1
    assert facts["challan_entries"][0]["challan_number"] == "910283"
    assert facts["challan_entries"][0]["amount"] == 50000.0


def test_ais_parser():
    sample_text = (
        "PAN: ABCDE1234F\n"
        "Assessment Year: 2026-27\n"
        "Saving Bank Interest: 15,200\n"
        "Dividend Income: 45,000\n"
        "Salary: 12,00,000\n"
        "Sale of Securities: 1,50,000\n"
    )
    parser = ParserRegistry.get_parser("AIS")
    assert parser is not None
    facts = parser.parse(sample_text)

    assert facts["pan"] == "ABCDE1234F"
    assert facts["assessment_year"] == "2026-27"
    assert facts["bank_interest"] == 15200.0
    assert facts["dividend"] == 45000.0
    assert facts["salary"] == 1200000.0
    assert facts["sale_transactions"] == 150000.0


def test_gst_notice_parser():
    sample_text = (
        "GSTIN: 27AAACA1234A1Z5\n"
        "Notice No: GST/2026/092019\n"
        "under section 73 of the CGST Act\n"
        "Outstanding Demand: 2,50,000\n"
    )
    parser = ParserRegistry.get_parser("GST Notice")
    assert parser is not None
    facts = parser.parse(sample_text)

    assert facts["gstin"] == "27AAACA1234A1Z5"
    assert facts["notice_number"] == "GST/2026/092019"
    assert facts["section"] == "Section 73"
    assert facts["amount"] == 250000.0


def test_bank_statement_parser():
    sample_text = (
        "HDFC Bank statement of account 501002930219\n"
        "Customer Name: Ramesh Kumar\n"
        "15-06-2026 DEBIT UPI 4,500 Balance 90,000\n"
        "20-06-2026 CREDIT NEFT 25,000 Balance 1,15,000\n"
    )
    parser = ParserRegistry.get_parser("Bank Statement")
    assert parser is not None
    facts = parser.parse(sample_text)

    assert facts["bank_name"] == "HDFC Bank"
    assert facts["account_number"] == "501002930219"
    assert facts["account_holder"] == "Ramesh Kumar"
    assert len(facts["transactions"]) == 2
    assert facts["transactions"][0]["amount"] == 4500.0
    assert facts["transactions"][0]["balance"] == 90000.0
    assert facts["transactions"][1]["type"] == "CREDIT"
    assert facts["transactions"][1]["amount"] == 25000.0


def test_balance_sheet_parser():
    sample_text = (
        "Share Capital 10,00,000\n"
        "Reserves & Surplus 5,00,000\n"
        "Current Liabilities 3,00,000\n"
        "Current Assets 6,00,000\n"
        "Fixed Assets 12,00,000\n"
    )
    parser = ParserRegistry.get_parser("Balance Sheet")
    assert parser is not None
    facts = parser.parse(sample_text)

    assert facts["capital"] == 1000000.0
    assert facts["reserves"] == 500000.0
    assert facts["current_liabilities"] == 300000.0
    assert facts["current_assets"] == 600000.0
    assert facts["fixed_assets"] == 1200000.0
    assert facts["assets"] == 1800000.0  # fixed (12L) + current (6L)
    assert facts["equity"] == 1500000.0  # capital (10L) + reserves (5L)
