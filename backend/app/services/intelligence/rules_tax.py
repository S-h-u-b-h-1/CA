"""Tax Rules — evaluates Form 26AS / AIS / TIS entries per client+assessment-year.

These checks intentionally mirror the thresholds already used by
TaxIntelligenceService.recompute() (app/services/tax_intelligence.py) so the two
systems stay consistent, but they are written natively against the entry tables
here so each suggestion can cite the specific Form26ASEntry/AISEntry/TISEntry
row(s) that triggered it as evidence, rather than a document-level summary.

"Missing deductions" (requested in the product spec) is intentionally NOT
implemented: no data source in this codebase captures a client's deduction
eligibility (80C/80D/HRA/etc.), and inventing one would violate the no-fabrication
mandate. It is listed as NOT_YET_SUPPORTED in the rule registry instead.
"""
from typing import List
from sqlalchemy.orm import Session
from app.models.models import Client, Form26ASEntry, AISEntry, TISEntry
from app.services.intelligence.core import EvidenceItem, SuggestionCandidate


def evaluate(db: Session, client: Client) -> List[SuggestionCandidate]:
    candidates: List[SuggestionCandidate] = []

    years = set()
    for row in db.query(Form26ASEntry.assessment_year).filter(Form26ASEntry.client_id == client.id).distinct():
        if row[0]:
            years.add(row[0])
    for row in db.query(AISEntry.assessment_year).filter(AISEntry.client_id == client.id).distinct():
        if row[0]:
            years.add(row[0])
    for row in db.query(TISEntry.assessment_year).filter(TISEntry.client_id == client.id).distinct():
        if row[0]:
            years.add(row[0])

    for ay in sorted(years):
        candidates.extend(_evaluate_year(db, client, ay))

    return candidates


