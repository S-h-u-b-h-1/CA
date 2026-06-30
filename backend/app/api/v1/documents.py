import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.models import Document, User, AuditLog, DocumentProcessingJob, DocumentTextChunk, RawDocument, DocumentVersion
from app.schemas.schemas import DocumentResponse, DocumentUpdate
from app.api.deps import get_current_user
from app.services.storage import get_storage_provider
from app.services.ocr import get_ocr_provider
from app.services.embeddings import get_embedding_provider
from app.services.deduplication import DeduplicationEngine
from app.services.pipeline import DocumentPipelineOrchestrator

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".csv", ".jpg", ".png", ".txt"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

def process_document_pipeline_task(document_id: str, db_session_factory):
    # Retrieve direct session since it's background task
    db = db_session_factory()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return

        doc.processing_status = "PROCESSING"
        db.commit()

        # 1. Trigger OCR extraction
        ocr_job = DocumentProcessingJob(
            organization_id=doc.organization_id,
            document_id=doc.id,
            job_type="OCR",
            status="PROCESSING"
        )
        db.add(ocr_job)
        db.commit()

        storage = get_storage_provider()
        file_bytes = storage.read_file(doc.file_path)

        ocr = get_ocr_provider()
        extracted_text = ocr.extract_text(file_bytes, doc.name)
        
        doc.extracted_text = extracted_text
        ocr_job.status = "SUCCESS"
        db.commit()

        # 2. Trigger Chunking & Embeddings
        embed_job = DocumentProcessingJob(
            organization_id=doc.organization_id,
            document_id=doc.id,
            job_type="EMBEDDING",
            status="PROCESSING"
        )
        db.add(embed_job)
        db.commit()

        # Chunk the text (basic split by paragraphs/lines)
        chunks = [c.strip() for c in extracted_text.split("\n\n") if c.strip()]
        if not chunks:
            chunks = [extracted_text]

        embedding_provider = get_embedding_provider()
        for idx, text_chunk in enumerate(chunks):
            vector = embedding_provider.get_embedding(text_chunk)
            chunk_obj = DocumentTextChunk(
                document_id=doc.id,
                chunk_index=idx,
                text_content=text_chunk,
                embedding_vector=vector
            )
            db.add(chunk_obj)
        
        doc.embedding_status = "COMPLETED"
        doc.processing_status = "COMPLETED"
        embed_job.status = "SUCCESS"
        db.commit()

    except Exception as e:
        db.rollback()
        # Mark jobs as failed
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.processing_status = "FAILED"
            doc.embedding_status = "FAILED"
            db.commit()
            
            # Log failure job
            fail_job = DocumentProcessingJob(
                organization_id=doc.organization_id,
                document_id=doc.id,
                job_type="PIPELINE",
                status="FAILED",
                error_message=str(e)
            )
            db.add(fail_job)
            db.commit()
    finally:
        db.close()


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: str = Form(...),
    client_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Validate File Ext
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format. Supported: {ALLOWED_EXTENSIONS}"
        )

    # 2. Validate Size
    file_content = await file.read()
    file_size = len(file_content)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds maximum limit of 10MB"
        )

    # 2.5 Validate File Signature (Magic Bytes) to prevent executable disguise
    if file_ext == ".pdf" and not file_content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File signature validation failed: content does not match PDF format."
        )
    elif file_ext == ".png" and not file_content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File signature validation failed: content does not match PNG format."
        )
    elif file_ext in (".jpg", ".jpeg") and not file_content.startswith(b"\xff\xd8\xff"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File signature validation failed: content does not match JPEG format."
        )
    elif file_ext in (".docx", ".xlsx") and not file_content.startswith(b"PK\x03\x04"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File signature validation failed: content does not match ZIP/Office format."
        )

    # 3. Compute hashes for deduplication
    hashes = DeduplicationEngine.calculate_file_hashes(file_content)

    # 4. Save file via storage provider
    safe_filename = f"{uuid.uuid4()}{file_ext}"
    storage = get_storage_provider()
    file_path = storage.save_file(safe_filename, file_content)

    # 5. Check if duplicate exists under the same organization
    existing_raw = DeduplicationEngine.check_duplicate_by_sha256(
        db, current_user.organization_id, hashes["sha256"]
    )

    if existing_raw:
        # Create a new version log for this document
        DeduplicationEngine.create_document_version(
            db,
            current_user.organization_id,
            existing_raw,
            file_path,
            f"Duplicate file uploaded: {file.filename}. Incremented version."
        )
        raw_doc = existing_raw
    else:
        # Create new RawDocument entry
        raw_doc = RawDocument(
            organization_id=current_user.organization_id,
            client_id=client_id,
            name=file.filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=file.content_type or "application/octet-stream",
            sha256_hash=hashes["sha256"],
            md5_hash=hashes["md5"],
            similarity_hash=hashes["similarity_hash"],
            file_fingerprint=hashes["file_fingerprint"],
            version=1,
            status="ACTIVE"
        )
        db.add(raw_doc)
        db.flush()

    # 6. Save legacy Document entry to maintain backwards compatibility
    doc = db.query(Document).filter(Document.id == raw_doc.id).first()
    if not doc:
        doc = Document(
            id=raw_doc.id,  # Link RawDocument UUID directly to Document UUID
            organization_id=current_user.organization_id,
            client_id=client_id,
            name=file.filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=file.content_type or "application/octet-stream",
            category=category,
            processing_status="PENDING",
            embedding_status="PENDING"
        )
        db.add(doc)
        db.flush()

    # Log action
    audit = AuditLog(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="DOCUMENT_UPLOAD",
        entity_type="DOCUMENT",
        entity_id=doc.id,
        details=f"Uploaded file: {file.filename} as {category}. Deduplication status: {'Duplicate/NewVersion' if existing_raw else 'Unique'}"
    )
    db.add(audit)
    db.commit()

    # 7. Trigger Background V2 processing pipeline
    from app.core.database import SessionLocal
    background_tasks.add_task(DocumentPipelineOrchestrator.process_document, SessionLocal(), raw_doc.id)

    db.refresh(doc)
    return doc


