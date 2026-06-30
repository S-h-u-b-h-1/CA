import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, text

from app.models.models import (
    ResearchSource, ResearchQuery, ResearchResult, Client, 
    Document, Form26ASEntry, AISEntry, TISEntry, ITRActionItem,
    ITRVerificationResult
)

class ResearchService:
    @staticmethod
    def search_sources(db: Session, query_text: str, filters: Optional[Dict[str, Any]] = None) -> List[ResearchSource]:
        """
        Search legal & tax sources with basic ranking and advanced filters.
        """
        query = db.query(ResearchSource).filter(ResearchSource.status == "ACTIVE")
        
        # Apply filters
        if filters:
            if filters.get("authority"):
                query = query.filter(ResearchSource.authority == filters["authority"])
            if filters.get("category"):
                query = query.filter(ResearchSource.category == filters["category"])
            if filters.get("section"):
                query = query.filter(ResearchSource.section == filters["section"])
            if filters.get("rule_number"):
                query = query.filter(ResearchSource.rule_number == filters["rule_number"])
            if filters.get("circular_number"):
                query = query.filter(ResearchSource.circular_number == filters["circular_number"])
            if filters.get("notification_number"):
                query = query.filter(ResearchSource.notification_number == filters["notification_number"])

        all_sources = query.all()
        if not all_sources:
            return []

        # Tokenize query text for scoring
        words = [w.lower() for w in re.findall(r"\w+", query_text) if len(w) > 2]
        if not words:
            return all_sources[:5]

        scored_sources = []
        for src in all_sources:
            score = 0
            title_lower = src.title.lower() if src.title else ""
            content_lower = src.content.lower() if src.content else ""
            keywords_lower = src.keywords.lower() if src.keywords else ""
            section_lower = src.section.lower() if src.section else ""

            # Score matching
            for word in words:
                if word in title_lower:
                    score += 15
                if word in section_lower:
                    score += 25
                if word in keywords_lower:
                    score += 10
                # Content frequency count
                score += content_lower.count(word) * 2

            if score > 0 or not query_text:
                scored_sources.append((score, src))

        # Sort by score descending
        scored_sources.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_sources[:5]]

    @staticmethod
    def generate_answer(
        db: Session, 
        organization_id: str,
        user_id: str,
        query_text: str, 
        client_id: Optional[str] = None, 
        assessment_year: Optional[str] = "2025-26",
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Retrieves matching legal sources, reads optional client context, 
        synthesizes a legal answer, and logs it.
        """
        # Save query log first
        query_record = ResearchQuery(
            organization_id=organization_id,
            user_id=user_id,
            client_id=client_id,
            query_text=query_text,
            filters_json=filters
        )
        db.add(query_record)
        db.commit()

        # Retrieve relevant authorities
        sources = ResearchService.search_sources(db, query_text, filters)

        if not sources:
            # Prevent legal hallucination if database has no matches
            summary = "No authoritative sources found in the database. As per CA rules, no answers can be generated without verified sources."
            applicable_law = "N/A"
            relevant_sections = "N/A"
            relevant_circulars = "N/A"
            relevant_notifications = "N/A"
            considerations = "N/A"
            risks = "N/A"
            confidence = 0.0
            matched_sources = []
        else:
            matched_sources = sources
            # Build applicable law blocks
            laws = []
            sections = []
            circulars = []
            notifications = []
            
            for src in sources:
                laws.append(f"{src.authority}: {src.title}")
                if src.section:
                    sections.append(f"Section {src.section}")
                if src.circular_number:
                    circulars.append(f"Circular {src.circular_number}")
                if src.notification_number:
                    notifications.append(f"Notification {src.notification_number}")

            applicable_law = "\n".join(set(laws))
            relevant_sections = ", ".join(set(sections)) if sections else "None directly cited."
            relevant_circulars = ", ".join(set(circulars)) if circulars else "None directly cited."
            relevant_notifications = ", ".join(set(notifications)) if notifications else "None directly cited."

            # Construct summary and details using the actual matched sources
            primary_src = sources[0]
            summary = f"Based on {primary_src.authority} references, this relates to {primary_src.title}. {primary_src.content[:200]}..."
            
            # Risks and considerations
            risks = f"Non-compliance with the provisions of {primary_src.authority} might trigger statutory interest, penalties, or assessment audits under the Income Tax Act."
            considerations = f"Chartered Accountants must verify all transactional records with supporting bank statements and invoice ledgers before filing declarations."
            confidence = 90.0 if len(sources) > 2 else 75.0

        # Load client context if provided
        client_context_log = ""
        if client_id:
            client_record = db.query(Client).filter(Client.id == client_id).first()
            if client_record:
                client_context_log += f"Client Name: {client_record.client_name} (PAN: {client_record.PAN or 'N/A'}). "
                
                # Check for active mismatches / warnings in ITR Actions
                actions = db.query(ITRActionItem).filter(
                    ITRActionItem.client_id == client_id,
                    ITRActionItem.assessment_year == assessment_year
                ).all()
                
                if actions:
                    client_context_log += "\nActive System Discrepancies:\n"
                    for act in actions:
                        client_context_log += f"- {act.action_text} ({act.reference_document or 'System'})\n"

                # Check if TIS/AIS mismatches specifically exist
                tis_mismatch = db.query(ITRVerificationResult).filter(
                    ITRVerificationResult.client_id == client_id,
                    ITRVerificationResult.assessment_year == assessment_year,
                    ITRVerificationResult.verification_type == "TIS_AIS_CONSISTENCY",
                    ITRVerificationResult.status == "WARNING"
                ).first()
                if tis_mismatch:
                    client_context_log += "\nDiscrepancy Highlight: High-value mismatch identified between TIS reported values and AIS records."

        # Merge client context into considerations & summary if it exists
        if client_context_log:
            considerations = (
                f"**Client Specific Observations:**\n{client_context_log}\n\n"
                f"**Legal Guidance:**\n{considerations}"
            )
            summary = f"[Client Context Integrated] {summary}"

        # Save structured research result
        res_record = ResearchResult(
            organization_id=organization_id,
            user_id=user_id,
            query_id=query_record.id,
            summary=summary,
            applicable_law=applicable_law,
            relevant_sections=relevant_sections,
            relevant_circulars=relevant_circulars,
            relevant_notifications=relevant_notifications,
            considerations=considerations,
            risks=risks,
            confidence=confidence,
            references_json=[
                {
                    "id": src.id,
                    "title": src.title,
                    "authority": src.authority,
                    "section": src.section,
                    "rule_number": src.rule_number,
                    "circular_number": src.circular_number,
                    "notification_number": src.notification_number,
                    "publication_date": src.publication_date.isoformat() if src.publication_date else None,
                    "effective_date": src.effective_date.isoformat() if src.effective_date else None,
                    "url": src.url,
                    "category": src.category,
                    "keywords": src.keywords,
                    "version": src.version,
                    "status": src.status,
                    "content": src.content,
                    "created_at": src.created_at.isoformat()
                } for src in matched_sources
            ]
        )
        db.add(res_record)
        db.commit()

        # Format output schema
        return {
            "id": res_record.id,
            "summary": summary,
            "applicable_law": applicable_law,
            "relevant_sections": relevant_sections,
            "relevant_circulars": relevant_circulars,
            "relevant_notifications": relevant_notifications,
            "considerations": considerations,
            "risks": risks,
            "confidence": confidence,
            "references": [
                {
                    "id": src.id,
                    "title": src.title,
                    "authority": src.authority,
                    "section": src.section,
                    "rule_number": src.rule_number,
                    "circular_number": src.circular_number,
                    "notification_number": src.notification_number,
                    "publication_date": src.publication_date,
                    "effective_date": src.effective_date,
                    "url": src.url,
                    "category": src.category,
                    "keywords": src.keywords,
                    "version": src.version,
                    "status": src.status,
                    "content": src.content,
                    "created_at": src.created_at
                } for src in matched_sources
            ],
            "created_at": res_record.created_at
        }
