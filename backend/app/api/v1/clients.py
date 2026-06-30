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
