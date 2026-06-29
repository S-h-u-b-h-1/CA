from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.models.models import User, ExternalSystem, IntegrationToken, SyncLog, AuditLog
from app.schemas.schemas import AKKCConnect, AKKCStatusResponse, SyncResponse
from app.api.deps import get_current_user
from app.services.akkc import AKKCConnector

router = APIRouter()

@router.post("/akkc/connect", response_model=AKKCStatusResponse)
def connect_akkc(
    payload: AKKCConnect,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify role
    if current_user.role not in ["SUPER_ADMIN", "FIRM_ADMIN", "PARTNER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators or partners can configure integrations"
        )

    connector = AKKCConnector(base_url=payload.base_url, api_key=payload.api_key)
    if not connector.test_connection():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not establish connection to AKKC platform"
        )

    # Upsert ExternalSystem
    system = db.query(ExternalSystem).filter(
        ExternalSystem.organization_id == current_user.organization_id,
        ExternalSystem.name == "AKKC",
        ExternalSystem.deleted_at.is_(None)
    ).first()

    if not system:
        system = ExternalSystem(
            organization_id=current_user.organization_id,
            name="AKKC",
            base_url=payload.base_url,
            status="ACTIVE"
        )
        db.add(system)
        db.flush()

    # Save Integration Token
    token = db.query(IntegrationToken).filter(
        IntegrationToken.organization_id == current_user.organization_id,
        IntegrationToken.external_system_id == system.id,
        IntegrationToken.deleted_at.is_(None)
    ).first()

    if not token:
        token = IntegrationToken(
            organization_id=current_user.organization_id,
            external_system_id=system.id,
            token_type="API_KEY",
            access_token=payload.api_key
        )
        db.add(token)
    else:
        token.access_token = payload.api_key
        token.updated_at = datetime.utcnow()
    
    # Audit log
    audit = AuditLog(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="INTEGRATION_CONNECT",
        entity_type="EXTERNAL_SYSTEM",
        entity_id=system.id,
        details=f"Connected AKKC platform at {payload.base_url}"
    )
    db.add(audit)
    db.commit()

    return {
        "connected": True,
        "system_name": "AKKC",
        "base_url": system.base_url,
        "last_synced_at": None
    }


@router.get("/akkc/status", response_model=AKKCStatusResponse)
def get_akkc_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    system = db.query(ExternalSystem).filter(
        ExternalSystem.organization_id == current_user.organization_id,
        ExternalSystem.name == "AKKC",
        ExternalSystem.deleted_at.is_(None)
    ).first()

    if not system or system.status != "ACTIVE":
        return {
            "connected": False,
            "system_name": "AKKC",
            "base_url": None,
            "last_synced_at": None
        }

    # Fetch last sync timestamp
    last_sync = db.query(SyncLog).filter(
        SyncLog.organization_id == current_user.organization_id,
        SyncLog.external_system_id == system.id,
        SyncLog.sync_status == "SUCCESS"
    ).order_by(SyncLog.created_at.desc()).first()

    last_synced_at = last_sync.created_at if last_sync else None

    return {
        "connected": True,
        "system_name": "AKKC",
        "base_url": system.base_url,
        "last_synced_at": last_synced_at
    }


@router.post("/akkc/sync/clients", response_model=SyncResponse)
def sync_akkc_clients(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    system = db.query(ExternalSystem).filter(
        ExternalSystem.organization_id == current_user.organization_id,
        ExternalSystem.name == "AKKC",
        ExternalSystem.status == "ACTIVE",
        ExternalSystem.deleted_at.is_(None)
    ).first()

    if not system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AKKC platform not connected. Please connect first."
        )

    token = db.query(IntegrationToken).filter(
        IntegrationToken.organization_id == current_user.organization_id,
        IntegrationToken.external_system_id == system.id,
        IntegrationToken.deleted_at.is_(None)
    ).first()

    try:
        connector = AKKCConnector(base_url=system.base_url, api_key=token.access_token if token else "")
        count = connector.sync_clients(db, current_user.organization_id, system.id)
        
        # Log audit
        audit = AuditLog(
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            action="INTEGRATION_SYNC_CLIENTS",
            entity_type="EXTERNAL_SYSTEM",
            entity_id=system.id,
            details=f"Synced {count} clients from AKKC"
        )
        db.add(audit)
        db.commit()

        return {
            "status": "success",
            "synced_count": count
        }
    except Exception as e:
        # Log failure
        fail_log = SyncLog(
            organization_id=current_user.organization_id,
            external_system_id=system.id,
            entity_type="CLIENTS",
            sync_status="FAILED",
            error_message=str(e)
        )
        db.add(fail_log)
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {str(e)}"
        )


@router.post("/akkc/sync/tasks", response_model=SyncResponse)
def sync_akkc_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    system = db.query(ExternalSystem).filter(
        ExternalSystem.organization_id == current_user.organization_id,
        ExternalSystem.name == "AKKC",
        ExternalSystem.status == "ACTIVE",
        ExternalSystem.deleted_at.is_(None)
    ).first()

    if not system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AKKC platform not connected."
        )

    try:
        connector = AKKCConnector(base_url=system.base_url)
        count = connector.sync_tasks(db, current_user.organization_id, system.id)
        return {
            "status": "success",
            "synced_count": count
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {str(e)}"
        )


@router.post("/akkc/sync/bills", response_model=SyncResponse)
def sync_akkc_bills(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    system = db.query(ExternalSystem).filter(
        ExternalSystem.organization_id == current_user.organization_id,
        ExternalSystem.name == "AKKC",
        ExternalSystem.status == "ACTIVE",
        ExternalSystem.deleted_at.is_(None)
    ).first()

    if not system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AKKC platform not connected."
        )

    try:
        connector = AKKCConnector(base_url=system.base_url)
        count = connector.sync_bills(db, current_user.organization_id, system.id)
        return {
            "status": "success",
            "synced_count": count
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {str(e)}"
        )
