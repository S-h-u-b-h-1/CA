from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.models.models import Client, User, AuditLog
from app.schemas.schemas import ClientCreate, ClientUpdate, ClientResponse
from app.api.deps import get_current_user

router = APIRouter()

@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if client name already exists for this organization
    existing = db.query(Client).filter(
        Client.organization_id == current_user.organization_id,
        Client.client_name == payload.client_name,
        Client.deleted_at.is_(None)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client with this name already exists in your organization"
        )

    client = Client(
        organization_id=current_user.organization_id,
        client_name=payload.client_name,
        client_type=payload.client_type,
        PAN=payload.PAN,
        GSTIN=payload.GSTIN,
        CIN_LLPIN=payload.CIN_LLPIN,
        TAN=payload.TAN,
        registered_address=payload.registered_address,
        contact_person=payload.contact_person,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        industry=payload.industry,
        status="ACTIVE"
    )
    db.add(client)
    db.flush()

    audit = AuditLog(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="CLIENT_CREATE",
        entity_type="CLIENT",
        entity_id=client.id,
        details=f"Created client: {client.client_name}"
    )
    db.add(audit)
    db.commit()
    db.refresh(client)
    return client


@router.get("", response_model=List[ClientResponse])
def list_clients(
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Client).filter(
        Client.organization_id == current_user.organization_id,
        Client.deleted_at.is_(None)
    )

    if status_filter:
        query = query.filter(Client.status == status_filter)
    
    if search:
        query = query.filter(Client.client_name.ilike(f"%{search}%"))

    return query.offset(skip).limit(limit).all()


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.organization_id == current_user.organization_id,
        Client.deleted_at.is_(None)
    ).first()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    return client


@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: str,
    payload: ClientUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.organization_id == current_user.organization_id,
        Client.deleted_at.is_(None)
    ).first()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )

    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)

    audit = AuditLog(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="CLIENT_UPDATE",
        entity_type="CLIENT",
        entity_id=client.id,
        details=f"Updated fields: {list(update_data.keys())}"
    )
    db.add(audit)
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.organization_id == current_user.organization_id,
        Client.deleted_at.is_(None)
    ).first()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )

    # Soft delete
    client.deleted_at = datetime.utcnow()
    client.status = "ARCHIVED"

    audit = AuditLog(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="CLIENT_DELETE",
        entity_type="CLIENT",
        entity_id=client.id,
        details=f"Soft deleted client: {client.client_name}"
    )
    db.add(audit)
    db.commit()
    return None


@router.get("/{client_id}/tax-profile")
def get_client_tax_profile(
    client_id: str,
    assessment_year: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.organization_id == current_user.organization_id,
        Client.deleted_at.is_(None)
    ).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
        
    ay_val = assessment_year or "2025-26"
    if len(ay_val) == 9: # 2025-2026
        ay_val = f"{ay_val[:4]}-{ay_val[7:]}" # 2025-26
        
    # Recompute to ensure aggregates cache is fresh
    from app.services.tax_intelligence import TaxIntelligenceService
    TaxIntelligenceService.recompute(db, client_id, ay_val)

    from app.models.models import ClientTaxProfile, ClientTaxSummary, ClientTaxInsight, DocumentMatch, Document
    
    profile = db.query(ClientTaxProfile).filter(
        ClientTaxProfile.client_id == client_id,
        ClientTaxProfile.assessment_year == ay_val
    ).first()
    
    summary = db.query(ClientTaxSummary).filter(
        ClientTaxSummary.client_id == client_id,
        ClientTaxSummary.assessment_year == ay_val
    ).first()
    
    insights = db.query(ClientTaxInsight).filter(
        ClientTaxInsight.client_id == client_id,
        ClientTaxInsight.assessment_year == ay_val
    ).all()
    
    matches = db.query(DocumentMatch).filter(
        DocumentMatch.client_id == client_id,
        DocumentMatch.assessment_year == ay_val
    ).all()
    
    docs = db.query(Document).filter(
        Document.client_id == client_id,
        Document.deleted_at.is_(None)
    ).all()

    return {
        "profile": {
            "pan": profile.pan if profile else client.PAN or "N/A",
            "client_name": profile.taxpayer_name if profile else client.client_name,
            "assessment_year": ay_val,
            "financial_year": profile.financial_year if profile else "2024-25",
            "latest_upload_date": profile.latest_upload_date.isoformat() if profile and profile.latest_upload_date else None,
            "processing_status": profile.processing_status if profile else "NO_DOCUMENTS",
            "confidence": profile.confidence if profile else 1.0
        },
        "summary": {
            "total_tds": summary.total_tds if summary else 0.0,
            "total_reported_income": summary.total_reported_income if summary else 0.0,
            "interest_income": summary.interest_income if summary else 0.0,
            "dividend_income": summary.dividend_income if summary else 0.0,
            "salary_income": summary.salary_income if summary else 0.0,
            "securities_transactions": summary.securities_transactions if summary else 0.0,
            "mutual_fund_transactions": summary.mutual_fund_transactions if summary else 0.0,
            "property_transactions": summary.property_transactions if summary else 0.0,
            "sft_transactions": summary.sft_transactions if summary else 0.0,
            "other_income": summary.other_income if summary else 0.0,
            "refund_amount": summary.refund_amount if summary else 0.0,
            "demand_amount": summary.demand_amount if summary else 0.0,
            "deductor_count": summary.deductor_count if summary else 0,
            "ais_category_count": summary.ais_category_count if summary else 0,
            "high_value_transactions": summary.high_value_transactions if summary else 0,
            "documents_processed": summary.documents_processed if summary else 0
        },
        "insights": [
            {
                "id": ins.id,
                "severity": ins.severity,
                "description": ins.description,
                "supporting_documents": ins.supporting_documents or [],
                "supporting_records": ins.supporting_records or {},
                "confidence": ins.confidence
            } for ins in insights
        ],
        "matches": [
            {
                "id": m.id,
                "match_type": m.match_type,
                "description": m.description,
                "amount": m.amount,
                "status": m.status
            } for m in matches
        ],
        "documents": [
            {
                "id": d.id,
                "name": d.name,
                "category": d.category,
                "processing_status": d.processing_status,
                "created_at": d.created_at.isoformat() if d.created_at else None
            } for d in docs
        ]
    }


