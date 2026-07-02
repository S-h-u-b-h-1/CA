from sqlalchemy.orm import Session
from datetime import datetime
from app.models.models import Notification

VALID_TRANSITIONS = {
    "UNREAD": {"READ", "ARCHIVED"},
    "READ": {"ARCHIVED"},
    "ARCHIVED": set(),
}


def create_notification(
    db: Session,
    organization_id: str,
    source: str,
    title: str,
    body: str = None,
    client_id: str = None,
    related_suggestion_id: str = None,
    related_government_update_id: str = None,
    related_compliance_task_id: str = None,
) -> Notification:
    notification = Notification(
        organization_id=organization_id,
        client_id=client_id,
        source=source,
        title=title,
        body=body,
        related_suggestion_id=related_suggestion_id,
        related_government_update_id=related_government_update_id,
        related_compliance_task_id=related_compliance_task_id,
        status="UNREAD",
    )
    db.add(notification)
    return notification


def transition_status(db: Session, notification: Notification, new_status: str) -> Notification:
    allowed = VALID_TRANSITIONS.get(notification.status, set())
    if new_status not in allowed:
        raise ValueError(f"Cannot transition notification from {notification.status} to {new_status} (allowed: {sorted(allowed) or 'none — terminal state'})")

    notification.status = new_status
    now = datetime.utcnow()
    if new_status == "READ":
        notification.read_at = now
    elif new_status == "ARCHIVED":
        notification.archived_at = now

    db.commit()
    db.refresh(notification)
    return notification