def _evaluate_year(db: Session, client: Client, ay: str) -> List[SuggestionCandidate]:
    out: List[SuggestionCandidate] = []

    f26 = db.query(Form26ASEntry).filter(Form26ASEntry.client_id == client.id, Form26ASEntry.assessment_year == ay).all()
    ais = db.query(AISEntry).filter(AISEntry.client_id == client.id, AISEntry.assessment_year == ay).all()
    tis = db.query(TISEntry).filter(TISEntry.client_id == client.id, TISEntry.assessment_year == ay).all()

    total_tds = sum(e.tax_deposited or 0.0 for e in f26)
    total_reported = sum(e.reported_value or 0.0 for e in ais)

    # Rule 1: PAN mismatch between 26AS and AIS (CRITICAL)
    pan_26as = {e.pan for e in f26 if e.pan}
    pan_ais = {e.pan for e in ais if e.pan}
    if pan_26as and pan_ais and pan_26as != pan_ais:
        ev = [EvidenceItem("FORM_26AS", f"Form 26AS references PAN(s) {sorted(pan_26as)}.", next(iter(f26)).id if f26 else None)]
        ev += [EvidenceItem("AIS", f"AIS references PAN(s) {sorted(pan_ais)}.", next(iter(ais)).id if ais else None)]
        out.append(SuggestionCandidate(
            rule_key="TAX_PAN_MISMATCH", category="TAX",
            title=f"PAN mismatch between Form 26AS and AIS ({ay})",
            severity="CRITICAL",
            explanation=f"Form 26AS references PAN {sorted(pan_26as)} while AIS references {sorted(pan_ais)} for assessment year {ay}. These should be identical for the same taxpayer.",
            recommendation="Verify the correct PAN was used when fetching both documents; re-download if a wrong PAN was selected.",
            dedup_suffix=ay, evidence=ev,
        ))

    # Rule 2: Assessment year mismatch (HIGH)
    ay_26as = {_norm_ay(e.assessment_year) for e in f26 if e.assessment_year}
    ay_ais = {_norm_ay(e.assessment_year) for e in ais if e.assessment_year}
    if ay_26as and ay_ais and ay_26as != ay_ais:
        ev = [EvidenceItem("FORM_26AS", f"Form 26AS lists AY {sorted(ay_26as)}."), EvidenceItem("AIS", f"AIS lists AY {sorted(ay_ais)}.")]
        out.append(SuggestionCandidate(
            rule_key="TAX_ASSESSMENT_YEAR_MISMATCH", category="TAX",
            title=f"Assessment year mismatch between Form 26AS and AIS ({ay})",
            severity="HIGH",
            explanation=f"Form 26AS lists AY {sorted(ay_26as)} while AIS lists AY {sorted(ay_ais)}.",
            recommendation="Confirm both documents were fetched for the same assessment year before relying on cross-checks between them.",
            dedup_suffix=ay, evidence=ev,
        ))

    # Rule 3: AIS income with no matching 26AS TDS ("Missing TDS")
    has_any_tds = any((e.tax_deposited or 0.0) > 0 for e in f26)
    for e in ais:
        cat = (e.information_category or "").lower()
        val = e.reported_value or 0.0
        if val > 0 and any(kw in cat for kw in ("dividend", "interest", "salary")) and not has_any_tds:
            out.append(SuggestionCandidate(
                rule_key="TAX_MISSING_TDS", category="TAX",
                title=f"Missing TDS for {e.information_category} income ({ay})",
                severity="HIGH",
                explanation=f"AIS reports {e.information_category} income of Rs.{val:,.2f}, but no corresponding TDS deposit was found in Form 26AS for {ay}.",
                recommendation="Confirm with the client/deductor whether TDS was actually deducted; if so, the 26AS may be incomplete or not yet updated.",
                dedup_suffix=f"{ay}:{e.id}",
                evidence=[EvidenceItem("AIS", f"{e.information_category}: Rs.{val:,.2f} reported.", e.id)],
            ))

    # Rule 4: 26AS TDS with no matching AIS income ("Unreported income")
    has_any_ais = len(ais) > 0
    for e in f26:
        tds = e.tax_deposited or 0.0
        if tds > 0 and not has_any_ais:
            out.append(SuggestionCandidate(
                rule_key="TAX_POSSIBLE_UNREPORTED_INCOME", category="TAX",
                title=f"TDS deducted with no matching AIS income entry ({ay})",
                severity="HIGH",
                explanation=f"Form 26AS shows TDS of Rs.{tds:,.2f} deposited by '{e.deductor_name or 'a deductor'}', but no corresponding income appears in AIS for {ay}.",
                recommendation="Check whether the related income was reported elsewhere or is genuinely missing from AIS — this can indicate unreported income or a stale AIS pull.",
                dedup_suffix=f"{ay}:{e.id}",
                evidence=[EvidenceItem("FORM_26AS", f"Deductor '{e.deductor_name}' deposited TDS Rs.{tds:,.2f}.", e.id)],
            ))

    # Rule 5: High TDS concentration in a single deductor (LOW, informational)
    deductor_tds = {}
    for e in f26:
        tan = e.deductor_tan or "Unknown"
        deductor_tds[tan] = deductor_tds.get(tan, 0.0) + (e.tax_deposited or 0.0)
    for tan, val in deductor_tds.items():
        if total_tds > 0 and (val / total_tds) > 0.70:
            out.append(SuggestionCandidate(
                rule_key="TAX_HIGH_TDS_CONCENTRATION", category="TAX",
                title=f"High TDS concentration in one deductor ({ay})",
                severity="LOW",
                explanation=f"Deductor TAN '{tan}' contributes {(val/total_tds)*100:.1f}% of total TDS credit (Rs.{val:,.2f}) for {ay}.",
                recommendation="Informational — worth noting if the client's income sources are expected to be more diversified.",
                dedup_suffix=f"{ay}:{tan}",
                evidence=[EvidenceItem("FORM_26AS", f"TAN '{tan}' = Rs.{val:,.2f} of Rs.{total_tds:,.2f} total TDS.")],
            ))

    # Rule 6: Excess TDS vs reported income (NEW — HIGH)
    if total_tds > 0 and total_reported > 0 and total_tds > total_reported:
        out.append(SuggestionCandidate(
            rule_key="TAX_EXCESS_TDS", category="TAX",
            title=f"Total TDS exceeds total AIS-reported income ({ay})",
            severity="HIGH",
            explanation=f"Total TDS deposited per Form 26AS (Rs.{total_tds:,.2f}) exceeds total income reported in AIS (Rs.{total_reported:,.2f}) for {ay}. This is a logical inconsistency worth investigating — it may indicate excess withholding (a refund opportunity) or incomplete AIS data.",
            recommendation="Reconcile category-by-category; if genuinely excess, this supports a refund claim.",
            dedup_suffix=ay,
            evidence=[EvidenceItem("FORM_26AS", f"Total TDS Rs.{total_tds:,.2f}."), EvidenceItem("AIS", f"Total reported income Rs.{total_reported:,.2f}.")],
        ))

    # Rule 7: Duplicate AIS income entries (NEW — "Duplicate income")
    seen = {}
    for e in ais:
        key = (e.information_category, round(e.reported_value or 0.0, 2), e.source_name)
        if key[1] > 0:
            seen.setdefault(key, []).append(e)
    for key, rows in seen.items():
        if len(rows) > 1:
            out.append(SuggestionCandidate(
                rule_key="TAX_DUPLICATE_AIS_INCOME", category="TAX",
                title=f"Possible duplicate income entries in AIS ({ay})",
                severity="MEDIUM",
                explanation=f"{len(rows)} AIS entries share the same category '{key[0]}', source '{key[2]}', and amount Rs.{key[1]:,.2f} for {ay}. This may be duplicate reporting rather than distinct transactions.",
                recommendation="Verify with the client whether these are genuinely separate transactions before totaling AIS income.",
                dedup_suffix=f"{ay}:{key[0]}:{key[1]}:{key[2]}",
                evidence=[EvidenceItem("AIS", f"{len(rows)}x entries: '{key[0]}' Rs.{key[1]:,.2f}.", rows[0].id)],
            ))

    # Rule 8: Large SFT transaction (MEDIUM)
    sft_total = sum(e.reported_value or 0.0 for e in ais if "sft" in (e.information_category or "").lower())
    if sft_total > 500000:
        out.append(SuggestionCandidate(
            rule_key="TAX_LARGE_SFT_TRANSACTION", category="TAX",
            title=f"Large SFT transactions reported ({ay})",
            severity="MEDIUM",
            explanation=f"AIS reports Specified Financial Transactions totaling Rs.{sft_total:,.2f} for {ay}.",
            recommendation="Review transaction logs to confirm disclosure consistency ahead of filing.",
            dedup_suffix=ay,
            evidence=[EvidenceItem("AIS", f"SFT total Rs.{sft_total:,.2f}.")],
        ))

    # Rule 9: Tax demand outstanding (HIGH)
    demand_total = sum(e.demand or 0.0 for e in f26 if e.demand)
    if demand_total > 0:
        out.append(SuggestionCandidate(
            rule_key="TAX_DEMAND_EXISTS", category="TAX",
            title=f"Outstanding tax demand identified ({ay})",
            severity="HIGH",
            explanation=f"Form 26AS shows an active tax demand of Rs.{demand_total:,.2f} for {ay}.",
            recommendation="Verify the demand with the client and check for a rectification or response deadline.",
            dedup_suffix=ay,
            evidence=[EvidenceItem("FORM_26AS", f"Outstanding demand Rs.{demand_total:,.2f}.")],
        ))

    # Rule 10: Refund available ("Refund opportunities", MEDIUM)
    refund_total = sum(e.refund or 0.0 for e in f26 if e.refund)
    if refund_total > 0:
        out.append(SuggestionCandidate(
            rule_key="TAX_REFUND_AVAILABLE", category="TAX",
            title=f"Refund opportunity identified ({ay})",
            severity="MEDIUM",
            explanation=f"Form 26AS indicates a refund of Rs.{refund_total:,.2f} available/claimed for {ay}.",
            recommendation="Confirm this has been claimed in the client's return, or flag it if the return is still pending.",
            dedup_suffix=ay,
            evidence=[EvidenceItem("FORM_26AS", f"Refund Rs.{refund_total:,.2f}.")],
        ))

    # Rule 11: Duplicate TDS entries in 26AS (MEDIUM)
    dup_seen = {}
    for e in f26:
        key = (e.deductor_tan, e.tax_deposited, e.section_code or e.section)
        if key[0] and key[1] and key[1] > 0:
            dup_seen.setdefault(key, []).append(e)
    for key, rows in dup_seen.items():
        if len(rows) > 1:
            out.append(SuggestionCandidate(
                rule_key="TAX_DUPLICATE_TDS", category="TAX",
                title=f"Possible duplicate TDS entries in Form 26AS ({ay})",
                severity="MEDIUM",
                explanation=f"{len(rows)} entries share deductor TAN '{key[0]}', amount Rs.{key[1]:,.2f}, and section '{key[2]}' for {ay}.",
                recommendation="Confirm these represent distinct deduction events (e.g. different months), not a duplicate row.",
                dedup_suffix=f"{ay}:{key[0]}:{key[1]}:{key[2]}",
                evidence=[EvidenceItem("FORM_26AS", f"{len(rows)}x TAN '{key[0]}' Rs.{key[1]:,.2f}.", rows[0].id)],
            ))

    # TIS Rule A: TIS vs AIS category value mismatch (HIGH)
    ais_by_cat, tis_by_cat = {}, {}
    for e in ais:
        c = (e.information_category or "Other").lower()
        ais_by_cat[c] = ais_by_cat.get(c, 0.0) + (e.reported_value or 0.0)
    for t in tis:
        c = (t.category or "Other").lower()
        tis_by_cat[c] = tis_by_cat.get(c, 0.0) + (t.reported_value or 0.0)
    for cat, tis_val in tis_by_cat.items():
        ais_val = ais_by_cat.get(cat, 0.0)
        if abs(tis_val - ais_val) > 10.0:
            out.append(SuggestionCandidate(
                rule_key="TAX_TIS_AIS_MISMATCH", category="TAX",
                title=f"TIS vs AIS value mismatch: {cat} ({ay})",
                severity="HIGH",
                explanation=f"Category '{cat}' shows Rs.{tis_val:,.2f} in TIS but Rs.{ais_val:,.2f} in AIS for {ay}.",
                recommendation="Reconcile the category before relying on either figure for computation.",
                dedup_suffix=f"{ay}:{cat}",
                evidence=[EvidenceItem("TIS", f"'{cat}' = Rs.{tis_val:,.2f}."), EvidenceItem("AIS", f"'{cat}' = Rs.{ais_val:,.2f}.")],
            ))

    # TIS Rule B: feedback value vs derived value (MEDIUM)
    for t in tis:
        if abs((t.feedback_value or 0.0) - (t.derived_value or 0.0)) > 10.0:
            out.append(SuggestionCandidate(
                rule_key="TAX_TIS_FEEDBACK_MISMATCH", category="TAX",
                title=f"TIS feedback value differs from derived value ({ay})",
                severity="MEDIUM",
                explanation=f"'{t.category}' / '{t.subcategory}': feedback value Rs.{t.feedback_value:,.2f} differs from derived value Rs.{t.derived_value:,.2f}.",
                recommendation="Client-submitted feedback on TIS may not have been reflected upstream — verify before filing.",
                dedup_suffix=f"{ay}:{t.id}",
                evidence=[EvidenceItem("TIS", f"Feedback Rs.{t.feedback_value:,.2f} vs derived Rs.{t.derived_value:,.2f}.", t.id)],
            ))

    # TIS Rule C: high-value TIS transaction (MEDIUM)
    for t in tis:
        if (t.reported_value or 0.0) > 500000.0:
            out.append(SuggestionCandidate(
                rule_key="TAX_TIS_HIGH_VALUE", category="TAX",
                title=f"High-value TIS transaction ({ay})",
                severity="MEDIUM",
                explanation=f"TIS reports Rs.{t.reported_value:,.2f} under '{t.category}' for {ay}.",
                recommendation="Check return schedule disclosures for this transaction.",
                dedup_suffix=f"{ay}:{t.id}",
                evidence=[EvidenceItem("TIS", f"'{t.category}' = Rs.{t.reported_value:,.2f}.", t.id)],
            ))

    return out


def _norm_ay(y: str) -> str:
    return f"{y[:4]}-{y[7:]}" if len(y) == 9 else y
