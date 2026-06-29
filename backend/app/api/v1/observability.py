from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from app.core.database import get_db
from app.models.models import (
    RawDocument, ProcessedDocument, StructuredDocument,
    StructuredInvoiceData, StructuredNoticeData,
    Entity, KnowledgeGraphNode, KnowledgeGraphEdge,
    ProcessingPipeline, ProcessingError, User
)
from app.api.deps import get_current_user
from app.services.pipeline import DocumentPipelineOrchestrator

router = APIRouter()

@router.get("/stats")
def get_pipeline_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    org_id = current_user.organization_id

    # 1. Pipeline Queue States
    queue_stats = db.query(
        ProcessingPipeline.status, func.count(ProcessingPipeline.id)
    ).filter(
        ProcessingPipeline.organization_id == org_id
    ).group_by(ProcessingPipeline.status).all()

    queue_dict = {"PENDING": 0, "PROCESSING": 0, "SUCCESS": 0, "FAILED": 0}
    for status_name, count in queue_stats:
        if status_name in queue_dict:
            queue_dict[status_name] = count

    # 2. Parsed Document breakdown
    invoice_count = db.query(StructuredInvoiceData).filter(
        StructuredInvoiceData.organization_id == org_id
    ).count()

    notice_count = db.query(StructuredNoticeData).filter(
        StructuredNoticeData.organization_id == org_id
    ).count()

    # Total Processed count
    total_processed = db.query(ProcessedDocument).filter(
        ProcessedDocument.organization_id == org_id
    ).count()

    # 3. Entity Counts breakdown
    entity_counts = db.query(
        Entity.entity_type, func.count(Entity.id)
    ).filter(
        Entity.organization_id == org_id
    ).group_by(Entity.entity_type).all()

    entity_breakdown = {}
    for etype, count in entity_counts:
        entity_breakdown[etype] = count

    # 4. Knowledge Graph Stats
    node_count = db.query(KnowledgeGraphNode).filter(
        KnowledgeGraphNode.organization_id == org_id
    ).count()

    edge_count = db.query(KnowledgeGraphEdge).filter(
        KnowledgeGraphEdge.organization_id == org_id
    ).count()

    # 5. Fetch recent errors
    recent_errors = db.query(ProcessingError).filter(
        ProcessingError.organization_id == org_id
    ).order_by(ProcessingError.created_at.desc()).limit(10).all()

    error_logs = [
        {
            "id": err.id,
            "pipeline_id": err.pipeline_id,
            "step_name": err.step_name,
            "error_message": err.error_message,
            "stack_trace": err.stack_trace[:300] + "..." if err.stack_trace else None,
            "created_at": err.created_at
        }
        for err in recent_errors
    ]

    # 6. Queue details (documents currently being processed)
    active_pipelines = db.query(
        ProcessingPipeline, RawDocument.name
    ).join(
        RawDocument, ProcessingPipeline.raw_document_id == RawDocument.id
    ).filter(
        ProcessingPipeline.organization_id == org_id
    ).order_by(ProcessingPipeline.updated_at.desc()).limit(20).all()

    queue_list = [
        {
            "pipeline_id": pipe.id,
            "document_name": doc_name,
            "current_step": pipe.current_step,
            "status": pipe.status,
            "retries": pipe.retries,
            "updated_at": pipe.updated_at
        }
        for pipe, doc_name in active_pipelines
    ]

    return {
        "queue_summary": queue_dict,
        "document_breakdown": {
            "Total Processed": total_processed,
            "Invoices": invoice_count,
            "Notices": notice_count,
            "Balance Sheets": total_processed - (invoice_count + notice_count) if total_processed > (invoice_count + notice_count) else 0
        },
        "entity_counts": entity_breakdown,
        "graph_summary": {
            "total_nodes": node_count,
            "total_edges": edge_count
        },
        "recent_errors": error_logs,
        "pipeline_queue": queue_list
    }


from fastapi import BackgroundTasks
from app.core.database import SessionLocal

@router.post("/pipelines/{pipeline_id}/retry")
def retry_pipeline_job(
    pipeline_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pipe = db.query(ProcessingPipeline).filter(
        ProcessingPipeline.id == pipeline_id,
        ProcessingPipeline.organization_id == current_user.organization_id
    ).first()

    if not pipe:
        raise HTTPException(status_code=404, detail="Pipeline job not found")

    pipe.status = "PENDING"
    pipe.current_step = "RETRY"
    db.commit()

    background_tasks.add_task(
        DocumentPipelineOrchestrator.process_document, 
        SessionLocal(), 
        pipe.raw_document_id
    )

    return {"status": "success", "message": "Pipeline retry scheduled."}


@router.get("/config")
def get_system_config(current_user: User = Depends(get_current_user)):
    from app.core.config import settings
    return {
        "llm_provider": settings.LLM_PROVIDER,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "ocr_provider": settings.OCR_PROVIDER,
        "storage_provider": settings.STORAGE_PROVIDER,
        "env": settings.ENV
    }

