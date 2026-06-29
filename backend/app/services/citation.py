import re
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.models.models import Citation, Entity
from app.services.extractor import LegalReferenceExtractor

class CitationEngine:
    @staticmethod
    def create_citation(
        db: Session,
        organization_id: str,
        source_type: str,
        source_document_id: Optional[str] = None,
        government_update_id: Optional[str] = None,
        client_id: Optional[str] = None,
        page_number: Optional[int] = None,
        paragraph_number: Optional[int] = None,
        line_start: Optional[int] = None,
        line_end: Optional[int] = None,
        section_reference: Optional[str] = None,
        act_reference: Optional[str] = None,
        rule_reference: Optional[str] = None,
        circular_number: Optional[str] = None,
        notification_number: Optional[str] = None,
        judgment_reference: Optional[str] = None,
        quote_text: Optional[str] = None,
        normalized_text: Optional[str] = None,
        source_url: Optional[str] = None,
        confidence_score: float = 1.0,
        target_entity_id: Optional[str] = None,
        text_reference: str = ""
    ) -> Citation:
        """
        Creates and returns a new Citation log entry in the database.
        """
        # Check for existing duplicate citation before creating a new one
        existing = db.query(Citation).filter(
            Citation.organization_id == organization_id,
            Citation.source_type == source_type,
            Citation.source_document_id == source_document_id,
            Citation.government_update_id == government_update_id,
            Citation.paragraph_number == paragraph_number,
            Citation.section_reference == section_reference,
            Citation.rule_reference == rule_reference,
            Citation.circular_number == circular_number,
            Citation.notification_number == notification_number,
            Citation.quote_text == quote_text,
            Citation.target_entity_id == target_entity_id
        ).first()

        if existing:
            return existing

        # Formulate text_reference description if empty
        if not text_reference:
            ref_parts = []
            if act_reference:
                ref_parts.append(f"Act: {act_reference}")
            if section_reference:
                ref_parts.append(f"Section: {section_reference}")
            if rule_reference:
                ref_parts.append(f"Rule: {rule_reference}")
            if circular_number:
                ref_parts.append(f"Circular: {circular_number}")
            if notification_number:
                ref_parts.append(f"Notification: {notification_number}")
            
            ref_desc = ", ".join(ref_parts) if ref_parts else "General regulatory citation"
            text_reference = f"{source_type} Citation [{ref_desc}]"

        citation = Citation(
            organization_id=organization_id,
            source_document_id=source_document_id,
            government_update_id=government_update_id,
            client_id=client_id,
            source_type=source_type,
            page_number=page_number,
            paragraph_number=paragraph_number,
            line_start=line_start,
            line_end=line_end,
            section_reference=section_reference,
            act_reference=act_reference,
            rule_reference=rule_reference,
            circular_number=circular_number,
            notification_number=notification_number,
            judgment_reference=judgment_reference,
            quote_text=quote_text,
            normalized_text=normalized_text,
            source_url=source_url,
            confidence_score=confidence_score,
            target_entity_id=target_entity_id,
            text_reference=text_reference
        )
        db.add(citation)
        db.commit()
        db.refresh(citation)
        return citation

    @staticmethod
    def extract_and_create_citations(
        db: Session,
        organization_id: str,
        text: str,
        source_type: str,
        source_document_id: Optional[str] = None,
        government_update_id: Optional[str] = None,
        client_id: Optional[str] = None,
        page_number: Optional[int] = None,
        paragraph_number: Optional[int] = None,
        source_url: Optional[str] = None
    ) -> List[Citation]:
        """
        Parses text content, extracts legal references and entities, and links them as Citation objects.
        """
        citations = []
        extracted = LegalReferenceExtractor.extract_all(text)
        
        # Determine the acts, rules, circulars, etc.
        sections = extracted.get("SECTION", [])
        rules = extracted.get("RULE", [])
        circulars = extracted.get("CIRCULAR", [])
        notifications = extracted.get("NOTIFICATION", [])

        # Default fallback act reference
        act_ref = "Income Tax Act" if "income tax" in text.lower() else ("CGST Act" if "gst" in text.lower() else "Indian Statutory Code")

        # 1. Create Citations for Sections
        for sec in sections:
            quote_context = CitationEngine.get_sentence_with_keyword(text, sec)
            cit = CitationEngine.create_citation(
                db=db,
                organization_id=organization_id,
                source_type=source_type,
                source_document_id=source_document_id,
                government_update_id=government_update_id,
                client_id=client_id,
                page_number=page_number,
                paragraph_number=paragraph_number,
                section_reference=sec,
                act_reference=act_ref,
                quote_text=quote_context or sec,
                normalized_text=text.strip(),
                source_url=source_url,
                confidence_score=0.9
            )
            citations.append(cit)

        # 2. Create Citations for Rules
        for rule in rules:
            quote_context = CitationEngine.get_sentence_with_keyword(text, rule)
            cit = CitationEngine.create_citation(
                db=db,
                organization_id=organization_id,
                source_type=source_type,
                source_document_id=source_document_id,
                government_update_id=government_update_id,
                client_id=client_id,
                page_number=page_number,
                paragraph_number=paragraph_number,
                rule_reference=rule,
                act_reference=act_ref,
                quote_text=quote_context or rule,
                normalized_text=text.strip(),
                source_url=source_url,
                confidence_score=0.9
            )
            citations.append(cit)

        # 3. Create Citations for Circulars
        for circ in circulars:
            quote_context = CitationEngine.get_sentence_with_keyword(text, circ)
            cit = CitationEngine.create_citation(
                db=db,
                organization_id=organization_id,
                source_type=source_type,
                source_document_id=source_document_id,
                government_update_id=government_update_id,
                client_id=client_id,
                page_number=page_number,
                paragraph_number=paragraph_number,
                circular_number=circ,
                quote_text=quote_context or circ,
                normalized_text=text.strip(),
                source_url=source_url,
                confidence_score=0.95
            )
            citations.append(cit)

        # 4. Create Citations for Notifications
        for notif in notifications:
            quote_context = CitationEngine.get_sentence_with_keyword(text, notif)
            cit = CitationEngine.create_citation(
                db=db,
                organization_id=organization_id,
                source_type=source_type,
                source_document_id=source_document_id,
                government_update_id=government_update_id,
                client_id=client_id,
                page_number=page_number,
                paragraph_number=paragraph_number,
                notification_number=notif,
                quote_text=quote_context or notif,
                normalized_text=text.strip(),
                source_url=source_url,
                confidence_score=0.95
            )
            citations.append(cit)

        # 5. Connect any extracted generic entities (PAN, GSTIN, etc.) to a document reference
        for etype in ["PAN", "GSTIN", "CIN", "DIN", "TAN"]:
            for val in extracted.get(etype, []):
                entity = db.query(Entity).filter(
                    Entity.organization_id == organization_id,
                    Entity.entity_type == etype,
                    Entity.value == val,
                    Entity.status == "ACTIVE"
                ).first()
                
                if entity:
                    quote_context = CitationEngine.get_sentence_with_keyword(text, val)
                    cit = CitationEngine.create_citation(
                        db=db,
                        organization_id=organization_id,
                        source_type=source_type,
                        source_document_id=source_document_id,
                        government_update_id=government_update_id,
                        client_id=client_id,
                        page_number=page_number,
                        paragraph_number=paragraph_number,
                        quote_text=quote_context or val,
                        normalized_text=text.strip(),
                        source_url=source_url,
                        confidence_score=1.0,
                        target_entity_id=entity.id,
                        text_reference=f"Extracted {etype}: {val}"
                    )
                    citations.append(cit)

        return citations

    @staticmethod
    def get_sentence_with_keyword(text: str, keyword: str) -> Optional[str]:
        """
        Extracts a surrounding sentence window containing the keyword to act as quote context.
        """
        if not text or not keyword:
            return None
        
        # Split text into rough sentences
        sentences = re.split(r"(?<=[.!?])\s+", text)
        for sentence in sentences:
            if keyword.lower() in sentence.lower():
                return sentence.strip()
        
        return None
