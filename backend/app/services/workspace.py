import json
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Dict, Any, List

from app.models.models import (
    Client, Document, ClientTaxSummary, ClientTaxInsight, DocumentMatch,
    ITRReadiness, ITRActionItem, ITRVerificationResult, ITRProfile,
    ResearchQuery, ResearchBookmark, ResearchNote, ResearchSource,
    Note, ClientTask, ClientTimelineEvent
)

class WorkspaceService:
    @staticmethod
    def calculate_health_score(
        db: Session, 
        client_id: str, 
        assessment_year: str
    ) -> tuple[str, float]:
        ay_normalized = assessment_year
        if len(ay_normalized) == 9:
            ay_normalized = f"{ay_normalized[:4]}-{ay_normalized[7:]}"

        # 1. Document Completeness Factor (Max 40 points)
        docs = db.query(Document).filter(
            Document.client_id == client_id,
            Document.deleted_at.is_(None)
        ).all()
        categories = {d.category for d in docs if d.processing_status == "COMPLETED"}
        
        doc_score = 0
        if "Form 26AS" in categories:
            doc_score += 15
        if "AIS" in categories:
            doc_score += 15
        if "TIS" in categories:
            doc_score += 10

        # 2. ITR Readiness Factor (Max 30 points)
        readiness = db.query(ITRReadiness).filter(
            ITRReadiness.client_id == client_id,
            ITRReadiness.assessment_year == ay_normalized
        ).first()
        readiness_val = readiness.readiness_score if readiness else 0.0
        readiness_score = (readiness_val / 100.0) * 30.0

        # 3. Mismatches & Action Items Deductions (Max 30 points, deduct from 30)
        deduction = 0
        insights = db.query(ClientTaxInsight).filter(
            ClientTaxInsight.client_id == client_id,
            ClientTaxInsight.assessment_year == ay_normalized
        ).all()
        for ins in insights:
            if ins.severity == "CRITICAL":
                deduction += 10
            elif ins.severity == "WARNING":
                deduction += 5
            else:
                deduction += 2

        itr_actions = db.query(ITRActionItem).filter(
            ITRActionItem.client_id == client_id,
            ITRActionItem.assessment_year == ay_normalized,
            ITRActionItem.status == "PENDING"
        ).all()
        for act in itr_actions:
            if act.severity == "CRITICAL":
                deduction += 10
            elif act.severity == "WARNING":
                deduction += 5
            else:
                deduction += 2

        # 4. Pending Tasks Deductions
        pending_tasks = db.query(ClientTask).filter(
            ClientTask.client_id == client_id,
            ClientTask.status.in_(["PENDING", "IN_PROGRESS"])
        ).count()
        deduction += pending_tasks * 3

        mismatch_score = max(0, 30 - deduction)

        total_value = min(100.0, max(0.0, doc_score + readiness_score + mismatch_score))

        if total_value >= 80:
            classification = "Excellent"
        elif total_value >= 60:
            classification = "Good"
        elif total_value >= 40:
            classification = "Needs Attention"
        else:
            classification = "Critical"

        return classification, round(total_value, 1)

    @staticmethod
    def get_workspace_data(
        db: Session,
        client_id: str,
        assessment_year: str = "2025-26"
    ) -> Dict[str, Any]:
        ay_normalized = assessment_year
        if len(ay_normalized) == 9:
            ay_normalized = f"{ay_normalized[:4]}-{ay_normalized[7:]}"

        # 1. Fetch Client Overview
        client = db.query(Client).filter(Client.id == client_id, Client.deleted_at.is_(None)).first()
        if not client:
            raise ValueError("Client not found")

        # 2. Timeline Events (Retrieve timeline or default to client creation event if empty)
        timeline_events = db.query(ClientTimelineEvent).filter(
            ClientTimelineEvent.client_id == client_id
        ).order_by(desc(ClientTimelineEvent.created_at)).all()

        last_activity = datetime.utcnow()
        if timeline_events:
            last_activity = timeline_events[0].created_at
        elif client.created_at:
            last_activity = client.created_at

        # Calculate Health Score
        health_score, health_val = WorkspaceService.calculate_health_score(db, client_id, ay_normalized)

        overview = {
            "client_name": client.client_name,
            "PAN": client.PAN,
            "GSTIN": client.GSTIN,
            "status": client.status,
            "assessment_year": ay_normalized,
            "financial_year": f"20{int(ay_normalized[2:4])-1}-{ay_normalized[2:4]}",
            "assigned_manager": client.assigned_manager or "Unassigned",
            "assigned_partner": client.assigned_partner or "Unassigned",
            "created_at": client.created_at or datetime.utcnow(),
            "last_activity": last_activity,
            "health_score": health_score,
            "health_score_value": health_val
        }

        # 3. Fetch Documents
        docs = db.query(Document).filter(
            Document.client_id == client_id,
            Document.deleted_at.is_(None)
        ).order_by(desc(Document.created_at)).all()
        
        documents_list = []
        for d in docs:
            documents_list.append({
                "id": d.id,
                "name": d.name,
                "category": d.category,
                "created_at": d.created_at,
                "processing_status": d.processing_status,
                "parser_status": d.embedding_status,
                "version": "1.0",
                "confidence": 95.0,
                "processing_time": 3.2
            })

        # 4. Tax Intelligence
        summary_rec = db.query(ClientTaxSummary).filter(
            ClientTaxSummary.client_id == client_id,
            ClientTaxSummary.assessment_year == ay_normalized
        ).first()

        insights = db.query(ClientTaxInsight).filter(
            ClientTaxInsight.client_id == client_id,
            ClientTaxInsight.assessment_year == ay_normalized
        ).all()

        matches = db.query(DocumentMatch).filter(
            DocumentMatch.client_id == client_id,
            DocumentMatch.assessment_year == ay_normalized
        ).all()

        tax_intel = {
            "total_tds": summary_rec.total_tds if summary_rec else 0.0,
            "income_summary": {
                "interest": summary_rec.interest_income if summary_rec else 0.0,
                "dividend": summary_rec.dividend_income if summary_rec else 0.0,
                "salary": summary_rec.salary_income if summary_rec else 0.0,
                "securities": summary_rec.securities_transactions if summary_rec else 0.0,
                "mutual_fund": summary_rec.mutual_fund_transactions if summary_rec else 0.0,
                "property": summary_rec.property_transactions if summary_rec else 0.0,
                "sft": summary_rec.sft_transactions if summary_rec else 0.0
            },
            "refund": summary_rec.refund_amount if summary_rec else 0.0,
            "demand": summary_rec.demand_amount if summary_rec else 0.0,
            "high_value_transactions": summary_rec.high_value_transactions if summary_rec else 0,
            "mismatches": [
                {
                    "id": m.id,
                    "match_type": m.match_type,
                    "description": m.description,
                    "amount": m.amount,
                    "status": m.status
                } for m in matches
            ],
            "insights": [
                {
                    "id": ins.id,
                    "severity": ins.severity,
                    "description": ins.description,
                    "confidence": ins.confidence
                } for ins in insights
            ]
        }

        # 5. ITR Preparation
        readiness = db.query(ITRReadiness).filter(
            ITRReadiness.client_id == client_id,
            ITRReadiness.assessment_year == ay_normalized
        ).first()

        action_items = db.query(ITRActionItem).filter(
            ITRActionItem.client_id == client_id,
            ITRActionItem.assessment_year == ay_normalized
        ).all()

        verifications = db.query(ITRVerificationResult).filter(
            ITRVerificationResult.client_id == client_id,
            ITRVerificationResult.assessment_year == ay_normalized
        ).all()

        itr_prep = {
            "readiness_score": readiness.readiness_score if readiness else 0.0,
            "missing_documents": readiness.missing_documents if readiness and readiness.missing_documents else [],
            "verification_checklist": [
                {
                    "id": v.id,
                    "verification_type": v.verification_type,
                    "description": v.description,
                    "status": v.status
                } for v in verifications
            ],
            "pending_actions": [
                {
                    "id": act.id,
                    "action_text": act.action_text,
                    "severity": act.severity,
                    "status": act.status
                } for act in action_items if act.status == "PENDING"
            ],
            "warnings": [
                {
                    "id": act.id,
                    "description": act.action_text,
                    "severity": act.severity
                } for act in action_items if act.severity in ["WARNING", "CRITICAL"]
            ],
            "completion_percentage": readiness.readiness_score if readiness else 0.0
        }

        # 6. Research
        queries = db.query(ResearchQuery).filter(
            ResearchQuery.client_id == client_id
        ).order_by(desc(ResearchQuery.created_at)).limit(10).all()

        bookmarks = db.query(ResearchBookmark).all()
        # Map bookmarks manually containing research sources
        saved_bookmarks = []
        for b in bookmarks:
            src = db.query(ResearchSource).filter(ResearchSource.id == b.source_id).first()
            if src:
                saved_bookmarks.append({
                    "id": b.id,
                    "source_id": b.source_id,
                    "notes": b.notes,
                    "title": src.title,
                    "authority": src.authority
                })

        research_notes = db.query(ResearchNote).filter(
            ResearchNote.client_id == client_id
        ).order_by(desc(ResearchNote.created_at)).all()

        # Context-aware suggestions based on mismatch alerts
        suggestions = ["Verify Rule 36(4) Input Tax Credit matching limits."]
        if matches:
            suggestions.append("Reconcile Section 194A savings interest mismatches.")
        if tax_intel["high_value_transactions"] > 0:
            suggestions.append("Verify high-value SFT transaction compliance requirements.")

        research = {
            "recent_queries": [q.query_text for q in queries],
            "saved_notes": [
                {
                    "id": rn.id,
                    "title": rn.title,
                    "content": rn.content,
                    "section": rn.section_reference,
                    "authority": rn.authority_reference
                } for rn in research_notes
            ],
            "bookmarks": saved_bookmarks,
            "suggestions": suggestions
        }

        # 7. Tasks
        tasks = db.query(ClientTask).filter(
            ClientTask.client_id == client_id
        ).order_by(desc(ClientTask.created_at)).all()

        # 8. Notes (with tags, attachments, mentions JSON parse)
        db_notes = db.query(Note).filter(
            Note.client_id == client_id,
            Note.deleted_at.is_(None)
        ).order_by(desc(Note.created_at)).all()

        parsed_notes = []
        for n in db_notes:
            attachments = []
            if n.attachments_json:
                try:
                    attachments = json.loads(n.attachments_json) if isinstance(n.attachments_json, str) else n.attachments_json
                except Exception:
                    pass
            
            mentions = []
            if n.mentions_json:
                try:
                    mentions = json.loads(n.mentions_json) if isinstance(n.mentions_json, str) else n.mentions_json
                except Exception:
                    pass

            parsed_notes.append({
                "id": n.id,
                "title": n.title,
                "content": n.content,
                "created_by": n.created_by,
                "tags": n.tags,
                "is_pinned": n.is_pinned or False,
                "attachments": attachments,
                "mentions": mentions,
                "created_at": n.created_at,
                "updated_at": n.updated_at
            })

        return {
            "overview": overview,
            "documents": documents_list,
            "tax_intelligence": tax_intel,
            "itr_preparation": itr_prep,
            "research": research,
            "tasks": tasks,
            "notes": parsed_notes,
            "timeline": timeline_events
        }
