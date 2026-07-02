from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.models.models import (
    ComplianceSource, User, GovernmentSource, 
    GovernmentUpdate, GovernmentUpdateVersion, ConnectorSyncLog
)
from app.schemas.schemas import ComplianceSourceCreate, ComplianceSourceUpdate, ComplianceSourceResponse
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/sources", response_model=List[ComplianceSourceResponse])
def list_compliance_sources(
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(ComplianceSource).filter(ComplianceSource.deleted_at.is_(None))
    if category:
        query = query.filter(ComplianceSource.category == category)
    return query.offset(skip).limit(limit).all()


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


# ==============================================================================
# PHASE 3 ROUTERS: GOVERNMENT KNOWLEDGE ACQUISITION PLATFORM
# ==============================================================================

from app.services.connectors.registry import ConnectorRegistry
from app.services.scheduler import ConnectorScheduler

@router.get("/connectors")
def list_connectors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Initialize schedules
    ConnectorScheduler.initialize_schedules(db)
    
    # Query database stats for all connectors
    sources = db.query(GovernmentSource).filter(GovernmentSource.status == "ACTIVE").all()
    
    results = []
    for conn in ConnectorRegistry.list_all():
        src = next((s for s in sources if s.source_name == conn.get_name()), None)
        if not src:
            src = GovernmentSource(
                source_name=conn.get_name(),
                category=conn.get_category(),
                official_url=conn.get_official_url(),
                requires_auth=conn.requires_auth(),
                sync_frequency=conn.schedule(),
                rate_limits=conn.get_rate_limits(),
                connector_status="RUNNING"
            )
            db.add(src)
            db.commit()
            db.refresh(src)
        
        results.append({
            "id": src.id,
            "connector_name": src.source_name,
            "authority": conn.get_authority(),
            "category": src.category,
            "status": src.connector_status,
            "health": src.health,
            "last_success": src.last_success,
            "last_failure": src.last_failure,
            "average_response_time": src.average_response_time,
            "retry_count": src.retry_count,
            "total_documents_count": src.total_documents_count,
            "version_count": src.version_count,
            "rate_limits": src.rate_limits,
            "auth_requirements": src.auth_requirements,
            "official_url": src.official_url
        })
    return results


@router.post("/connectors/{source_id}/sync")
def sync_connector(
    source_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    source = db.query(GovernmentSource).filter(GovernmentSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Compliance source connector not found")

    background_tasks.add_task(ConnectorScheduler.trigger_sync, source.source_name, db)
    return {"status": "success", "message": f"Sync task for '{source.source_name}' triggered successfully."}


@router.post("/connectors/{source_id}/pause")
def pause_connector(
    source_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    source = db.query(GovernmentSource).filter(GovernmentSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Compliance source connector not found")

    ConnectorScheduler.pause_schedule(source.source_name, db)
    return {"status": "success", "message": f"Sync for '{source.source_name}' is paused."}


@router.post("/connectors/{source_id}/resume")
def resume_connector(
    source_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    source = db.query(GovernmentSource).filter(GovernmentSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Compliance source connector not found")

    ConnectorScheduler.resume_schedule(source.source_name, db)
    return {"status": "success", "message": f"Sync for '{source.source_name}' is resumed."}


@router.get("/connectors/{source_id}/logs")
def get_connector_logs(
    source_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logs = db.query(ConnectorSyncLog).filter(
        ConnectorSyncLog.source_id == source_id
    ).order_by(ConnectorSyncLog.sync_time.desc()).limit(50).all()
    return logs


@router.get("/connectors/documents")
def search_government_documents(
    q: Optional[str] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query_builder = db.query(GovernmentUpdate).filter(GovernmentUpdate.status == "ACTIVE")
    if q:
        query_builder = query_builder.filter(
            or_(
                GovernmentUpdate.title.ilike(f"%{q}%"),
                GovernmentUpdate.document_number.ilike(f"%{q}%"),
                GovernmentUpdate.summary.ilike(f"%{q}%")
            )
        )
    if category:
        query_builder = query_builder.filter(GovernmentUpdate.issuing_authority == category)
    
    docs = query_builder.order_by(GovernmentUpdate.issue_date.desc()).limit(100).all()
    return docs


@router.get("/connectors/documents/{doc_id}/versions")
def get_document_versions(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(GovernmentUpdate).filter(GovernmentUpdate.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Government document not found")

    versions = db.query(GovernmentUpdateVersion).filter(
        GovernmentUpdateVersion.government_update_id == doc_id
    ).order_by(GovernmentUpdateVersion.version_number.asc()).all()

    return {
        "document": doc,
        "versions": [
            {
                "id": v.id,
                "version_number": v.version_number,
                "checksum": v.checksum,
                "added_paragraphs": v.added_paragraphs,
                "removed_paragraphs": v.removed_paragraphs,
                "changed_sections": v.changed_sections,
                "structured_differences": v.structured_differences,
                "created_at": v.created_at,
                "markdown_content": v.markdown_content
            }
            for v in versions
        ]
    }


@router.delete("/connectors/documents/{doc_id}")
def archive_government_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Archive (soft-remove) an erroneous or duplicate ingested update - e.g.
    a stale record left over from a since-fixed connector bug. Does not hard
    delete: sets status to ARCHIVED so it drops out of the active document
    registry/search while remaining available for audit."""
    if current_user.role not in ["SUPER_ADMIN", "FIRM_ADMIN", "PARTNER"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    doc = db.query(GovernmentUpdate).filter(GovernmentUpdate.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Government document not found")

    doc.status = "ARCHIVED"
    db.commit()
    return {"status": "success", "message": f"Document {doc_id} archived."}


from app.schemas.compliance_schemas import (
    ComplianceProfileCreate, ComplianceProfileSchema, ComplianceTaskCreate,
    ComplianceTaskSchema, ComplianceHistorySchema, ComplianceAlertSchema,
    ComplianceDashboardResponse
)
from app.services.compliance_service import ComplianceService
from app.models.models import ComplianceProfile, ComplianceTask, ComplianceHistory, ComplianceAlert, Client

@router.get("/dashboard", response_model=ComplianceDashboardResponse)
def get_compliance_dashboard_view(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        data = ComplianceService.get_dashboard_data(db, current_user.organization_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clients/{client_id}")
def get_client_compliance_profile(
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
        raise HTTPException(status_code=404, detail="Client not found")

    profiles = db.query(ComplianceProfile).filter(ComplianceProfile.client_id == client_id).all()
    tasks = db.query(ComplianceTask).filter(ComplianceTask.client_id == client_id).all()
    history = db.query(ComplianceHistory).filter(ComplianceHistory.client_id == client_id).all()
    health_score, health_val = ComplianceService.compute_health_score(db, client_id)

    return {
        "client_name": client.client_name,
        "health_score": health_score,
        "health_score_value": health_val,
        "profiles": profiles,
        "tasks": tasks,
        "history": history
    }

@router.post("/profile", response_model=ComplianceProfileSchema)
def create_client_compliance_profile(
    payload: ComplianceProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(
        Client.id == payload.client_id,
        Client.organization_id == current_user.organization_id,
        Client.deleted_at.is_(None)
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    profile = ComplianceProfile(
        organization_id=current_user.organization_id,
        client_id=payload.client_id,
        compliance_type=payload.compliance_type,
        registration_number=payload.registration_number,
        frequency=payload.frequency or "MONTHLY",
        due_day=payload.due_day or 20,
        assigned_manager=payload.assigned_manager,
        assigned_partner=payload.assigned_partner,
        risk_level=payload.risk_level or "LOW"
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    
    # Generate tasks
    ComplianceService.generate_recurring_tasks(db, profile)
    return profile

@router.get("/calendar", response_model=List[ComplianceTaskSchema])
def get_compliance_calendar_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tasks = db.query(ComplianceTask).filter(
        ComplianceTask.organization_id == current_user.organization_id
    ).order_by(ComplianceTask.due_date.asc()).all()
    return tasks

@router.post("/task", response_model=ComplianceTaskSchema)
def create_manual_compliance_task(
    payload: ComplianceTaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = ComplianceTask(
        organization_id=current_user.organization_id,
        client_id=payload.client_id,
        profile_id=payload.profile_id,
        task_name=payload.task_name,
        due_date=payload.due_date,
        priority=payload.priority or "MEDIUM",
        status=payload.status or "PENDING",
        assigned_user_id=payload.assigned_user_id,
        notes=payload.notes
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

@router.put("/task/{id}", response_model=ComplianceTaskSchema)
def update_compliance_task_route(
    id: str,
    payload: ComplianceTaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(ComplianceTask).filter(
        ComplianceTask.id == id,
        ComplianceTask.organization_id == current_user.organization_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Compliance task not found")
        
    old_status = task.status
    task.task_name = payload.task_name
    task.due_date = payload.due_date
    task.priority = payload.priority or "MEDIUM"
    if payload.status:
        task.status = payload.status
    task.assigned_user_id = payload.assigned_user_id
    task.notes = payload.notes
    
    db.commit()
    
    # If completed, route to complete helper
    if payload.status == "COMPLETED" and old_status != "COMPLETED":
        ComplianceService.complete_task(db, id, None, payload.notes)
        
    db.refresh(task)
    return task

@router.get("/alerts", response_model=List[ComplianceAlertSchema])
def get_compliance_alerts_list(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Scan daily alerts
    ComplianceService.generate_daily_alerts(db, current_user.organization_id)
    alerts = db.query(ComplianceAlert).filter(
        ComplianceAlert.organization_id == current_user.organization_id,
        ComplianceAlert.is_resolved == False
    ).all()
    return alerts