@router.get("/{client_id}/tax-summary")
def get_client_tax_summary(
    client_id: str,
    assessment_year: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.organization_id == current_user.organization_id,
        Client.deleted_at.is_(None)
    ).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
        
    ay_val = assessment_year or "2025-26"
    if len(ay_val) == 9: # 2025-2026
        ay_val = f"{ay_val[:4]}-{ay_val[7:]}" # 2025-26
        
    from app.models.models import ClientTaxSummary
    summary = db.query(ClientTaxSummary).filter(
        ClientTaxSummary.client_id == client_id,
        ClientTaxSummary.assessment_year == ay_val
    ).first()
    
    if not summary:
        return {}
    return {
        "total_tds": summary.total_tds,
        "total_reported_income": summary.total_reported_income,
        "interest_income": summary.interest_income,
        "dividend_income": summary.dividend_income,
        "salary_income": summary.salary_income,
        "securities_transactions": summary.securities_transactions,
        "mutual_fund_transactions": summary.mutual_fund_transactions,
        "property_transactions": summary.property_transactions,
        "sft_transactions": summary.sft_transactions,
        "refund_amount": summary.refund_amount,
        "demand_amount": summary.demand_amount,
        "deductor_count": summary.deductor_count,
        "ais_category_count": summary.ais_category_count,
        "documents_processed": summary.documents_processed
    }


@router.get("/{client_id}/tax-insights")
def get_client_tax_insights(
    client_id: str,
    assessment_year: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.organization_id == current_user.organization_id,
        Client.deleted_at.is_(None)
    ).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
        
    ay_val = assessment_year or "2025-26"
    if len(ay_val) == 9: # 2025-2026
        ay_val = f"{ay_val[:4]}-{ay_val[7:]}" # 2025-26
        
    from app.models.models import ClientTaxInsight
    insights = db.query(ClientTaxInsight).filter(
        ClientTaxInsight.client_id == client_id,
        ClientTaxInsight.assessment_year == ay_val
    ).all()
    
    return [
        {
            "id": ins.id,
            "severity": ins.severity,
            "description": ins.description,
            "supporting_documents": ins.supporting_documents or [],
            "confidence": ins.confidence
        } for ins in insights
    ]


