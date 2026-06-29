from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.models.models import ComplianceSource, User
from app.schemas.schemas import ComplianceSourceCreate, ComplianceSourceUpdate, ComplianceSourceResponse
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/sources", response_model=List[ComplianceSourceResponse])
def list_compliance_sources(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(ComplianceSource).filter(ComplianceSource.deleted_at.is_(None))
    if category:
        query = query.filter(ComplianceSource.category == category)
    return query.all()


@router.post("/sources", response_model=ComplianceSourceResponse, status_code=status.HTTP_201_CREATED)
def create_compliance_source(
    payload: ComplianceSourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Only administrative users should be able to alter official compliance sources
    if current_user.role not in ["SUPER_ADMIN", "FIRM_ADMIN", "PARTNER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators or partners can register new compliance sources"
        )

    source = ComplianceSource(
        source_name=payload.source_name,
        category=payload.category,
        official_url=payload.official_url,
        access_type=payload.access_type,
        requires_auth=payload.requires_auth,
        update_frequency=payload.update_frequency,
        status="ACTIVE",
        notes=payload.notes
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.put("/sources/{source_id}", response_model=ComplianceSourceResponse)
def update_compliance_source(
    source_id: str,
    payload: ComplianceSourceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in ["SUPER_ADMIN", "FIRM_ADMIN", "PARTNER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators or partners can update compliance sources"
        )

    source = db.query(ComplianceSource).filter(
        ComplianceSource.id == source_id,
        ComplianceSource.deleted_at.is_(None)
    ).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compliance source not found"
        )

    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(source, field, value)

    db.commit()
    db.refresh(source)
    return source


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_compliance_source(
    source_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in ["SUPER_ADMIN", "FIRM_ADMIN", "PARTNER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators or partners can delete compliance sources"
        )

    source = db.query(ComplianceSource).filter(
        ComplianceSource.id == source_id,
        ComplianceSource.deleted_at.is_(None)
    ).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compliance source not found"
        )

    # Soft delete
    source.deleted_at = datetime.utcnow()
    source.status = "INACTIVE"
    db.commit()
    return None
