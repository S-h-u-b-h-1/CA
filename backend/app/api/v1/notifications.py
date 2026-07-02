from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.models import Notification, Client, User
from app.schemas.notification_schemas import NotificationSchema, NotificationStatusUpdate
from app.services import notification_service
from app.api.deps import get_current_user

router = APIRouter()


@router.get("", response_model=List[NotificationSchema])
def list_notifications(
    status_filter: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Notification).filter(Notification.organization_id == current_user.organization_id)
    if status_filter:
        query = query.filter(Notification.status == status_filter)
    else:
        query = query.filter(Notification.status != "ARCHIVED")
    rows = query.order_by(Notification.created_at.desc()).limit(limit).all()

    client_names = {c.id: c.client_name for c in db.query(Client).filter(Client.organization_id == current_user.organization_id).all()}
    out = []
    for r in rows:
        schema = NotificationSchema.model_validate(r)
        schema.client_name = client_names.get(r.client_id)
        out.append(schema)
    return out


@router.get("/unread-count")
def get_unread_count(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = db.query(Notification).filter(
        Notification.organization_id == current_user.organization_id,
        Notification.status == "UNREAD",
    ).count()
    return {"unread_count": count}


@router.put("/{notification_id}/status", response_model=NotificationSchema)
def update_notification_status(
    notification_id: str, payload: NotificationStatusUpdate,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    notification = db.query(Notification).filter(
        Notification.id == notification_id, Notification.organization_id == current_user.organization_id
    ).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    try:
        updated = notification_service.transition_status(db, notification, payload.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return updated
