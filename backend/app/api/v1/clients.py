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
