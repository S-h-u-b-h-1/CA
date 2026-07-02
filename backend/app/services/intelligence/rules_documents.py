"""Document Rules — flags missing document types for a client, gated on real
signals (the client's registered compliance types and client_type) rather than
assuming every client needs every document.

Checks both Document.classification (auto-detected by the deterministic
classify_document() classifier) and Document.category (free-text, user-supplied
at upload) so a document isn't wrongly flagged "missing" just because a user
picked an inconsistent category label — this mirrors the same gap noted in
ITRPreparationService.recompute(), which only checks category.

"Expired supporting documents" (requested in the product spec) is intentionally
NOT implemented: the Document model captures no validity/expiry metadata, and
choosing an expiry policy per document type would be inventing a rule. Only
upload recency is trackable — listed as NOT_YET_SUPPORTED in the registry.
"""
from typing import List
from sqlalchemy.orm import Session
from app.models.models import Client, Document, ComplianceProfile
from app.services.intelligence.core import EvidenceItem, SuggestionCandidate


def evaluate(db: Session, client: Client) -> List[SuggestionCandidate]:
    out: List[SuggestionCandidate] = []

    docs = db.query(Document).filter(Document.client_id == client.id, Document.deleted_at.is_(None)).all()
    present_labels = {(d.classification or "").lower() for d in docs} | {(d.category or "").lower() for d in docs}

    def has(target: str) -> bool:
        t = target.lower()
        return any(t in label or label in t for label in present_labels if label)

    compliance_types = {
        p.compliance_type for p in db.query(ComplianceProfile).filter(
            ComplianceProfile.organization_id == client.organization_id,
            ComplianceProfile.client_id == client.id,
        ).all()
    }

    required = ["Bank Statement"]
    if "GST" in compliance_types:
        required.append("GSTR-3B")
    if compliance_types & {"Income Tax", "TDS"} or not compliance_types:
        required += ["Form 16", "Form 26AS"]
    if client.client_type in ("Company", "LLP"):
        required += ["Balance Sheet", "Profit & Loss"]

    for doc_type in required:
        if not has(doc_type):
            out.append(SuggestionCandidate(
                rule_key="DOCUMENT_MISSING", category="DOCUMENTS",
                title=f"Missing {doc_type}",
                severity="MEDIUM",
                explanation=f"No document classified or categorized as '{doc_type}' has been uploaded for '{client.client_name}'. {len(docs)} document(s) on file: {sorted({d.classification or d.category for d in docs}) if docs else 'none'}.",
                recommendation=f"Request {doc_type} from the client if applicable to their filing obligations.",
                dedup_suffix=doc_type,
                evidence=[EvidenceItem("CLIENT", f"Client has {len(docs)} document(s) on file, none matching '{doc_type}'.", client.id)],
            ))

    return out
