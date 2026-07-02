"""Compliance Rules — built on the Compliance Engine's own tables (ComplianceProfile,
ComplianceTask). That subsystem already enforces organization/client scoping at the
API layer, not inside ComplianceService itself, so every query here explicitly
filters by organization_id + client_id rather than relying on shared helpers.
"""
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session
from app.models.models import Client, ComplianceProfile, ComplianceTask
from app.services.intelligence.core import EvidenceItem, SuggestionCandidate


def evaluate(db: Session, client: Client) -> List[SuggestionCandidate]:
    out: List[SuggestionCandidate] = []
    now = datetime.utcnow()

    profiles = db.query(ComplianceProfile).filter(
        ComplianceProfile.organization_id == client.organization_id,
        ComplianceProfile.client_id == client.id,
    ).all()

    if not profiles:
        out.append(SuggestionCandidate(
            rule_key="COMPLIANCE_MISSING_PROFILE", category="COMPLIANCE",
            title="No compliance profile configured for this client",
            severity="HIGH",
            explanation=f"'{client.client_name}' has zero compliance types registered (GST, Income Tax, TDS, etc.) — no recurring due dates or tasks are being tracked.",
            recommendation="Set up at least one compliance profile if this client has active filing obligations, so due dates and tasks are tracked.",
            dedup_suffix="none",
            evidence=[EvidenceItem("CLIENT", f"Client '{client.client_name}' has 0 registered compliance profiles.", client.id)],
        ))
        return out

    profile_by_id = {p.id: p for p in profiles}
    tasks = db.query(ComplianceTask).filter(
        ComplianceTask.organization_id == client.organization_id,
        ComplianceTask.client_id == client.id,
        ComplianceTask.status != "COMPLETED",
    ).all()

    overdue_by_profile: dict = {}
    for t in tasks:
        profile = profile_by_id.get(t.profile_id)
        if not profile:
            continue

        if t.due_date < now:
            days_overdue = (now - t.due_date).days
            severity = "CRITICAL" if days_overdue > 30 else "HIGH"
            out.append(SuggestionCandidate(
                rule_key="COMPLIANCE_OVERDUE_TASK", category="COMPLIANCE",
                title=f"Overdue filing: {t.task_name}",
                severity=severity,
                explanation=f"'{t.task_name}' was due on {t.due_date.strftime('%d %b %Y')} and is {days_overdue} day(s) overdue.",
                recommendation="File as soon as possible to limit late-fee/interest exposure, then mark the task complete.",
                dedup_suffix=t.id,
                evidence=[
                    EvidenceItem("COMPLIANCE_TASK", f"Task '{t.task_name}' due {t.due_date.strftime('%d %b %Y')}, status {t.status}.", t.id),
                    EvidenceItem("COMPLIANCE_PROFILE", f"Compliance type '{profile.compliance_type}', frequency {profile.frequency}.", profile.id),
                ],
            ))
            overdue_by_profile.setdefault(profile.id, []).append(t)

        elif t.due_date <= now + timedelta(days=7):
            days_left = (t.due_date - now).days
            severity = "HIGH" if days_left <= 2 else "MEDIUM"
            out.append(SuggestionCandidate(
                rule_key="COMPLIANCE_UPCOMING_DUE", category="COMPLIANCE",
                title=f"Upcoming due date: {t.task_name}",
                severity=severity,
                explanation=f"'{t.task_name}' is due on {t.due_date.strftime('%d %b %Y')} ({days_left} day(s) away).",
                recommendation="Prepare filing documents ahead of the due date.",
                dedup_suffix=t.id,
                evidence=[
                    EvidenceItem("COMPLIANCE_TASK", f"Task '{t.task_name}' due {t.due_date.strftime('%d %b %Y')}.", t.id),
                    EvidenceItem("COMPLIANCE_PROFILE", f"Compliance type '{profile.compliance_type}', frequency {profile.frequency}.", profile.id),
                ],
            ))

    for profile in profiles:
        overdue_tasks = overdue_by_profile.get(profile.id, [])
        if profile.risk_level == "HIGH" and len(overdue_tasks) >= 2:
            out.append(SuggestionCandidate(
                rule_key="COMPLIANCE_HIGH_RISK_CLIENT", category="COMPLIANCE",
                title=f"High-risk client with multiple overdue {profile.compliance_type} filings",
                severity="CRITICAL",
                explanation=f"'{client.client_name}' has a HIGH risk_level compliance profile for {profile.compliance_type} with {len(overdue_tasks)} overdue task(s).",
                recommendation="Prioritize this client — high risk classification combined with multiple overdue filings warrants immediate partner attention.",
                dedup_suffix=profile.id,
                evidence=(
                    [EvidenceItem("COMPLIANCE_PROFILE", f"'{profile.compliance_type}' profile marked risk_level=HIGH.", profile.id)]
                    + [EvidenceItem("COMPLIANCE_TASK", f"Overdue: '{t.task_name}'.", t.id) for t in overdue_tasks]
                ),
            ))

    return out