@router.get("/{client_id}/itr-profile")
def get_client_itr_profile(
    client_id: str,
    assessment_year: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.organization_id == current_user.organization_id,
        Client.deleted_at.is_(None)
    ).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
        
    ay_val = assessment_year or "2025-26"
    if len(ay_val) == 9:
        ay_val = f"{ay_val[:4]}-{ay_val[7:]}"
        
    from app.services.tax_intelligence import TaxIntelligenceService
    TaxIntelligenceService.recompute(db, client_id, ay_val)

    from app.models.models import ITRProfile
    profile = db.query(ITRProfile).filter(
        ITRProfile.client_id == client_id,
        ITRProfile.assessment_year == ay_val
    ).first()

    if not profile:
        return {
            "pan": client.PAN or "N/A",
            "client_name": client.client_name,
            "assessment_year": ay_val,
            "itr_status": "NOT_STARTED",
            "documents_uploaded": [],
            "data_completeness_score": 0.0,
            "processing_status": "PENDING"
        }

    return {
        "id": profile.id,
        "pan": client.PAN or "N/A",
        "client_name": client.client_name,
        "assessment_year": profile.assessment_year,
        "financial_year": profile.financial_year,
        "itr_status": profile.itr_status,
        "documents_uploaded": profile.documents_uploaded or [],
        "data_completeness_score": profile.data_completeness_score,
        "processing_status": profile.processing_status,
        "confidence": profile.confidence
    }


@router.get("/{client_id}/itr-readiness")
def get_client_itr_readiness(
    client_id: str,
    assessment_year: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.organization_id == current_user.organization_id,
        Client.deleted_at.is_(None)
    ).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
        
    ay_val = assessment_year or "2025-26"
    if len(ay_val) == 9:
        ay_val = f"{ay_val[:4]}-{ay_val[7:]}"

    from app.models.models import ITRReadiness
    readiness = db.query(ITRReadiness).filter(
        ITRReadiness.client_id == client_id,
        ITRReadiness.assessment_year == ay_val
    ).first()

    if not readiness:
        return {
            "readiness_score": 0.0,
            "reasons": [],
            "collected_documents": [],
            "missing_documents": ["Form 26AS", "AIS", "Form 16", "Bank Statement"]
        }

    return {
        "readiness_score": readiness.readiness_score,
        "reasons": readiness.reasons or [],
        "collected_documents": readiness.collected_documents or [],
        "missing_documents": readiness.missing_documents or []
    }


@router.get("/{client_id}/itr-actions")
def get_client_itr_actions(
    client_id: str,
    assessment_year: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.organization_id == current_user.organization_id,
        Client.deleted_at.is_(None)
    ).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
        
    ay_val = assessment_year or "2025-26"
    if len(ay_val) == 9:
        ay_val = f"{ay_val[:4]}-{ay_val[7:]}"

    from app.models.models import ITRActionItem
    actions = db.query(ITRActionItem).filter(
        ITRActionItem.client_id == client_id,
        ITRActionItem.assessment_year == ay_val
    ).all()

    return [
        {
            "id": a.id,
            "action_text": a.action_text,
            "severity": a.severity,
            "reference_document": a.reference_document,
            "status": a.status
        } for a in actions
    ]


@router.get("/{client_id}/itr-verification")
def get_client_itr_verification(
    client_id: str,
    assessment_year: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.organization_id == current_user.organization_id,
        Client.deleted_at.is_(None)
    ).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
        
    ay_val = assessment_year or "2025-26"
    if len(ay_val) == 9:
        ay_val = f"{ay_val[:4]}-{ay_val[7:]}"

    from app.models.models import ITRVerificationResult
    results = db.query(ITRVerificationResult).filter(
        ITRVerificationResult.client_id == client_id,
        ITRVerificationResult.assessment_year == ay_val
    ).all()

    return [
        {
            "id": r.id,
            "verification_type": r.verification_type,
            "description": r.description,
            "status": r.status
        } for r in results
    ]


from app.schemas.workspace import (
    ClientWorkspaceResponse, ClientTaskSchema, ClientTaskCreate,
    ClientNoteSchema, ClientNoteCreate, ClientTimelineSchema, ClientTimelineCreate
)
from app.services.workspace import WorkspaceService
from app.models.models import ClientTask, ClientTimelineEvent, Note
import json