@router.get("", response_model=List[DocumentResponse])
def list_documents(
    client_id: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Document).filter(
        Document.organization_id == current_user.organization_id,
        Document.deleted_at.is_(None)
    )

    if client_id:
        query = query.filter(Document.client_id == client_id)
    if category:
        query = query.filter(Document.category == category)

    return query.offset(skip).limit(limit).all()


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.organization_id == current_user.organization_id,
        Document.deleted_at.is_(None)
    ).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    return doc


@router.put("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: str,
    payload: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.organization_id == current_user.organization_id,
        Document.deleted_at.is_(None)
    ).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(doc, field, value)

    audit = AuditLog(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="DOCUMENT_UPDATE",
        entity_type="DOCUMENT",
        entity_id=doc.id,
        details=f"Updated fields: {list(update_data.keys())}"
    )
    db.add(audit)
    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.organization_id == current_user.organization_id,
        Document.deleted_at.is_(None)
    ).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Soft delete
    doc.deleted_at = datetime.utcnow()

    # Try to delete actual file if local storage
    try:
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
    except Exception:
        pass  # Non-blocking file deletion failure

    audit = AuditLog(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="DOCUMENT_DELETE",
        entity_type="DOCUMENT",
        entity_id=doc.id,
        details=f"Soft deleted file: {doc.name}"
    )
    db.add(audit)
    db.commit()
    return None


