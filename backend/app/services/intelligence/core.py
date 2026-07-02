from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EvidenceItem:
    evidence_type: str
    summary: str
    reference_id: Optional[str] = None


@dataclass
class SuggestionCandidate:
    rule_key: str
    category: str
    title: str
    severity: str
    explanation: str
    dedup_suffix: str
    evidence: List[EvidenceItem] = field(default_factory=list)
    recommendation: Optional[str] = None
    related_document_ids: List[str] = field(default_factory=list)
    related_government_update_id: Optional[str] = None
    confidence_override: Optional[str] = None
    confidence_reason_override: Optional[str] = None


SEVERITY_LEVELS = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
CONFIDENCE_LEVELS = ("HIGH", "MEDIUM", "LOW")


def derive_confidence(evidence: List[EvidenceItem]) -> tuple[str, str]:
    """Confidence is derived from the number of DISTINCT real evidence-source
    types cited, never asserted by a rule directly. This is what makes it
    reproducible: the same evidence set always yields the same confidence.

    HIGH   - 2+ distinct source types corroborate the finding
    MEDIUM - exactly 1 authoritative source type
    LOW    - no structured evidence could be cited
    """
    distinct_kinds = sorted({e.evidence_type for e in evidence})
    if len(distinct_kinds) >= 2:
        return "HIGH", f"Supported by {len(distinct_kinds)} independent data sources: {', '.join(distinct_kinds)}."
    if len(distinct_kinds) == 1:
        return "MEDIUM", f"Supported by one authoritative data source: {distinct_kinds[0]}."
    return "LOW", "Incomplete supporting information — no structured evidence source could be cited."