@router.get("/{client_id}/workspace", response_model=ClientWorkspaceResponse)
def get_client_workspace(
    client_id: str,
    assessment_year: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.organization_id == current_user.organization_id,
        Client.deleted_at.is_(None)
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    ay_val = assessment_year or "2025-26"
    try:
        data = WorkspaceService.get_workspace_data(db, client_id, ay_val)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{client_id}/tasks", response_model=ClientTaskSchema)
def create_workspace_task(
    client_id: str,
    payload: ClientTaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.organization_id == current_user.organization_id,
        Client.deleted_at.is_(None)
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
        
    task = ClientTask(
        organization_id=current_user.organization_id,
        client_id=client_id,
        task_name=payload.task_name,
        description=payload.description,
        status=payload.status or "PENDING",
        linked_to=payload.linked_to,
        linked_id=payload.linked_id,
        due_date=payload.due_date
    )
    db.add(task)
    
    # Log timeline event
    evt = ClientTimelineEvent(
        organization_id=current_user.organization_id,
        client_id=client_id,
        event_type="TASK_CREATED",
        title=f"Task Created: {payload.task_name}",
        description=payload.description
    )
    db.add(evt)
    db.commit()
    db.refresh(task)
    return task

@router.put("/{client_id}/tasks/{task_id}", response_model=ClientTaskSchema)
def update_workspace_task(
    client_id: str,
    task_id: str,
    payload: ClientTaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(ClientTask).filter(
        ClientTask.id == task_id,
        ClientTask.client_id == client_id,
        ClientTask.organization_id == current_user.organization_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    old_status = task.status
    task.task_name = payload.task_name
    task.description = payload.description
    if payload.status:
        task.status = payload.status
    task.linked_to = payload.linked_to
    task.linked_id = payload.linked_id
    task.due_date = payload.due_date
    
    # If completed, log timeline
    if payload.status == "COMPLETED" and old_status != "COMPLETED":
        evt = ClientTimelineEvent(
            organization_id=current_user.organization_id,
            client_id=client_id,
            event_type="TASK_COMPLETED",
            title=f"Task Completed: {task.task_name}",
            description=task.description
        )
        db.add(evt)
        
    db.commit()
    db.refresh(task)
    return task

@router.delete("/{client_id}/tasks/{task_id}")
def delete_workspace_task(
    client_id: str,
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(ClientTask).filter(
        ClientTask.id == task_id,
        ClientTask.client_id == client_id,
        ClientTask.organization_id == current_user.organization_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"message": "Task deleted successfully"}

@router.post("/{client_id}/notes", response_model=ClientNoteSchema)
def create_workspace_note(
    client_id: str,
    payload: ClientNoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.organization_id == current_user.organization_id,
        Client.deleted_at.is_(None)
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
        
    note = Note(
        organization_id=current_user.organization_id,
        client_id=client_id,
        title=payload.title,
        content=payload.content,
        created_by=current_user.id,
        tags=payload.tags,
        is_pinned=payload.is_pinned or False,
        attachments_json=json.dumps(payload.attachments) if payload.attachments else None,
        mentions_json=json.dumps(payload.mentions) if payload.mentions else None
    )
    db.add(note)
    
    evt = ClientTimelineEvent(
        organization_id=current_user.organization_id,
        client_id=client_id,
        event_type="NOTE_ADDED",
        title=f"Note Drafted: {payload.title}",
        description=payload.content[:100] + "..." if len(payload.content) > 100 else payload.content
    )
    db.add(evt)
    db.commit()
    db.refresh(note)
    
    # Return structure mapped
    return {
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "created_by": note.created_by,
        "tags": note.tags,
        "is_pinned": note.is_pinned,
        "attachments": payload.attachments or [],
        "mentions": payload.mentions or [],
        "created_at": note.created_at,
        "updated_at": note.updated_at
    }

@router.put("/{client_id}/notes/{note_id}", response_model=ClientNoteSchema)
def update_workspace_note(
    client_id: str,
    note_id: str,
    payload: ClientNoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.client_id == client_id,
        Note.organization_id == current_user.organization_id,
        Note.deleted_at.is_(None)
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
        
    note.title = payload.title
    note.content = payload.content
    note.tags = payload.tags
    if payload.is_pinned is not None:
        note.is_pinned = payload.is_pinned
    note.attachments_json = json.dumps(payload.attachments) if payload.attachments else None
    note.mentions_json = json.dumps(payload.mentions) if payload.mentions else None
    
    db.commit()
    db.refresh(note)
    return {
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "created_by": note.created_by,
        "tags": note.tags,
        "is_pinned": note.is_pinned,
        "attachments": payload.attachments or [],
        "mentions": payload.mentions or [],
        "created_at": note.created_at,
        "updated_at": note.updated_at
    }

@router.delete("/{client_id}/notes/{note_id}")
def delete_workspace_note(
    client_id: str,
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.client_id == client_id,
        Note.organization_id == current_user.organization_id,
        Note.deleted_at.is_(None)
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    note.deleted_at = datetime.utcnow()
    db.commit()
    return {"message": "Note deleted successfully"}

@router.post("/{client_id}/timeline", response_model=ClientTimelineSchema)
def create_timeline_event(
    client_id: str,
    payload: ClientTimelineCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.organization_id == current_user.organization_id,
        Client.deleted_at.is_(None)
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
        
    evt = ClientTimelineEvent(
        organization_id=current_user.organization_id,
        client_id=client_id,
        event_type=payload.event_type,
        title=payload.title,
        description=payload.description
    )
    db.add(evt)
    db.commit()
    db.refresh(evt)
    return evt
