"""Client Health Rules — a meta rule-group that reasons over other subsystems'
outputs rather than raw data directly. This is what makes the engine a genuine
"reasoning layer": it can compare/aggregate signals other rule groups (and other
services) already produced, not just re-derive facts from source tables.

Rule 1 cross-checks the two health-score implementations that already exist
independently in this codebase (ComplianceService.compute_health_score, driven by
filing history, vs WorkspaceService.calculate_health_score, driven by document/ITR
completeness) — if they disagree sharply, that's itself a real, worth-surfacing
signal, not a new score being invented.

Rule 2 rolls up same-client CRITICAL findings from other categories into a single
"needs urgent attention" flag, so a CA doesn't have to notice 3 separate CRITICAL
rows to realize a client is in trouble. It runs after the other rule groups and
inspects their output for this client within the same generation pass.
"""
from typing import List
from sqlalchemy.orm import Session
from app.models.models import Client, ClientTaxProfile
from app.services.compliance_service import ComplianceService
from app.services.workspace import WorkspaceService
from app.services.intelligence.core import EvidenceItem, SuggestionCandidate

BAND_ORDER = ["Critical", "Needs Attention", "Good", "Excellent"]


def evaluate(db: Session, client: Client, other_candidates: List[SuggestionCandidate]) -> List[SuggestionCandidate]:
    out: List[SuggestionCandidate] = []
    out.extend(_health_score_divergence(db, client))
    out.extend(_critical_rollup(client, other_candidates))
    return out


def _health_score_divergence(db: Session, client: Client) -> List[SuggestionCandidate]:
    compliance_label, compliance_score = ComplianceService.compute_health_score(db, client.id)

    latest_profile = (
        db.query(ClientTaxProfile)
        .filter(ClientTaxProfile.client_id == client.id)
        .order_by(ClientTaxProfile.assessment_year.desc())
        .first()
    )
    if not latest_profile:
        return []

    workspace_label, workspace_score = WorkspaceService.calculate_health_score(db, client.id, latest_profile.assessment_year)

    try:
        gap = abs(BAND_ORDER.index(compliance_label) - BAND_ORDER.index(workspace_label))
    except ValueError:
        return []

    if gap >= 2:
        return [SuggestionCandidate(
            rule_key="CLIENT_HEALTH_SCORE_DIVERGENCE", category="COMPLIANCE",
            title="Compliance and document-readiness health scores disagree",
            severity="MEDIUM",
            explanation=(
                f"Compliance filing health is '{compliance_label}' ({compliance_score:.0f}) while document/ITR "
                f"readiness health for AY {latest_profile.assessment_year} is '{workspace_label}' ({workspace_score:.0f}). "
                f"These are computed independently — a wide gap usually means one dimension of the engagement "
                f"is being tracked while the other is being neglected."
            ),
            recommendation="Check which dimension is lagging and whether the discrepancy reflects a real gap in the engagement.",
            dedup_suffix=latest_profile.assessment_year,
            evidence=[
                EvidenceItem("COMPLIANCE_HISTORY", f"Compliance health: {compliance_label} ({compliance_score:.0f})."),
                EvidenceItem("DOCUMENT", f"Document/ITR readiness health: {workspace_label} ({workspace_score:.0f})."),
            ],
        )]
    return []


def _critical_rollup(client: Client, other_candidates: List[SuggestionCandidate]) -> List[SuggestionCandidate]:
    critical = [c for c in other_candidates if c.severity == "CRITICAL"]
    if len(critical) >= 2:
        categories = sorted({c.category for c in critical})
        return [SuggestionCandidate(
            rule_key="CLIENT_HEALTH_MULTIPLE_CRITICAL", category="COMPLIANCE",
            title=f"{client.client_name} has {len(critical)} critical findings across {len(categories)} categor{'y' if len(categories)==1 else 'ies'}",
            severity="CRITICAL",
            explanation="This client has multiple independent CRITICAL findings this cycle: " + "; ".join(f"\"{c.title}\"" for c in critical[:5]) + (f" and {len(critical)-5} more" if len(critical) > 5 else "") + ".",
            recommendation="Review this client as a whole rather than addressing findings one at a time — the combination may warrant partner attention.",
            dedup_suffix="rollup",
            evidence=[EvidenceItem(c.category, c.title) for c in critical],
        )]
    return []