@router.get("/{document_id}/structured")
def get_structured_data(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.organization_id == current_user.organization_id,
        Document.deleted_at.is_(None)
    ).first()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
        
    from app.models.models import (
        Form26ASEntry, AISEntry, GSTNoticeEntry, BankStatementTransaction,
        BalanceSheetItem, FinancialRatio, TaxSummary, ChallanEntry, DeductorEntry
    )
    
    classification = doc.classification or "Unknown"
    
    data = {
        "classification": classification,
        "pan": None,
        "assessment_year": None,
        "financial_year": None,
        "details": {}
    }
    
    if classification == "Form 26AS":
        f26_entries = db.query(Form26ASEntry).filter(Form26ASEntry.document_id == document_id).all()
        deductors = db.query(DeductorEntry).filter(DeductorEntry.document_id == document_id).all()
        challans = db.query(ChallanEntry).filter(ChallanEntry.document_id == document_id).all()
        tax_sum = db.query(TaxSummary).filter(TaxSummary.document_id == document_id).first()
        
        if f26_entries:
            data["pan"] = f26_entries[0].pan
            data["assessment_year"] = f26_entries[0].assessment_year
            data["financial_year"] = f26_entries[0].financial_year
            
        data["details"] = {
            "entries": [{
                "deductor_name": e.deductor_name,
                "deductor_tan": e.deductor_tan,
                "section": e.section,
                "amount_paid": e.amount_paid,
                "tax_deducted": e.tax_deducted,
                "tax_deposited": e.tax_deposited
            } for e in f26_entries],
            "deductors": [{
                "name": d.deductor_name,
                "tan": d.deductor_tan,
                "total_tds": d.total_tds,
                "total_tcs": d.total_tcs
            } for d in deductors],
            "challans": [{
                "challan_number": c.challan_number,
                "bsr_code": c.bsr_code,
                "date_of_deposit": c.date_of_deposit.isoformat() if c.date_of_deposit else None,
                "amount": c.amount
            } for c in challans],
            "summary": {
                "total_tax_paid": tax_sum.total_tax_paid if tax_sum else 0.0,
                "refund_claimed": tax_sum.refund_claimed if tax_sum else 0.0,
                "outstanding_demand": tax_sum.outstanding_demand if tax_sum else 0.0
            }
        }
        
    elif classification in ["AIS", "TIS"]:
        ais = db.query(AISEntry).filter(AISEntry.document_id == document_id).first()
        if ais:
            data["pan"] = ais.pan
            data["assessment_year"] = ais.assessment_year
            data["financial_year"] = ais.financial_year
            data["details"] = {
                "bank_interest": ais.bank_interest,
                "dividend": ais.dividend,
                "salary": ais.salary,
                "purchase_transactions": ais.purchase_transactions,
                "sale_transactions": ais.sale_transactions,
                "foreign_remittance": ais.foreign_remittance,
                "high_value_transactions": ais.high_value_transactions
            }
            
    elif classification == "GST Notice":
        gst = db.query(GSTNoticeEntry).filter(GSTNoticeEntry.document_id == document_id).first()
        if gst:
            data["details"] = {
                "gstin": gst.gstin,
                "notice_number": gst.notice_number,
                "issue_date": gst.issue_date.isoformat() if gst.issue_date else None,
                "reply_due_date": gst.reply_due_date.isoformat() if gst.reply_due_date else None,
                "section": gst.section,
                "authority": gst.authority,
                "tax_period": gst.tax_period,
                "amount": gst.amount,
                "penalty": gst.penalty,
                "interest": gst.interest,
                "reason": gst.reason,
                "risk_level": gst.risk_level
            }
            
    elif classification == "Bank Statement":
        txs = db.query(BankStatementTransaction).filter(BankStatementTransaction.document_id == document_id).all()
        if txs:
            data["details"] = {
                "account_holder": txs[0].account_holder,
                "bank_name": txs[0].bank_name,
                "account_number": txs[0].account_number,
                "transactions": [{
                    "date": t.transaction_date.strftime("%d-%m-%Y") if t.transaction_date else None,
                    "particulars": t.particulars,
                    "type": t.transaction_type,
                    "amount": t.amount,
                    "balance": t.balance
                } for t in txs]
            }
            
    elif classification == "Balance Sheet":
        bs = db.query(BalanceSheetItem).filter(BalanceSheetItem.document_id == document_id).first()
        ratio = db.query(FinancialRatio).filter(FinancialRatio.document_id == document_id).first()
        if bs:
            data["financial_year"] = bs.financial_year
            data["details"] = {
                "assets": bs.assets,
                "liabilities": bs.liabilities,
                "equity": bs.equity,
                "current_assets": bs.current_assets,
                "current_liabilities": bs.current_liabilities,
                "non_current_assets": bs.non_current_assets,
                "fixed_assets": bs.fixed_assets,
                "capital": bs.capital,
                "reserves": bs.reserves,
                "current_ratio": ratio.current_ratio if ratio else 1.0,
                "working_capital": ratio.working_capital if ratio else 0.0
            }
            
    else:
        # Fallback structured tables
        from app.models.models import StructuredInvoiceData, StructuredNoticeData
        inv = db.query(StructuredInvoiceData).filter(StructuredInvoiceData.raw_document_id == document_id).first()
        if inv:
            data["classification"] = "Invoice"
            data["details"] = {
                "invoice_number": inv.invoice_number,
                "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                "vendor_name": inv.vendor_name,
                "total_amount": inv.total_amount,
                "taxable_value": inv.taxable_value
            }
        else:
            notc = db.query(StructuredNoticeData).filter(StructuredNoticeData.raw_document_id == document_id).first()
            if notc:
                data["classification"] = "Notice"
                data["assessment_year"] = notc.assessment_year
                data["details"] = {
                    "din": notc.din,
                    "section": notc.section,
                    "tax_demand_amount": notc.tax_demand_amount,
                    "issuing_authority": notc.issuing_authority
                }
                
    return data


