import os
import re
import traceback
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from app.models.models import (
    RawDocument, ProcessedDocument, StructuredDocument,
    StructuredInvoiceData, StructuredNoticeData, StructuredReturnData, StructuredBankStatement,
    KnowledgeChunk, Embedding, Entity, EntityRelationship,
    Citation, DocumentVersion, ProcessingPipeline, ProcessingError,
    KnowledgeGraphNode, KnowledgeGraphEdge,
    Form26ASEntry, AISEntry, GSTNoticeEntry, BankStatementTransaction,
    BalanceSheetItem, FinancialRatio, TaxSummary, ChallanEntry, DeductorEntry,
    DocumentAISummary
)
from app.services.deduplication import DeduplicationEngine
from app.services.storage import get_storage_provider
from app.services.ocr import get_ocr_provider
from app.services.embeddings import get_embedding_provider
from app.services.parsers import ParserRegistry
from app.services.graph import GraphService
from app.services.citation import CitationEngine
from app.services.extractor import LegalReferenceExtractor


# Regex helpers for Indian regulatory identifiers
PAN_REGEX = r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b"
GSTIN_REGEX = r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b"
CIN_REGEX = r"\b[ULH][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}\b"
DIN_REGEX = r"\b[0-9]{8}\b"
TAN_REGEX = r"\b[A-Z]{4}[0-9]{5}[A-Z]{1}\b"


