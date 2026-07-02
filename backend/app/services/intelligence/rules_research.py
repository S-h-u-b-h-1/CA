"""Research Rules — flags low-confidence answers from the internal Research
Workspace for a client, so they get a second look rather than being treated as
settled.

ResearchService.generate_answer() is a deterministic keyword-scoring engine over
an 8-entry seed corpus (backend/app/core/seed_research.py) — not an LLM call, and
not a comprehensive legal database. Suggestions from this rule are worded to
reflect that: a low ResearchResult.confidence here means "the keyword match was
weak," not "the AI is unsure" in any deeper sense.
"""
from typing import List
from sqlalchemy.orm import Session
from app.models.models import Client, ResearchQuery, ResearchResult
from app.services.intelligence.core import EvidenceItem, SuggestionCandidate

LOW_CONFIDENCE_THRESHOLD = 75.0


def evaluate(db: Session, client: Client) -> List[SuggestionCandidate]:
    out: List[SuggestionCandidate] = []

    rows = (
        db.query(ResearchQuery, ResearchResult)
        .join(ResearchResult, ResearchResult.query_id == ResearchQuery.id)
        .filter(ResearchQuery.client_id == client.id)
        .all()
    )

    for query, result in rows:
        if (result.confidence or 0.0) < LOW_CONFIDENCE_THRESHOLD:
            out.append(SuggestionCandidate(
                rule_key="RESEARCH_LOW_CONFIDENCE_ANSWER", category="RESEARCH",
                title="Low-confidence research answer on file for this client",
                severity="LOW",
                explanation=(
                    f"A research query (\"{query.query_text[:120]}\") returned a match confidence of "
                    f"{result.confidence:.0f}%, below the {LOW_CONFIDENCE_THRESHOLD:.0f}% threshold. "
                    f"The Research Workspace is a keyword-matched citation lookup over a small seeded "
                    f"source set, not an AI-verified legal opinion — a weak match here means the keyword "
                    f"overlap was thin, not that a model is uncertain."
                ),
                recommendation="Review this answer manually or search authoritative sources directly before relying on it.",
                dedup_suffix=result.id,
                evidence=[EvidenceItem("RESEARCH_RESULT", f"Query \"{query.query_text[:80]}\" -> confidence {result.confidence:.0f}%.", result.id)],
            ))

    return out
