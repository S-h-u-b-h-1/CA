from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.models import User, Citation, CitationVerification
from app.api.deps import get_current_user
from app.services.citation import CitationEngine
from app.services.verification import SourceVerificationEngine
from pydantic import BaseModel

router = APIRouter()

# Schema inputs for Citations
class CitationCreatePayload(BaseModel):
    source_type: str
    source_document_id: Optional[str] = None
    government_update_id: Optional[str] = None
    client_id: Optional[str] = None
    page_number: Optional[int] = None
    paragraph_number: Optional[int] = None
    section_reference: Optional[str] = None
    act_reference: Optional[str] = None
    rule_reference: Optional[str] = None
    circular_number: Optional[str] = None
    notification_number: Optional[str] = None
    quote_text: Optional[str] = None
    source_url: Optional[str] = None
    target_entity_id: Optional[str] = None
    text_reference: Optional[str] = None

class VerifyPayload(BaseModel):
    citation_id: str

@router.get("")
def list_citations(
    source_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Citation).filter(
        Citation.organization_id == current_user.organization_id,
        Citation.status == "ACTIVE"
    )
    if source_type:
        query = query.filter(Citation.source_type == source_type)
    return query.all()

@router.post("")
def create_citation(
    payload: CitationCreatePayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        citation = CitationEngine.create_citation(
            db=db,
            organization_id=current_user.organization_id,
            source_type=payload.source_type,
            source_document_id=payload.source_document_id,
            government_update_id=payload.government_update_id,
            client_id=payload.client_id,
            page_number=payload.page_number,
            paragraph_number=payload.paragraph_number,
            section_reference=payload.section_reference,
            act_reference=payload.act_reference,
            rule_reference=payload.rule_reference,
            circular_number=payload.circular_number,
            notification_number=payload.notification_number,
            quote_text=payload.quote_text,
            source_url=payload.source_url,
            target_entity_id=payload.target_entity_id,
            text_reference=payload.text_reference or ""
        )
        return citation
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create citation: {str(e)}"
        )

@router.get("/search")
def search_citations_endpoint(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    like_query = f"%{q}%"
    citations = db.query(Citation).filter(
        Citation.organization_id == current_user.organization_id,
        Citation.status == "ACTIVE",
        Citation.quote_text.ilike(like_query)
    ).limit(20).all()
    return citations

@router.get("/document/{document_id}")
def get_citations_by_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    citations = db.query(Citation).filter(
        Citation.organization_id == current_user.organization_id,
        Citation.source_document_id == document_id,
        Citation.status == "ACTIVE"
    ).all()
    return citations

@router.get("/government/{government_update_id}")
def get_citations_by_gov_update(
    government_update_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    citations = db.query(Citation).filter(
        Citation.organization_id == current_user.organization_id,
        Citation.government_update_id == government_update_id,
        Citation.status == "ACTIVE"
    ).all()
    return citations

@router.get("/client/{client_id}")
def get_citations_by_client(
    client_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    citations = db.query(Citation).filter(
        Citation.organization_id == current_user.organization_id,
        Citation.client_id == client_id,
        Citation.status == "ACTIVE"
    ).all()
    return citations

@router.get("/{citation_id}")
def get_citation(
    citation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    citation = db.query(Citation).filter(
        Citation.id == citation_id,
        Citation.organization_id == current_user.organization_id,
        Citation.status == "ACTIVE"
    ).first()
    if not citation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Citation not found"
        )
    return citation

@router.post("/verify")
def verify_citation_endpoint(
    payload: VerifyPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        result = SourceVerificationEngine.verify_citation(
            db=db,
            organization_id=current_user.organization_id,
            citation_id=payload.citation_id
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {str(e)}"
        )