class DocumentPipelineOrchestrator:
    @staticmethod
    def process_document(db: Session, raw_doc_id: str) -> bool:
        """Executes the modular pipeline steps for a RawDocument. Fully retryable."""
        raw_doc = db.query(RawDocument).filter(RawDocument.id == raw_doc_id).first()
        if not raw_doc:
            return False

        # Fetch or create pipeline state
        pipeline = db.query(ProcessingPipeline).filter(
            ProcessingPipeline.raw_document_id == raw_doc_id
        ).first()

        if not pipeline:
            pipeline = ProcessingPipeline(
                organization_id=raw_doc.organization_id,
                raw_document_id=raw_doc_id,
                current_step="VALIDATE",
                status="PROCESSING"
            )
            db.add(pipeline)
            db.commit()
            db.refresh(pipeline)
        else:
            pipeline.status = "PROCESSING"
            pipeline.retries += 1
            db.commit()

        try:
            # 1. OCR text extraction
            pipeline.current_step = "OCR"
            db.commit()
            
            # Check if processed document already exists (from a previous retry or run)
            proc_doc = db.query(ProcessedDocument).filter(
                ProcessedDocument.raw_document_id == raw_doc_id
            ).first()

            if not proc_doc:
                storage = get_storage_provider()
                file_bytes = storage.read_file(raw_doc.file_path)
                
                ocr = get_ocr_provider()
                ocr_text = ocr.extract_text(file_bytes, raw_doc.name)
                
                proc_doc = ProcessedDocument(
                    organization_id=raw_doc.organization_id,
                    raw_document_id=raw_doc_id,
                    ocr_text=ocr_text,
                    normalized_text=ocr_text.strip(),
                    language="en",
                    metadata_json={"extracted_at": datetime.utcnow().isoformat()}
                )
                db.add(proc_doc)
                db.flush()
            else:
                ocr_text = proc_doc.ocr_text

            # 2. Parsing (Structured Facts)
            pipeline.current_step = "PARSE"
            db.commit()

            # Classify the document type
            doc_type = DocumentPipelineOrchestrator.classify_document(ocr_text or "", raw_doc.name)
            raw_doc.classification = doc_type
            
            # Sync classification to legacy Document if exists
            from app.models.models import Document
            legacy_doc = db.query(Document).filter(Document.id == raw_doc.id).first()
            if legacy_doc:
                legacy_doc.classification = doc_type
                db.add(legacy_doc)
            db.add(raw_doc)
            db.commit()

            parser = ParserRegistry.get_parser(doc_type)
            if parser and ocr_text:
                structured_facts = parser.parse(ocr_text)
                
                # Create StructuredDocument link
                struct_link = db.query(StructuredDocument).filter(
                    StructuredDocument.raw_document_id == raw_doc_id
                ).first()
                if not struct_link:
                    struct_link = StructuredDocument(
                        organization_id=raw_doc.organization_id,
                        raw_document_id=raw_doc_id,
                        parser_name=doc_type
                    )
                    db.add(struct_link)

                # Store fact tables scoped by type
                if doc_type == "Form 26AS":
                    # Store deductors
                    for ded in structured_facts.get("deductors", []):
                        ded_entry = DeductorEntry(
                            organization_id=raw_doc.organization_id,
                            document_id=raw_doc_id,
                            deductor_name=ded.get("deductor_name"),
                            deductor_tan=ded.get("deductor_tan"),
                            total_tds=ded.get("total_tds", 0.0),
                            total_tcs=ded.get("total_tcs", 0.0)
                        )
                        db.add(ded_entry)
                    # Store TDS entries
                    for entry in structured_facts.get("tds_entries", []):
                        tds_entry = Form26ASEntry(
                            organization_id=raw_doc.organization_id,
                            client_id=raw_doc.client_id,
                            document_id=raw_doc_id,
                            pan=structured_facts.get("pan"),
                            assessment_year=structured_facts.get("assessment_year"),
                            financial_year=structured_facts.get("financial_year"),
                            taxpayer_name=structured_facts.get("taxpayer_name"),
                            deductor_name=entry.get("deductor_name"),
                            deductor_tan=entry.get("deductor_tan"),
                            section=entry.get("section"),
                            section_code=entry.get("section_code"),
                            amount_paid=entry.get("amount_paid"),
                            amount_credited=entry.get("amount_credited"),
                            tax_deducted=entry.get("tax_deducted"),
                            tax_deposited=entry.get("tax_deposited"),
                            raw_row_text=entry.get("raw_row_text")
                        )
                        db.add(tds_entry)
                    # Store Challan entries
                    for challan in structured_facts.get("challan_entries", []):
                        ch_entry = ChallanEntry(
                            organization_id=raw_doc.organization_id,
                            document_id=raw_doc_id,
                            challan_number=challan.get("challan_number"),
                            bsr_code=challan.get("bsr_code"),
                            date_of_deposit=challan.get("date_of_deposit"),
                            amount=challan.get("amount")
                        )
                        db.add(ch_entry)
                    # Create generic TaxSummary
                    tax_sum = TaxSummary(
                        organization_id=raw_doc.organization_id,
                        document_id=raw_doc_id,
                        total_tax_paid=structured_facts.get("total_tds", 0.0),
                        refund_claimed=0.0,
                        outstanding_demand=structured_facts.get("outstanding_demand", 0.0)
                    )
                    db.add(tax_sum)

                elif doc_type == "AIS":
                    # Get client_id
                    doc_record = db.query(Document).filter(Document.id == raw_doc_id).first()
                    client_id = doc_record.client_id if doc_record else None

                    for entry in structured_facts.get("entries", []):
                        ais_entry = AISEntry(
                            organization_id=raw_doc.organization_id,
                            client_id=client_id,
                            document_id=raw_doc_id,
                            pan=structured_facts.get("pan"),
                            taxpayer_name=structured_facts.get("taxpayer_name"),
                            assessment_year=structured_facts.get("assessment_year"),
                            financial_year=structured_facts.get("financial_year"),
                            information_category=entry.get("information_category"),
                            information_source=entry.get("information_source"),
                            source_name=entry.get("source_name"),
                            reported_value=entry.get("reported_value"),
                            processed_value=entry.get("processed_value"),
                            accepted_value=entry.get("accepted_value"),
                            derived_value=entry.get("derived_value"),
                            transaction_type=entry.get("transaction_type"),
                            raw_row_text=entry.get("raw_row_text")
                        )
                        db.add(ais_entry)

                elif doc_type == "TIS":
                    # Get client_id
                    doc_record = db.query(Document).filter(Document.id == raw_doc_id).first()
                    client_id = doc_record.client_id if doc_record else None

                    from app.models.models import TISEntry
                    for entry in structured_facts.get("entries", []):
                        tis_entry = TISEntry(
                            organization_id=raw_doc.organization_id,
                            client_id=client_id,
                            document_id=raw_doc_id,
                            pan=structured_facts.get("pan"),
                            assessment_year=structured_facts.get("assessment_year"),
                            financial_year=structured_facts.get("financial_year"),
                            category=entry.get("category"),
                            subcategory=entry.get("subcategory"),
                            reported_value=entry.get("reported_value"),
                            derived_value=entry.get("derived_value"),
                            feedback_value=entry.get("feedback_value"),
                            transaction_type=entry.get("transaction_type"),
                            raw_row_text=entry.get("raw_row_text")
                        )
                        db.add(tis_entry)

                elif doc_type == "GST Notice":
                    gst_notice = GSTNoticeEntry(
                        organization_id=raw_doc.organization_id,
                        document_id=raw_doc_id,
                        gstin=structured_facts.get("gstin"),
                        notice_number=structured_facts.get("notice_number"),
                        issue_date=structured_facts.get("issue_date"),
                        reply_due_date=structured_facts.get("reply_due_date"),
                        section=structured_facts.get("section"),
                        authority=structured_facts.get("authority"),
                        tax_period=structured_facts.get("tax_period"),
                        amount=structured_facts.get("amount"),
                        penalty=structured_facts.get("penalty"),
                        interest=structured_facts.get("interest"),
                        reason=structured_facts.get("reason"),
                        risk_level=structured_facts.get("risk_level")
                    )
                    db.add(gst_notice)

                elif doc_type == "Invoice":
                    # Backward compatibility for existing queries
                    inv_data = db.query(StructuredInvoiceData).filter(
                        StructuredInvoiceData.raw_document_id == raw_doc_id
                    ).first()
                    if not inv_data:
                        inv_data = StructuredInvoiceData(
                            organization_id=raw_doc.organization_id,
                            raw_document_id=raw_doc_id,
                            **structured_facts
                        )
                        db.add(inv_data)

                elif doc_type == "Notice" or doc_type == "Income Tax Notice":
                    # Backward compatibility for existing queries
                    notice_data = db.query(StructuredNoticeData).filter(
                        StructuredNoticeData.raw_document_id == raw_doc_id
                    ).first()
                    if not notice_data:
                        notice_data = StructuredNoticeData(
                            organization_id=raw_doc.organization_id,
                            raw_document_id=raw_doc_id,
                            **structured_facts
                        )
                        db.add(notice_data)

                elif doc_type == "Bank Statement":
                    for tx in structured_facts.get("transactions", []):
                        tx_entry = BankStatementTransaction(
                            organization_id=raw_doc.organization_id,
                            document_id=raw_doc_id,
                            account_holder=structured_facts.get("account_holder"),
                            bank_name=structured_facts.get("bank_name"),
                            account_number=structured_facts.get("account_number"),
                            transaction_date=datetime.strptime(tx.get("date"), "%d-%m-%Y") if tx.get("date") else None,
                            particulars=tx.get("particulars"),
                            transaction_type=tx.get("type"),
                            amount=tx.get("amount"),
                            balance=tx.get("balance")
                        )
                        db.add(tx_entry)

                elif doc_type == "Balance Sheet":
                    bs_entry = BalanceSheetItem(
                        organization_id=raw_doc.organization_id,
                        document_id=raw_doc_id,
                        financial_year=structured_facts.get("financial_year"),
                        assets=structured_facts.get("assets"),
                        liabilities=structured_facts.get("liabilities"),
                        equity=structured_facts.get("equity"),
                        current_assets=structured_facts.get("current_assets"),
                        current_liabilities=structured_facts.get("current_liabilities"),
                        non_current_assets=structured_facts.get("non_current_assets"),
                        fixed_assets=structured_facts.get("fixed_assets"),
                        capital=structured_facts.get("capital"),
                        reserves=structured_facts.get("reserves")
                    )
                    db.add(bs_entry)
                    
                    # Compute working capital and current ratio
                    cur_assets = structured_facts.get("current_assets", 0.0) or 0.0
                    cur_liab = structured_facts.get("current_liabilities", 0.0) or 0.0
                    ratio = cur_assets / cur_liab if cur_liab > 0 else 1.0
                    ratio_entry = FinancialRatio(
                        organization_id=raw_doc.organization_id,
                        document_id=raw_doc_id,
                        current_ratio=ratio,
                        working_capital=(cur_assets - cur_liab)
                    )
                    db.add(ratio_entry)

                # Save AI summary
                DocumentPipelineOrchestrator.generate_ai_summary(
                    db, raw_doc.organization_id, raw_doc_id, doc_type, structured_facts
                )

            # 3, 4, 5. Entity, Embeddings, Graph steps bypassed for Emergency Reset Sprint
            pipeline.current_step = "COMPLETE"
            db.commit()

            # Complete Pipeline
            pipeline.current_step = "COMPLETE"
            pipeline.status = "SUCCESS"
            db.commit()

            try:
                from app.models.models import Document
                from app.services.tax_intelligence import TaxIntelligenceService
                doc_record = db.query(Document).filter(Document.id == raw_doc_id).first()
                if doc_record and doc_record.client_id:
                    ay = structured_facts.get("assessment_year") or "2025-26"
                    TaxIntelligenceService.recompute(db, doc_record.client_id, ay)
            except Exception as e:
                print(f"Warning: Client Tax Intelligence recompute failed: {e}")

            # Sync V1 legacy document status if exists
            from app.models.models import Document
            legacy_doc = db.query(Document).filter(Document.id == raw_doc.id).first()
            if legacy_doc:
                legacy_doc.processing_status = "COMPLETED"
                legacy_doc.embedding_status = "COMPLETED"
                legacy_doc.extracted_text = ocr_text
                db.commit()
            return True

        except Exception as e:
            db.rollback()
            pipeline.status = "FAILED"
            db.commit()

            # Log detailed stack trace to processing_errors table
            error_log = ProcessingError(
                organization_id=raw_doc.organization_id,
                pipeline_id=pipeline.id,
                step_name=pipeline.current_step,
                error_message=str(e),
                stack_trace=traceback.format_exc()
            )
            db.add(error_log)
            db.commit()

            # Sync V1 legacy document status if exists
            from app.models.models import Document
            legacy_doc = db.query(Document).filter(Document.id == raw_doc.id).first()
            if legacy_doc:
                legacy_doc.processing_status = "FAILED"
                legacy_doc.embedding_status = "FAILED"
                db.commit()

            return False

    @staticmethod
    def extract_entities(text: str) -> List[tuple]:
        """Regex matches Direct/Indirect tax entity codes inside text content"""
        results = []
        
        # PAN
        for m in re.findall(PAN_REGEX, text):
            results.append(("PAN", m))
        
        # GSTIN
        for m in re.findall(GSTIN_REGEX, text):
            results.append(("GSTIN", m))
        
        # CIN
        for m in re.findall(CIN_REGEX, text):
            results.append(("CIN", m))

        # DIN
        for m in re.findall(DIN_REGEX, text):
            results.append(("DIN", m))

        # TAN
        for m in re.findall(TAN_REGEX, text):
            results.append(("TAN", m))

        return list(set(results)) # Unique tuples

    @staticmethod
    def classify_document(text: str, filename: str) -> str:
        name_lower = filename.lower()
        text_lower = text.lower() if text else ""
        
        if "gst notice" in name_lower or "drc-07" in text_lower or ("gst" in text_lower and "notice" in text_lower):
            return "GST Notice"
        elif "tis" in name_lower or "taxpayer information summary" in text_lower:
            return "TIS"
        elif "26as" in name_lower or "26as" in text_lower:
            return "Form 26AS"
        elif (
            "ais" in name_lower or 
            "annual information statement" in text_lower or 
            "information category" in text_lower or 
            "reported value" in text_lower or 
            "processed value" in text_lower or 
            "tds/tcs" in text_lower or 
            "sft" in text_lower or 
            "interest from deposit" in text_lower or 
            "dividend" in text_lower or 
            "securities" in text_lower
        ):
            return "AIS"
        elif "form 16" in name_lower or "form16" in name_lower or "form no. 16" in text_lower:
            return "Form 16"
        elif "itr" in name_lower and "ack" in name_lower or "acknowledgement" in text_lower:
            return "ITR Acknowledgement"
        elif "itr" in name_lower and (name_lower.endswith(".json") or name_lower.endswith(".xml")):
            return "ITR JSON/XML"
        elif "income tax notice" in name_lower or ("income tax" in text_lower and "notice" in text_lower):
            return "Income Tax Notice"
        elif "gstr-1" in name_lower or "gstr1" in name_lower:
            return "GSTR-1"
        elif "gstr-2b" in name_lower or "gstr2b" in name_lower:
            return "GSTR-2B"
        elif "gstr-3b" in name_lower or "gstr3b" in name_lower or "gstr 3b" in text_lower:
            return "GSTR-3B"
        elif "invoice" in name_lower or "bill" in name_lower or "tax invoice" in text_lower:
            return "Invoice"
        elif "bank statement" in name_lower or "bank_statement" in name_lower or "statement of account" in text_lower:
            return "Bank Statement"
        elif "balance sheet" in name_lower or "bs" in name_lower or "balance sheet" in text_lower:
            return "Balance Sheet"
        elif "profit" in name_lower or "p&l" in name_lower or "p and l" in name_lower or "profit & loss" in text_lower:
            return "Profit & Loss"
        elif "trial balance" in name_lower or "trial balance" in text_lower:
            return "Trial Balance"
        elif "audit report" in name_lower or "auditor's report" in text_lower:
            return "Audit Report"
        elif "assessment order" in name_lower or "assessment order" in text_lower:
            return "Assessment Order"
        elif "appeal order" in name_lower or "appeal order" in text_lower:
            return "Appeal Order"
        elif "mca" in name_lower or "mca filing" in text_lower:
            return "MCA Filing"
        elif "roc" in name_lower or "roc filing" in text_lower:
            return "ROC Filing"
        elif filename.endswith(".pdf"):
            return "General PDF"
        else:
            return "Unknown"

    @staticmethod
    def generate_ai_summary(db: Session, org_id: str, doc_id: str, doc_type: str, facts: dict) -> None:
        summary = f"Summary of {doc_type} document."
        insights = []
        issues = []
        missing = []
        actions = []
        risk = "LOW"

        if doc_type == "Form 26AS":
            pan = facts.get("pan") or "Unknown"
            ay = facts.get("assessment_year") or "Unknown"
            fy = facts.get("financial_year") or "Unknown"
            total_tds = facts.get("total_tds", 0.0)
            ded_count = len(facts.get("deductors", []))
            
            summary = f"Form 26AS Tax Credit Statement for PAN {pan}, AY {ay} (FY {fy}). Contains {ded_count} active deductor entries with a total TDS credit of INR {total_tds:,.2f}."
            insights = [
                f"Total tax deducted at source: INR {total_tds:,.2f}.",
                f"Identified {ded_count} deductors matching PAN records."
            ]
            if total_tds > 1000000:
                insights.append("High volume tax deductions detected.")
                
            actions = [
                "Verify that all listed TDS credits are reflected in the client's draft ITR.",
                "Cross-examine deductor TAN numbers with official TRACES portal entries."
            ]
            if not pan or pan == "Unknown":
                missing.append("PAN identifier missing from document header.")
                risk = "MEDIUM"
                
        elif doc_type == "AIS":
            pan = facts.get("pan") or "Unknown"
            ay = facts.get("assessment_year") or "Unknown"
            interest = facts.get("bank_interest", 0.0)
            dividend = facts.get("dividend", 0.0)
            salary = facts.get("salary", 0.0)
            sales = facts.get("sale_transactions", 0.0)
            
            summary = f"Annual Information Statement (AIS) for PAN {pan}, AY {ay}. Identifies salary of INR {salary:,.2f}, bank interest of INR {interest:,.2f}, dividend income of INR {dividend:,.2f}, and securities sales of INR {sales:,.2f}."
            insights = [
                f"Salary reported: INR {salary:,.2f}.",
                f"Bank interest compiled: INR {interest:,.2f}.",
                f"Dividend earnings: INR {dividend:,.2f}."
            ]
            if sales > 0:
                insights.append(f"Mutual fund/equity sale transactions amount to INR {sales:,.2f}.")
                actions.append("Reconcile securities transactions with Capital Gains schedule in ITR.")
            if facts.get("high_value_transactions"):
                risk = "HIGH"
                issues.append("High value financial transactions flagged in AIS summary.")
                actions.append("Request broker contract notes for high-value sales.")
                
        elif doc_type == "GST Notice":
            gstin = facts.get("gstin") or "Unknown"
            num = facts.get("notice_number") or "Unknown"
            amt = facts.get("amount", 0.0)
            risk = facts.get("risk_level", "MEDIUM")
            
            summary = f"GST Demand Notice ({num}) issued to GSTIN {gstin} under {facts.get('section', 'unknown section')}. Total outstanding demand: INR {amt:,.2f}."
            insights = [
                f"Notice number: {num}.",
                f"Applicable section: {facts.get('section', 'N/A')}.",
                f"Total demand amount: INR {amt:,.2f}."
            ]
            issues = [f"Unresolved tax liability of INR {amt:,.2f}."]
            actions = [
                f"Draft formal reply to notice {num} before response deadline.",
                "Verify Input Tax Credit mismatch in GSTR-2B vs GSTR-3B."
            ]
            
        elif doc_type == "Bank Statement":
            holder = facts.get("account_holder") or "Unknown"
            bank = facts.get("bank_name") or "Unknown"
            acc = facts.get("account_number") or "Unknown"
            tx_count = len(facts.get("transactions", []))
            
            summary = f"Bank statement of account {acc} with {bank} held by {holder}. Statement contains {tx_count} transaction lines."
            insights = [
                f"Bank: {bank}.",
                f"Account Holder: {holder}.",
                f"Transaction count: {tx_count}."
            ]
            actions = [
                "Reconcile closing balance with balance sheet ledger entries.",
                "Verify UPI and NEFT transfers for tax audits."
            ]
            
        elif doc_type == "Balance Sheet":
            fy = facts.get("financial_year") or "Unknown"
            assets = facts.get("assets", 0.0)
            liabilities = facts.get("liabilities", 0.0)
            capital = facts.get("capital", 0.0)
            
            summary = f"Balance Sheet for FY {fy}. Total Assets: INR {assets:,.2f}. Total Liabilities: INR {liabilities:,.2f}."
            insights = [
                f"Total Capital & Reserves: INR {(capital + facts.get('reserves', 0.0)):,.2f}.",
                f"Current Assets: INR {facts.get('current_assets', 0.0):,.2f}.",
                f"Current Liabilities: INR {facts.get('current_liabilities', 0.0):,.2f}."
            ]
            # Compute working capital
            wc = facts.get("current_assets", 0.0) - facts.get("current_liabilities", 0.0)
            insights.append(f"Net working capital: INR {wc:,.2f}.")
            if wc < 0:
                issues.append("Negative working capital detected (liquidity risk).")
                risk = "MEDIUM"
            actions.append("Audit accounts payable ageing schedule.")

        else:
            summary = f"Successfully parsed {doc_type} document containing {len(facts)} fields."
            insights = ["Document text successfully run through classification and parser framework."]
            actions = ["Review extracted metadata and verify compliance rules."]

        # Check if already exists, else write
        ai_sum = db.query(DocumentAISummary).filter(DocumentAISummary.document_id == doc_id).first()
        if not ai_sum:
            ai_sum = DocumentAISummary(
                organization_id=org_id,
                document_id=doc_id,
                summary_text=summary,
                key_insights=insights,
                compliance_issues=issues,
                missing_information=missing,
                suggested_actions=actions,
                risk_level=risk
            )
            db.add(ai_sum)
        else:
            ai_sum.summary_text = summary
            ai_sum.key_insights = insights
            ai_sum.compliance_issues = issues
            ai_sum.missing_information = missing
            ai_sum.suggested_actions = actions
            ai_sum.risk_level = risk
        db.commit()
