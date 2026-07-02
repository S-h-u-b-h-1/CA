"""Authority Update Rules — surfaces recent government/regulatory updates that
may affect a client, matched by category.

There is no full-text or section-level relevance analysis here — matching is a
category-string join between the client's ComplianceProfile.compliance_type and
GovernmentSource.category. That's real (the categories genuinely come from the
live connector registry) but coarse, so confidence is deliberately pinned to
MEDIUM regardless of how many records are involved — this is a heuristic match,
not a corroborated fact, and should always prompt a human review of the update.

Mapping is intentionally partial: PF, ESI, and Professional Tax have no real
connector category to map to today (verified against the live registry: only
Direct Tax, Indirect Tax, Corporate Law, Securities Law, Professional Standards
exist as real categories from the 8 live connectors) — inventing a mapping for
labour-law/state-PT sources that don't exist yet would be fabrication.
"""
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session
from app.models.models import Client, ComplianceProfile, GovernmentUpdate, GovernmentSource
from app.services.intelligence.core import EvidenceItem, SuggestionCandidate

COMPLIANCE_TYPE_TO_UPDATE_CATEGORIES = {
    "GST": ["Indirect Tax"],
    "Income Tax": ["Direct Tax"],
    "TDS": ["Direct Tax"],  # Section 194x, governed by CBDT — Direct Tax, not Indirect Tax
    "TCS": ["Direct Tax"],  # Section 206C of the Income-tax Act — a Direct Tax mechanism despite the name
    "MCA/ROC": ["Corporate Law"],
    # PF, ESI, Professional Tax: no real connector category covers these domains today.
}

LOOKBACK_DAYS = 30
MAX_PER_CATEGORY = 5


def compliance_types_for_category(category: str) -> List[str]:
    """Reverse lookup of COMPLIANCE_TYPE_TO_UPDATE_CATEGORIES, used by the
    connector sync hook to find which compliance types a newly-ingested
    update's category is relevant to, without duplicating the mapping."""
    return [ct for ct, categories in COMPLIANCE_TYPE_TO_UPDATE_CATEGORIES.items() if category in categories]


def evaluate(db: Session, client: Client) -> List[SuggestionCandidate]:
    out: List[SuggestionCandidate] = []

    compliance_types = {
        p.compliance_type for p in db.query(ComplianceProfile).filter(
            ComplianceProfile.organization_id == client.organization_id,
            ComplianceProfile.client_id == client.id,
        ).all()
    }
    if not compliance_types:
        return out

    target_categories = set()
    for ct in compliance_types:
        target_categories.update(COMPLIANCE_TYPE_TO_UPDATE_CATEGORIES.get(ct, []))
    if not target_categories:
        return out

    cutoff = datetime.utcnow() - timedelta(days=LOOKBACK_DAYS)
    updates = (
        db.query(GovernmentUpdate, GovernmentSource)
        .join(GovernmentSource, GovernmentUpdate.source_id == GovernmentSource.id)
        .filter(
            GovernmentUpdate.status == "ACTIVE",
            GovernmentSource.category.in_(target_categories),
            GovernmentUpdate.issue_date >= cutoff,
        )
        .order_by(GovernmentUpdate.issue_date.desc())
        .limit(MAX_PER_CATEGORY * len(target_categories))
        .all()
    )

    for update, source in updates:
        matched_type = next(
            (ct for ct in compliance_types if source.category in COMPLIANCE_TYPE_TO_UPDATE_CATEGORIES.get(ct, [])),
            None,
        )
        days_old = (datetime.utcnow() - update.issue_date).days if update.issue_date else None
        severity = "HIGH" if days_old is not None and days_old <= 7 else "MEDIUM"

        out.append(SuggestionCandidate(
            rule_key="RESEARCH_AUTHORITY_UPDATE_MATCH", category="RESEARCH",
            title=f"{update.issuing_authority or source.source_name} update may affect this client's {matched_type} compliance",
            severity=severity,
            explanation=(
                f"\"{update.title}\" was issued {update.issue_date.strftime('%d %b %Y') if update.issue_date else 'recently'} "
                f"under category '{source.category}', which is mapped to this client's '{matched_type}' compliance profile."
            ),
            recommendation="Review the update directly to confirm it applies to this client before acting on it.",
            dedup_suffix=f"{matched_type}:{update.id}",
            related_government_update_id=update.id,
            confidence_override="MEDIUM",
            confidence_reason_override=(
                "Based on a category match between this client's compliance profile and the update's "
                "classification, not full-text analysis — always verify direct applicability."
            ),
            evidence=[
                EvidenceItem("GOVERNMENT_UPDATE", f"\"{update.title}\" ({source.source_name}, {source.category}).", update.id),
                EvidenceItem("COMPLIANCE_PROFILE", f"Client has an active '{matched_type}' compliance profile.", None),
            ],
        ))

    return out
