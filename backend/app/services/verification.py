from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any, Optional
from app.models.models import Citation, CitationVerification, RawDocument, ProcessedDocument, GovernmentUpdate

class SourceVerificationEngine:
    @staticmethod
    def verify_citation(db: Session, organization_id: str, citation_id: str) -> Dict[str, Any]:
        """
        Verifies if a citation's quote text exists in its source document.
        Returns a verification record payload and caches the result.
        """
        citation = db.query(Citation).filter(
            Citation.id == citation_id,
            Citation.organization_id == organization_id
        ).first()

        if not citation:
            return {
                "status": "FAILED",
                "score": 0.0,
                "error": "Citation record not found."
            }

        source_text = ""
        source_name = "Unknown Source"
        
        # 1. Fetch Source Text based on Source Type
        if citation.source_type == "GOVERNMENT_UPDATE" or citation.government_update_id:
            gov_id = citation.government_update_id or citation.source_document_id
            gov_update = db.query(GovernmentUpdate).filter(GovernmentUpdate.id == gov_id).first()
            if gov_update:
                source_text = gov_update.html_content or ""
                source_name = gov_update.title or gov_update.document_number or "Government Circular"
        else:
            doc_id = citation.source_document_id
            raw_doc = db.query(RawDocument).filter(
                RawDocument.id == doc_id,
                RawDocument.organization_id == organization_id
            ).first()
            if raw_doc:
                source_name = raw_doc.name
                proc_doc = db.query(ProcessedDocument).filter(ProcessedDocument.raw_document_id == doc_id).first()
                if proc_doc:
                    source_text = proc_doc.ocr_text or ""

        if not source_text:
            return {
                "status": "FAILED",
                "score": 0.0,
                "error": "Source document text content is empty or not processed."
            }

        # 2. Check Match Quality
        quote = citation.quote_text or ""
        clean_quote = quote.strip().lower()
        clean_source = source_text.strip().lower()

        status = "FAILED"
        score = 0.0
        details = {
            "source_name": source_name,
            "source_type": citation.source_type,
            "has_url": bool(citation.source_url),
            "quote_checked": quote
        }

        if not clean_quote:
            # Document exists, but no quote was provided
            status = "VERIFIED"
            score = 1.0
            details["message"] = "Document verified (no specific text snippet requested)."
        elif clean_quote in clean_source:
            # Exact Match
            status = "VERIFIED"
            score = 1.0
            details["message"] = "Exact text snippet matched successfully."
        else:
            # Word Overlap check for partial verification
            quote_words = [w for w in clean_quote.split() if len(w) > 3]
            if quote_words:
                matches = sum(1 for w in quote_words if w in clean_source)
                ratio = matches / len(quote_words)
                details["word_overlap_ratio"] = ratio
                if ratio >= 0.6:
                    status = "PARTIALLY_VERIFIED"
                    score = ratio
                    details["message"] = f"Partial text match found ({int(ratio * 100)}% word overlap)."
                else:
                    status = "FAILED"
                    score = ratio
                    details["message"] = "Text snippet not found in source document."
            else:
                status = "FAILED"
                score = 0.0
                details["message"] = "Text snippet not found in source document."

        # 3. Create or Update CitationVerification record
        verification = db.query(CitationVerification).filter(
            CitationVerification.citation_id == citation_id,
            CitationVerification.organization_id == organization_id
        ).first()

        if not verification:
            verification = CitationVerification(
                organization_id=organization_id,
                citation_id=citation_id,
                status=status,
                details_json=details
            )
            db.add(verification)
        else:
            verification.status = status
            verification.details_json = details
            verification.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(verification)

        return {
            "status": status,
            "score": score,
            "verification_id": verification.id,
            "details": details
        }
