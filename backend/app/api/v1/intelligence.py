from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.core.database import get_db
from app.models.models import Client, Suggestion
from app.schemas.intelligence_schemas import (
    SuggestionSchema, SuggestionStatusUpdate, IntelligenceDashboardResponse, IntelligenceRuleInfo, RegenerateResponse,
)
from app.services.intelligence import engine
from app.services.intelligence.registry import list_rules
from app.api.deps import get_current_user
from app.models.models import User

router = APIRouter()


def _client_or_404(db: Session, client_id: str, organization_id: str) -> Client:
    client = db.query(Client).filter(
        Client.id == client_id, Client.organization_id == organization_id, Client.deleted_at.is_(None)
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.get("/rules", response_model=List[IntelligenceRuleInfo])
def get_rule_registry(current_user: User = Depends(get_current_user)):
    return list_rules()


@router.post("/regenerate/{client_id}", response_model=RegenerateResponse)
def regenerate_for_client(client_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    client = _client_or_404(db, client_id, current_user.organization_id)
    result = engine.generate_for_client(db, client)
    return result


@router.post("/regenerate")
def regenerate_for_organization(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return engine.generate_for_organization(db, current_user.organization_id)


@router.get("/dashboard", response_model=IntelligenceDashboardResponse)
def get_intelligence_dashboard(
    category: Optional[str] = None,
    client_id: Optional[str] = None,
    severity: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Suggestion).options(joinedload(Suggestion.evidence)).filter(
        Suggestion.organization_id == current_user.organization_id
    )
    if status_filter:
        query = query.filter(Suggestion.status == status_filter)
    else:
        query = query.filter(Suggestion.status.in_(engine.ACTIVE_STATUSES))
    if category:
        query = query.filter(Suggestion.category == category)
    if client_id:
        query = query.filter(Suggestion.client_id == client_id)
    if severity:
        query = query.filter(Suggestion.severity == severity)

    rows = query.order_by(Suggestion.generated_at.desc()).all()

    client_names = {c.id: c.client_name for c in db.query(Client).filter(Client.organization_id == current_user.organization_id).all()}
    by_category: dict = {}
    critical = high = medium = low = 0
    for r in rows:
        by_category[r.category] = by_category.get(r.category, 0) + 1
        if r.severity == "CRITICAL":
            critical += 1
        elif r.severity == "HIGH":
            high += 1
        elif r.severity == "MEDIUM":
            medium += 1
        elif r.severity == "LOW":
            low += 1

    suggestions = []
    for r in rows:
        s = SuggestionSchema.model_validate(r)
        s.client_name = client_names.get(r.client_id)
        suggestions.append(s)

    return IntelligenceDashboardResponse(
        total_open=len(rows), critical_count=critical, high_count=high, medium_count=medium, low_count=low,
        by_category=by_category, suggestions=suggestions,
    )


@router.get("/clients/{client_id}", response_model=List[SuggestionSchema])
def get_client_suggestions(client_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    client = _client_or_404(db, client_id, current_user.organization_id)
    rows = (
        db.query(Suggestion)
        .options(joinedload(Suggestion.evidence))
        .filter(Suggestion.organization_id == current_user.organization_id, Suggestion.client_id == client.id)
        .order_by(Suggestion.generated_at.desc())
        .all()
    )
    return rows


def _suggestion_or_404(db: Session, suggestion_id: str, organization_id: str) -> Suggestion:
    row = db.query(Suggestion).filter(Suggestion.id == suggestion_id, Suggestion.organization_id == organization_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return row


@router.put("/{suggestion_id}/status", response_model=SuggestionSchema)
def update_suggestion_status(
    suggestion_id: str, payload: SuggestionStatusUpdate,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    row = _suggestion_or_404(db, suggestion_id, current_user.organization_id)
    try:
        updated = engine.transition_status(db, row, payload.status, current_user.id, payload.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return updated
