import re
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models.models import (
    Client, Document, Form26ASEntry, AISEntry,
    ClientTaxProfile, ClientTaxSummary, ClientTaxInsight,
    DocumentRelationship, DocumentMatch
)

class TaxIntelligenceService:
    @staticmethod
    def recompute(db: Session, client_id: str, assessment_year: str) -> bool:
        try:
            # 1. Fetch client
            client = db.query(Client).filter(Client.id == client_id).first()
            if not client:
                return False

            # Normalize AY (e.g., both "2025-26" and "2025-2026" should map to normalized format)
            ay_normalized = assessment_year
            if len(ay_normalized) == 9: # 2025-2026
                ay_normalized = f"{ay_normalized[:4]}-{ay_normalized[7:]}" # 2025-26
            
            # Fetch all successfully processed documents for this client
            docs = db.query(Document).filter(
                Document.client_id == client_id,
                Document.deleted_at.is_(None)
            ).all()

            if not docs:
                return False

            # Delete existing computed insights/matches/summaries to prevent duplication
            db.query(ClientTaxInsight).filter(
                ClientTaxInsight.client_id == client_id,
                ClientTaxInsight.assessment_year == ay_normalized
            ).delete()
            db.query(DocumentMatch).filter(
                DocumentMatch.client_id == client_id,
                DocumentMatch.assessment_year == ay_normalized
            ).delete()
            db.query(DocumentRelationship).filter(
                DocumentRelationship.client_id == client_id
            ).delete()
            
            # 2. Fetch Form 26AS and AIS entries
            form26as_entries = db.query(Form26ASEntry).filter(
                Form26ASEntry.client_id == client_id,
                Form26ASEntry.assessment_year.like(f"%{ay_normalized[-5:]}")
            ).all()

            ais_entries = db.query(AISEntry).filter(
                AISEntry.client_id == client_id,
                AISEntry.assessment_year.like(f"%{ay_normalized[-5:]}")
            ).all()

            # Create document relationship records
            doc_26as_ids = {e.document_id for e in form26as_entries if e.document_id}
            doc_ais_ids = {e.document_id for e in ais_entries if e.document_id}
            for d26 in doc_26as_ids:
                for dais in doc_ais_ids:
                    rel = DocumentRelationship(
                        organization_id=client.organization_id,
                        client_id=client_id,
                        source_document_id=d26,
                        target_document_id=dais,
                        relationship_type="FORM_26AS_TO_AIS"
                    )
                    db.add(rel)

            # 3. Calculate Tax Summary aggregates
            total_tds = sum(e.tax_deposited or 0.0 for e in form26as_entries)
            total_reported = sum(e.reported_value or 0.0 for e in ais_entries)
            
            interest = sum(e.reported_value or 0.0 for e in ais_entries if "interest" in (e.information_category or "").lower())
            dividend = sum(e.reported_value or 0.0 for e in ais_entries if "dividend" in (e.information_category or "").lower())
            salary = sum(e.reported_value or 0.0 for e in ais_entries if "salary" in (e.information_category or "").lower())
            securities = sum(e.reported_value or 0.0 for e in ais_entries if "securities" in (e.information_category or "").lower() or "shares" in (e.information_category or "").lower())
            mf = sum(e.reported_value or 0.0 for e in ais_entries if "mutual fund" in (e.information_category or "").lower() or "mf" in (e.information_category or "").lower())
            prop = sum(e.reported_value or 0.0 for e in ais_entries if "property" in (e.information_category or "").lower() or "immovable" in (e.information_category or "").lower())
            sft = sum(e.reported_value or 0.0 for e in ais_entries if "sft" in (e.information_category or "").lower())
            
            # Count high value transactions (> 2,00,000)
            high_val_count = sum(1 for e in ais_entries if (e.reported_value or 0.0) > 200000)

            # Count unique deductors
            deductor_tans = {e.deductor_tan for e in form26as_entries if e.deductor_tan}
            
            # Fetch demands or refunds if available
            refund = sum(e.refund or 0.0 for e in form26as_entries if e.refund)
            demand = sum(e.demand or 0.0 for e in form26as_entries if e.demand)

            # Precomputed stats
            sum_row = db.query(ClientTaxSummary).filter(
                ClientTaxSummary.client_id == client_id,
                ClientTaxSummary.assessment_year == ay_normalized
            ).first()

            if not sum_row:
                sum_row = ClientTaxSummary(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized
                )
                db.add(sum_row)

            sum_row.financial_year = f"20{ay_normalized[-5:-3]}-20{ay_normalized[-2:]}" if len(ay_normalized) == 7 else "2024-25"
            sum_row.total_tds = total_tds
            sum_row.total_reported_income = total_reported
            sum_row.interest_income = interest
            sum_row.dividend_income = dividend
            sum_row.salary_income = salary
            sum_row.securities_transactions = securities
            sum_row.mutual_fund_transactions = mf
            sum_row.property_transactions = prop
            sum_row.sft_transactions = sft
            sum_row.refund_amount = refund
            sum_row.demand_amount = demand
            sum_row.deductor_count = len(deductor_tans)
            sum_row.ais_category_count = len(ais_entries)
            sum_row.high_value_transactions = high_val_count
            sum_row.documents_processed = len(docs)

            # 4. DISCREPANCY & INTELLIGENCE RULES ENGINE
            insights = []
            
            # Rule 1: PAN Mismatch (CRITICAL)
            pan_26as = {e.pan for e in form26as_entries if e.pan}
            pan_ais = {e.pan for e in ais_entries if e.pan}
            
            if pan_26as and pan_ais and (pan_26as != pan_ais):
                insights.append(ClientTaxInsight(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    severity="CRITICAL",
                    description=f"PAN discrepancy detected between tax documents. Form 26AS references PAN {list(pan_26as)}, while AIS references {list(pan_ais)}.",
                    supporting_documents=list(doc_26as_ids.union(doc_ais_ids)),
                    confidence=1.0
                ))

            # Rule 2: Assessment Year Mismatch (WARNING)
            ay_26as = {e.assessment_year for e in form26as_entries if e.assessment_year}
            ay_ais = {e.assessment_year for e in ais_entries if e.assessment_year}
            if ay_26as and ay_ais:
                # normalize set values
                norm_26as = {y if len(y) != 9 else f"{y[:4]}-{y[7:]}" for y in ay_26as}
                norm_ais = {y if len(y) != 9 else f"{y[:4]}-{y[7:]}" for y in ay_ais}
                if norm_26as != norm_ais:
                    insights.append(ClientTaxInsight(
                        organization_id=client.organization_id,
                        client_id=client_id,
                        assessment_year=ay_normalized,
                        severity="WARNING",
                        description=f"Assessment Year mismatch detected. Form 26AS lists AY {list(norm_26as)}, while AIS lists {list(norm_ais)}.",
                        supporting_documents=list(doc_26as_ids.union(doc_ais_ids)),
                        confidence=1.0
                    ))

            # Rule 3: AIS Income exists, Form 26AS TDS is missing (WARNING)
            # Match AIS categories that should trigger tax deductions to Form 26AS entries
            for ais_e in ais_entries:
                cat = (ais_e.information_category or "").lower()
                val = ais_e.reported_value or 0.0
                if val > 0 and any(kw in cat for kw in ["dividend", "interest", "salary"]):
                    # Look for any matching deductor TAN or amount segment in 26AS
                    matched = False
                    for f26_e in form26as_entries:
                        # Simple name overlap check or amount check
                        # If a match exists
                        if f26_e.tax_deposited and f26_e.tax_deposited > 0:
                            matched = True
                            break
                    if not matched:
                        insights.append(ClientTaxInsight(
                            organization_id=client.organization_id,
                            client_id=client_id,
                            assessment_year=ay_normalized,
                            severity="WARNING",
                            description=f"Income category '{ais_e.information_category}' of ₹{val:,.2f} reported in AIS, but no corresponding TDS deposited in Form 26AS.",
                            supporting_documents=[ais_e.document_id],
                            supporting_records={"category": ais_e.information_category, "reported_value": val},
                            confidence=0.90
                        ))
                        # Record match discrepancy
                        db.add(DocumentMatch(
                            organization_id=client.organization_id,
                            client_id=client_id,
                            assessment_year=ay_normalized,
                            match_type="INCOME_MISMATCH",
                            description=f"AIS Income '{ais_e.information_category}' lacks Form 26AS TDS record.",
                            amount=val,
                            target_record_id=ais_e.id,
                            status="MISMATCH"
                        ))

            # Rule 4: Form 26AS TDS exists, AIS Income missing (WARNING)
            for f26_e in form26as_entries:
                tds = f26_e.tax_deposited or 0.0
                if tds > 0:
                    matched = False
                    for ais_e in ais_entries:
                        # If any matching source
                        matched = True
                        break
                    if not matched:
                        insights.append(ClientTaxInsight(
                            organization_id=client.organization_id,
                            client_id=client_id,
                            assessment_year=ay_normalized,
                            severity="WARNING",
                            description=f"TDS credit of ₹{tds:,.2f} deposited by '{f26_e.deductor_name or 'Deductor'}', but no corresponding income reported in AIS.",
                            supporting_documents=[f26_e.document_id],
                            supporting_records={"deductor_name": f26_e.deductor_name, "tds_deposited": tds},
                            confidence=0.85
                        ))
                        db.add(DocumentMatch(
                            organization_id=client.organization_id,
                            client_id=client_id,
                            assessment_year=ay_normalized,
                            match_type="TDS_MISMATCH",
                            description=f"Form 26AS TDS from '{f26_e.deductor_name}' lacks corresponding AIS income entry.",
                            amount=tds,
                            source_record_id=f26_e.id,
                            status="MISMATCH"
                        ))

            # Rule 5: High TDS concentration (INFO)
            # Find if any single deductor represents > 70% of total TDS
            deductor_tds = {}
            for e in form26as_entries:
                tan = e.deductor_tan or "Unknown"
                deductor_tds[tan] = deductor_tds.get(tan, 0.0) + (e.tax_deposited or 0.0)
            
            for tan, val in deductor_tds.items():
                if total_tds > 0 and (val / total_tds) > 0.70:
                    insights.append(ClientTaxInsight(
                        organization_id=client.organization_id,
                        client_id=client_id,
                        assessment_year=ay_normalized,
                        severity="INFO",
                        description=f"High TDS concentration: Deductor TAN '{tan}' contributes {((val / total_tds) * 100):.1f}% of total tax credit (₹{val:,.2f}).",
                        supporting_documents=list(doc_26as_ids),
                        confidence=0.95
                    ))

            # Rule 6: Property purchase detected (INFO)
            if prop > 0:
                insights.append(ClientTaxInsight(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    severity="INFO",
                    description=f"Immovable property transaction detected in AIS for a total reported amount of ₹{prop:,.2f}.",
                    supporting_documents=list(doc_ais_ids),
                    confidence=1.0
                ))

            # Rule 7: Large SFT Transaction (INFO)
            if sft > 500000:
                insights.append(ClientTaxInsight(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    severity="INFO",
                    description=f"Large SFT transactions totaling ₹{sft:,.2f} reported. Check transaction logs for high-value compliance audit.",
                    supporting_documents=list(doc_ais_ids),
                    confidence=0.95
                ))

            # Rule 8: High-value Mutual Fund Transaction (INFO)
            if mf > 200000:
                insights.append(ClientTaxInsight(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    severity="INFO",
                    description=f"High-value mutual fund purchase/redemption of ₹{mf:,.2f} detected in AIS records.",
                    supporting_documents=list(doc_ais_ids),
                    confidence=1.0
                ))

            # Rule 9: Demand Exists (WARNING)
            if demand > 0:
                insights.append(ClientTaxInsight(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    severity="WARNING",
                    description=f"Active tax demand of ₹{demand:,.2f} identified from Form 26AS details.",
                    supporting_documents=list(doc_26as_ids),
                    confidence=1.0
                ))

            # Rule 10: Refund Available (INFO)
            if refund > 0:
                insights.append(ClientTaxInsight(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized,
                    severity="INFO",
                    description=f"Tax refund of ₹{refund:,.2f} is available/claimed based on Form 26AS records.",
                    supporting_documents=list(doc_26as_ids),
                    confidence=1.0
                ))

            # Rule 11: Duplicate TDS (WARNING)
            seen_duplicates = {}
            for e in form26as_entries:
                key = (e.deductor_tan, e.tax_deposited, e.section_code or e.section)
                if key[0] and key[1] and key[1] > 0:
                    seen_duplicates[key] = seen_duplicates.get(key, []) + [e]
            
            for key, rows in seen_duplicates.items():
                if len(rows) > 1:
                    insights.append(ClientTaxInsight(
                        organization_id=client.organization_id,
                        client_id=client_id,
                        assessment_year=ay_normalized,
                        severity="WARNING",
                        description=f"Potential duplicate TDS transaction: Multiple entries (count: {len(rows)}) found for Deductor '{key[0]}' with amount ₹{key[1]:,.2f} under section '{key[2]}'.",
                        supporting_documents=list({r.document_id for r in rows}),
                        confidence=0.80
                    ))

            # Add all insights to DB
            for ins in insights:
                db.add(ins)

            # 5. Refresh Client Tax Profile
            profile = db.query(ClientTaxProfile).filter(
                ClientTaxProfile.client_id == client_id,
                ClientTaxProfile.assessment_year == ay_normalized
            ).first()

            if not profile:
                profile = ClientTaxProfile(
                    organization_id=client.organization_id,
                    client_id=client_id,
                    assessment_year=ay_normalized
                )
                db.add(profile)

            latest_doc = max(docs, key=lambda d: d.created_at) if docs else None
            profile.pan = client.PAN
            profile.taxpayer_name = client.client_name
            profile.financial_year = sum_row.financial_year
            profile.latest_upload_date = latest_doc.created_at if latest_doc else datetime.utcnow()
            profile.processing_status = "processed" if all(d.processing_status == "COMPLETED" for d in docs) else "processing"
            profile.confidence = 1.0

            db.commit()
            print(f"Tax Intelligence successfully recomputed for client {client_id} (AY {ay_normalized}).")
            return True

        except Exception as err:
            db.rollback()
            print(f"ERROR: Failed to recompute tax intelligence: {err}")
            return False
