"""Intelligence Engine orchestrator.

Reconciliation, not blind regeneration: every rule candidate carries a stable
dedup_key (rule_key + client_id + a rule-specific suffix identifying the exact
triggering record). Re-running the engine:
  - creates a Suggestion for a dedup_key seen for the first time
  - refreshes title/evidence/severity on an existing NEW/ACKNOWLEDGED/IN_PROGRESS
    Suggestion so it stays current without resetting the CA's progress on it
  - leaves RESOLVED/DISMISSED suggestions alone even if the same dedup_key
    reappears (no resurrecting dismissed suggestions)
  - auto-resolves any open suggestion whose dedup_key did NOT appear in this
    run, because that means the underlying condition cleared (e.g. the task
    that was overdue got completed)

This keeps suggestions as lifecycle objects per the architecture requirement,
rather than ephemeral, disappear-on-next-request rows.
"""
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from app.models.models import Client, Suggestion, SuggestionEvidence, AuditLog
from app.services.intelligence.core import SuggestionCandidate, derive_confidence
from app.services.intelligence import (
    rules_tax, rules_compliance, rules_documents, rules_authority_updates, rules_research, rules_client_health,
)

ACTIVE_STATUSES = ("NEW", "ACKNOWLEDGED", "IN_PROGRESS")

# Strict linear lifecycle: NEW -> ACKNOWLEDGED -> IN_PROGRESS -> RESOLVED.
# DISMISSED is reachable from any non-terminal state. No skipping stages.
VALID_TRANSITIONS = {
    "NEW": {"ACKNOWLEDGED", "DISMISSED"},
    "ACKNOWLEDGED": {"IN_PROGRESS", "DISMISSED"},
    "IN_PROGRESS": {"RESOLVED", "DISMISSED"},
    "RESOLVED": set(),
    "DISMISSED": set(),
}


def transition_status(db: Session, suggestion: Suggestion, new_status: str, user_id: str, reason: str = None) -> Suggestion:
    allowed = VALID_TRANSITIONS.get(suggestion.status, set())
    if new_status not in allowed:
        raise ValueError(f"Cannot transition suggestion from {suggestion.status} to {new_status} (allowed: {sorted(allowed) or 'none — terminal state'})")

    old_status = suggestion.status
    suggestion.status = new_status
    now = datetime.utcnow()
    if new_status == "ACKNOWLEDGED":
        suggestion.acknowledged_at = now
    elif new_status == "IN_PROGRESS":
        suggestion.in_progress_at = now
    elif new_status == "RESOLVED":
        suggestion.resolved_at = now
    elif new_status == "DISMISSED":
        suggestion.dismissed_at = now
        suggestion.dismissed_by = user_id
        suggestion.dismissed_reason = reason

    db.add(AuditLog(
        organization_id=suggestion.organization_id, user_id=user_id,
        action="SUGGESTION_STATUS_CHANGE", entity_type="Suggestion", entity_id=suggestion.id,
        details=f"{old_status} -> {new_status}" + (f" ({reason})" if reason else ""),
    ))
    db.commit()
    db.refresh(suggestion)
    return suggestion


def _dedup_key(candidate: SuggestionCandidate, client_id: str) -> str:
    return f"{candidate.rule_key}:{client_id}:{candidate.dedup_suffix}"[:255]


def generate_for_client(db: Session, client: Client) -> dict:
    candidates: List[SuggestionCandidate] = []
    candidates += rules_tax.evaluate(db, client)
    candidates += rules_compliance.evaluate(db, client)
    candidates += rules_documents.evaluate(db, client)
    candidates += rules_authority_updates.evaluate(db, client)
    candidates += rules_research.evaluate(db, client)
    candidates += rules_client_health.evaluate(db, client, candidates)

    seen_keys = set()
    generated, refreshed = 0, 0

    for candidate in candidates:
        dedup_key = _dedup_key(candidate, client.id)
        seen_keys.add(dedup_key)

        confidence, confidence_reason = (
            (candidate.confidence_override, candidate.confidence_reason_override)
            if candidate.confidence_override
            else derive_confidence(candidate.evidence)
        )

        existing = db.query(Suggestion).filter(
            Suggestion.organization_id == client.organization_id,
            Suggestion.dedup_key == dedup_key,
        ).first()

        if existing and existing.status not in ACTIVE_STATUSES:
            continue  # RESOLVED/DISMISSED — don't resurrect

        if existing:
            existing.title = candidate.title
            existing.severity = candidate.severity
            existing.confidence = confidence
            existing.confidence_reason = confidence_reason
            existing.explanation = candidate.explanation
            existing.recommendation = candidate.recommendation
            existing.related_document_ids = candidate.related_document_ids or None
            existing.related_government_update_id = candidate.related_government_update_id
            existing.generated_at = datetime.utcnow()
            db.query(SuggestionEvidence).filter(SuggestionEvidence.suggestion_id == existing.id).delete()
            for ev in candidate.evidence:
                db.add(SuggestionEvidence(suggestion_id=existing.id, evidence_type=ev.evidence_type, reference_id=ev.reference_id, summary=ev.summary))
            refreshed += 1
        else:
            row = Suggestion(
                organization_id=client.organization_id,
                client_id=client.id,
                rule_key=candidate.rule_key,
                category=candidate.category,
                title=candidate.title,
                severity=candidate.severity,
                confidence=confidence,
                confidence_reason=confidence_reason,
                explanation=candidate.explanation,
                recommendation=candidate.recommendation,
                related_document_ids=candidate.related_document_ids or None,
                related_government_update_id=candidate.related_government_update_id,
                dedup_key=dedup_key,
                status="NEW",
            )
            db.add(row)
            db.flush()  # assign row.id before attaching evidence
            for ev in candidate.evidence:
                db.add(SuggestionEvidence(suggestion_id=row.id, evidence_type=ev.evidence_type, reference_id=ev.reference_id, summary=ev.summary))
            generated += 1

    stale = db.query(Suggestion).filter(
        Suggestion.organization_id == client.organization_id,
        Suggestion.client_id == client.id,
        Suggestion.status.in_(ACTIVE_STATUSES),
    ).all()
    resolved = 0
    for row in stale:
        if row.dedup_key not in seen_keys:
            row.status = "RESOLVED"
            row.resolved_at = datetime.utcnow()
            db.add(AuditLog(
                organization_id=client.organization_id, user_id=None,
                action="SUGGESTION_AUTO_RESOLVED", entity_type="Suggestion", entity_id=row.id,
                details=f"Auto-resolved: underlying condition for rule '{row.rule_key}' no longer holds.",
            ))
            resolved += 1

    db.commit()
    return {"client_id": client.id, "generated": generated, "refreshed": refreshed, "resolved": resolved, "rules_evaluated": len(candidates)}


def generate_for_organization(db: Session, organization_id: str) -> dict:
    clients = db.query(Client).filter(Client.organization_id == organization_id, Client.deleted_at.is_(None)).all()
    totals = {"clients_processed": 0, "generated": 0, "refreshed": 0, "resolved": 0}
    for client in clients:
        result = generate_for_client(db, client)
        totals["clients_processed"] += 1
        totals["generated"] += result["generated"]
        totals["refreshed"] += result["refreshed"]
        totals["resolved"] += result["resolved"]
    return totals