@router.get("/{document_id}/summary")
def get_document_summary(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.organization_id == current_user.organization_id,
        Document.deleted_at.is_(None)
    ).first()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
        
    from app.models.models import DocumentAISummary
    ai_sum = db.query(DocumentAISummary).filter(DocumentAISummary.document_id == document_id).first()
    if not ai_sum:
        # Generate on-demand dummy or fallback summary if not created yet (to prevent crashes)
        return {
            "summary": "Document processing complete. Detailed summary and insights generation in progress.",
            "key_insights": ["Document classified and indexed successfully."],
            "compliance_issues": [],
            "missing_information": [],
            "suggested_actions": ["Review raw OCR extracted text in document dashboard."],
            "risk_level": "LOW"
        }
        
    return {
        "summary": ai_sum.summary_text,
        "key_insights": ai_sum.key_insights or [],
        "compliance_issues": ai_sum.compliance_issues or [],
        "missing_information": ai_sum.missing_information or [],
        "suggested_actions": ai_sum.suggested_actions or [],
        "risk_level": ai_sum.risk_level
    }


@router.get("/{document_id}/form26as")
def get_form26as_data(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.organization_id == current_user.organization_id,
        Document.deleted_at.is_(None)
    ).first()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
        
    from app.models.models import ProcessingPipeline, ProcessingError, ProcessedDocument, Form26ASEntry
    
    pipeline = db.query(ProcessingPipeline).filter(
        ProcessingPipeline.raw_document_id == document_id
    ).first()
    
    pipeline_status = pipeline.status if pipeline else "PENDING"
    
    if pipeline_status == "FAILED":
        err_msg = "Form 26AS processing failed"
        if pipeline:
            err_row = db.query(ProcessingError).filter(
                ProcessingError.pipeline_id == pipeline.id
            ).order_by(ProcessingError.created_at.desc()).first()
            if err_row:
                err_msg = err_row.error_message
        return {
            "document_id": document_id,
            "status": "failed",
            "error": err_msg
        }
        
    proc_doc = db.query(ProcessedDocument).filter(
        ProcessedDocument.raw_document_id == document_id
    ).first()
    
    if pipeline_status != "SUCCESS" or not proc_doc:
        return {
            "document_id": document_id,
            "status": "processing" if pipeline_status == "PROCESSING" else "pending",
            "classification": "FORM_26AS",
            "extracted_text_preview": "",
            "summary": {
                "pan": None,
                "assessment_year": None,
                "total_tds": 0.0,
                "deductor_count": 0
            },
            "entries": []
        }
        
    entries_rows = db.query(Form26ASEntry).filter(
        Form26ASEntry.document_id == document_id
    ).all()
    
    deductors_tan = set()
    total_tds = 0.0
    entries = []
    
    pan = None
    assessment_year = None
    
    for e in entries_rows:
        if e.pan:
            pan = e.pan
        if e.assessment_year:
            assessment_year = e.assessment_year
        if e.deductor_tan:
            deductors_tan.add(e.deductor_tan)
            
        tds_dep = e.tax_deposited or 0.0
        total_tds += tds_dep
        
        entries.append({
            "deductor_name": e.deductor_name,
            "deductor_tan": e.deductor_tan,
            "section_code": e.section_code or e.section or "194A",
            "amount_paid": e.amount_paid or 0.0,
            "tax_deducted": e.tax_deducted or 0.0,
            "tax_deposited": tds_dep,
            "raw_row_text": e.raw_row_text or ""
        })
        
    extracted_text_preview = proc_doc.ocr_text[:1000] if proc_doc.ocr_text else ""
    
    return {
        "document_id": document_id,
        "status": "processed",
        "classification": "FORM_26AS",
        "extracted_text_preview": extracted_text_preview,
        "summary": {
            "pan": pan or "N/A",
            "assessment_year": assessment_year or "N/A",
            "total_tds": total_tds,
            "deductor_count": len(deductors_tan)
        },
        "entries": entries
    }
