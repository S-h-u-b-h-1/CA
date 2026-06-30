from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.models import (
    Client, Document, ClientTaxProfile, ClientTaxSummary, ClientTaxInsight,
    ITRProfile, ITRReadiness, ITRActionItem, ITRVerificationResult
)

class ITRPreparationService:
    @staticmethod
    def recompute(db: Session, client_id: str, assessment_year: str) -> bool:
        try:
            client = db.query(Client).filter(Client.id == client_id).first()
            if not client:
                return False

            ay_normalized = assessment_year
            if len(ay_normalized) == 9: # 2025-2026
                ay_normalized = f"{ay_normalized[:4]}-{ay_normalized[7:]}" # 2025-26

            # Delete old records
            db.query(ITRProfile).filter(
                ITRProfile.client_id == client_id,
                ITRProfile.assessment_year == ay_normalized
            ).delete()
            db.query(ITRReadiness).filter(
                ITRReadiness.client_id == client_id,
                ITRReadiness.assessment_year == ay_normalized
            ).delete()
            db.query(ITRActionItem).filter(
                ITRActionItem.client_id == client_id,
                ITRActionItem.assessment_year == ay_normalized
            ).delete()
            db.query(ITRVerificationResult).filter(
                ITRVerificationResult.client_id == client_id,
                ITRVerificationResult.assessment_year == ay_normalized
            ).delete()

            # Fetch precalculated structures
            summary = db.query(ClientTaxSummary).filter(
                ClientTaxSummary.client_id == client_id,
                ClientTaxSummary.assessment_year == ay_normalized
            ).first()

            insights = db.query(ClientTaxInsight).filter(
                ClientTaxInsight.client_id == client_id,
                ClientTaxInsight.assessment_year == ay_normalized
            ).all()

            docs = db.query(Document).filter(
                Document.client_id == client_id,
                Document.deleted_at.is_(None)
            ).all()

            # 1. Document checklist & completeness
            categories_uploaded = {d.category for d in docs if d.category}
            
            # Match rules
            required_docs = ["Form 26AS", "AIS", "Form 16", "Bank Statement"]
            collected_docs = []
            missing_docs = []
            
            for req in required_docs:
                # category matching check
                matched = False
                for cat in categories_uploaded:
                    if req.lower() in cat.lower() or cat.lower() in req.lower():
                        matched = True
                        break
                if matched:
                    collected_docs.append(req)
                else:
                    missing_docs.append(req)

            completeness_score = (len(collected_docs) / len(required_docs)) * 100.0

            # 2. Verification checklist
            verifications = []
            
            # Check 1: PAN Consistency
            pan_mismatch = any("PAN discrepancy" in ins.description for ins in insights)
            if pan_mismatch:
                verifications.append(ITRVerificationResult(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    verification_type="PAN_CONSISTENCY",
                    description="PAN values discrepancy detected across uploaded tax files.",
                    status="FAIL"
                ))
            else:
                verifications.append(ITRVerificationResult(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    verification_type="PAN_CONSISTENCY",
                    description="PAN references are consistent across all documents.",
                    status="PASS"
                ))

            # Check 2: AY Consistency
            ay_mismatch = any("Assessment Year mismatch" in ins.description for ins in insights)
            if ay_mismatch:
                verifications.append(ITRVerificationResult(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    verification_type="AY_CONSISTENCY",
                    description=f"Assessment Year mismatch flagged on uploaded tax files.",
                    status="FAIL"
                ))
            else:
                verifications.append(ITRVerificationResult(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    verification_type="AY_CONSISTENCY",
                    description=f"Assessment Year references are consistent with AY {ay_normalized}.",
                    status="PASS"
                ))

            # Check 3: Duplicate transactions
            duplicates_exist = any("duplicate" in ins.description.lower() for ins in insights)
            if duplicates_exist:
                verifications.append(ITRVerificationResult(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    verification_type="DUPLICATE_CHECK",
                    description="Potential duplicate TDS/transaction entries identified in source files.",
                    status="WARNING"
                ))
            else:
                verifications.append(ITRVerificationResult(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    verification_type="DUPLICATE_CHECK",
                    description="No duplicate transaction records detected.",
                    status="PASS"
                ))

            # Check 4: Interest Income Verification
            interest_mis = any("interest income" in ins.description.lower() or "saving bank interest" in ins.description.lower() for ins in insights)
            if interest_mis and summary and summary.interest_income > 0:
                verifications.append(ITRVerificationResult(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    verification_type="INTEREST_VERIFICATION",
                    description=f"Interest income of ₹{summary.interest_income:,.2f} reported in AIS lacks corresponding TDS in Form 26AS.",
                    status="WARNING"
                ))
            else:
                verifications.append(ITRVerificationResult(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    verification_type="INTEREST_VERIFICATION",
                    description="Interest income verified without mismatch.",
                    status="PASS"
                ))

            # Check 5: Dividend Income Verification
            div_mis = any("dividend" in ins.description.lower() for ins in insights)
            if div_mis and summary and summary.dividend_income > 0:
                verifications.append(ITRVerificationResult(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    verification_type="DIVIDEND_VERIFICATION",
                    description=f"Dividend income of ₹{summary.dividend_income:,.2f} reported in AIS lacks corresponding TDS in Form 26AS.",
                    status="WARNING"
                ))
            else:
                verifications.append(ITRVerificationResult(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    verification_type="DIVIDEND_VERIFICATION",
                    description="Dividend income verified without mismatch.",
                    status="PASS"
                ))

            # Check 6: Missing Supporting Documents
            if missing_docs:
                verifications.append(ITRVerificationResult(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    verification_type="SUPPORTING_DOCUMENTS",
                    description=f"Missing key tax documents: {', '.join(missing_docs)}.",
                    status="WARNING"
                ))
            else:
                verifications.append(ITRVerificationResult(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    verification_type="SUPPORTING_DOCUMENTS",
                    description="All standard supporting documents uploaded.",
                    status="PASS"
                ))

            # Check 7: Unexpected High-Value Transactions
            has_high_val = (summary.high_value_transactions > 0) if summary else False
            if has_high_val:
                verifications.append(ITRVerificationResult(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    verification_type="HIGH_VALUE_TRANSACTION_CHECK",
                    description=f"Identified high-value transactions (>₹2L) that require audit disclosure.",
                    status="WARNING"
                ))
            else:
                verifications.append(ITRVerificationResult(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    verification_type="HIGH_VALUE_TRANSACTION_CHECK",
                    description="No unexpected high-value transaction alerts.",
                    status="PASS"
                ))

            # 3. ITR Readiness Score
            readiness_score = 100.0
            reasons = []
            
            # Deduct weights
            if "Form 26AS" in missing_docs:
                readiness_score -= 30.0
                reasons.append({"text": "Form 26AS is missing", "status": "FAIL"})
            else:
                reasons.append({"text": "Form 26AS is available", "status": "READY"})
                
            if "AIS" in missing_docs:
                readiness_score -= 30.0
                reasons.append({"text": "AIS is missing", "status": "FAIL"})
            else:
                reasons.append({"text": "AIS is available", "status": "READY"})

            if "Form 16" in missing_docs:
                readiness_score -= 20.0
                reasons.append({"text": "Form 16 salary summary is missing", "status": "FAIL"})
            else:
                reasons.append({"text": "Form 16 salary summary is available", "status": "READY"})
                
            if "Bank Statement" in missing_docs:
                readiness_score -= 15.0
                reasons.append({"text": "Bank Statement is missing", "status": "FAIL"})
            else:
                reasons.append({"text": "Bank Statement is available", "status": "READY"})

            if pan_mismatch:
                readiness_score -= 20.0
                reasons.append({"text": "PAN consistency checks failed", "status": "FAIL"})
            else:
                reasons.append({"text": "PAN verification passed", "status": "READY"})

            if ay_mismatch:
                readiness_score -= 15.0
                reasons.append({"text": "Assessment Year mismatch flagged", "status": "FAIL"})

            if interest_mis:
                readiness_score -= 10.0
                reasons.append({"text": "Interest income discrepancy between AIS and Form 26AS", "status": "FAIL"})

            if div_mis:
                readiness_score -= 10.0
                reasons.append({"text": "Dividend income discrepancy between AIS and Form 26AS", "status": "FAIL"})

            readiness_score = max(0.0, min(100.0, readiness_score))

            # 4. Action Items Generator
            action_items = []
            for req in missing_docs:
                action_items.append(ITRActionItem(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    action_text=f"Collect {req} document to complete return preparation.",
                    severity="CRITICAL" if req in ["Form 26AS", "AIS"] else "WARNING",
                    reference_document=req,
                    status="PENDING"
                ))

            if interest_mis and summary:
                action_items.append(ITRActionItem(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    action_text=f"Verify interest income of ₹{summary.interest_income:,.2f} reported in AIS but missing matching TDS credit.",
                    severity="WARNING",
                    reference_document="AIS",
                    status="PENDING"
                ))

            if div_mis and summary:
                action_items.append(ITRActionItem(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    action_text=f"Verify dividend income of ₹{summary.dividend_income:,.2f} reported in AIS but missing matching TDS credit.",
                    severity="WARNING",
                    reference_document="AIS",
                    status="PENDING"
                ))

            if pan_mismatch:
                action_items.append(ITRActionItem(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    action_text="Resolve client PAN verification errors across uploaded files.",
                    severity="CRITICAL",
                    reference_document="Form 26AS",
                    status="PENDING"
                ))

            if has_high_val and summary:
                action_items.append(ITRActionItem(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    action_text=f"Audit {summary.high_value_transactions} high-value transactions flagged in AIS for required schedule disclosures.",
                    severity="INFO",
                    reference_document="AIS",
                    status="PENDING"
                ))

            # Save everything
            for v in verifications:
                db.add(v)
            for a in action_items:
                db.add(a)

            # Profile creation/update
            prof_row = ITRProfile(
                organization_id=client.organization_id,
                client_id=client_id,
                assessment_year=ay_normalized,
                financial_year=f"20{ay_normalized[-5:-3]}-20{ay_normalized[-2:]}" if len(ay_normalized) == 7 else "2024-25",
                itr_status="READY_TO_PREPARE" if readiness_score >= 80.0 else "PENDING_DOCUMENTS",
                documents_uploaded=collected_docs,
                data_completeness_score=completeness_score,
                processing_status="COMPLETED",
                confidence=1.0
            )
            db.add(prof_row)

            readiness_row = ITRReadiness(
                organization_id=client.organization_id,
                client_id=client_id,
                assessment_year=ay_normalized,
                readiness_score=readiness_score,
                reasons=reasons,
                collected_documents=collected_docs,
                missing_documents=missing_docs
            )
            db.add(readiness_row)

            db.commit()
            print(f"ITR Preparation successfully recomputed for client {client_id} (AY {ay_normalized}). Score: {readiness_score}%")
            return True

        except Exception as e:
            db.rollback()
            print(f"ERROR: Failed to recompute ITR preparation: {e}")
            return False
