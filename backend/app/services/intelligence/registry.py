"""Rule registry — documents every rule the Intelligence Engine knows about,
including ones that are intentionally NOT implemented, and why. Mirrors the
pattern used by compliance_rules.py's COMPLIANCE_TYPE_REGISTRY: make limitations
visible through the API instead of silently doing nothing or inventing a rule.
"""

CONFIDENCE_BASIS = (
    "Derived automatically from the number of distinct real data-source types "
    "cited as evidence: 2+ sources = HIGH, 1 source = MEDIUM, none = LOW. Never "
    "set directly by a rule."
)

RULE_REGISTRY = [
    # --- Tax Rules (app/services/intelligence/rules_tax.py) ---
    {"rule_key": "TAX_PAN_MISMATCH", "category": "TAX", "title": "PAN mismatch between Form 26AS and AIS", "status": "ACTIVE",
     "description": "Flags when Form 26AS and AIS reference different PANs for the same assessment year.",
     "data_sources_used": ["Form26ASEntry", "AISEntry"], "confidence_basis": CONFIDENCE_BASIS},
    {"rule_key": "TAX_ASSESSMENT_YEAR_MISMATCH", "category": "TAX", "title": "Assessment year mismatch", "status": "ACTIVE",
     "description": "Flags when Form 26AS and AIS were fetched for different assessment years.",
     "data_sources_used": ["Form26ASEntry", "AISEntry"], "confidence_basis": CONFIDENCE_BASIS},
    {"rule_key": "TAX_MISSING_TDS", "category": "TAX", "title": "Missing TDS", "status": "ACTIVE",
     "description": "AIS reports salary/interest/dividend income with no corresponding TDS deposit in Form 26AS.",
     "data_sources_used": ["AISEntry", "Form26ASEntry"], "confidence_basis": CONFIDENCE_BASIS},
    {"rule_key": "TAX_POSSIBLE_UNREPORTED_INCOME", "category": "TAX", "title": "Unreported income", "status": "ACTIVE",
     "description": "Form 26AS shows TDS deposited with no matching AIS income entry at all.",
     "data_sources_used": ["Form26ASEntry", "AISEntry"], "confidence_basis": CONFIDENCE_BASIS},
    {"rule_key": "TAX_EXCESS_TDS", "category": "TAX", "title": "Excess TDS", "status": "ACTIVE",
     "description": "Total TDS deposited exceeds total AIS-reported income for the year — possible excess withholding.",
     "data_sources_used": ["Form26ASEntry", "AISEntry"], "confidence_basis": CONFIDENCE_BASIS},
    {"rule_key": "TAX_DUPLICATE_AIS_INCOME", "category": "TAX", "title": "Duplicate income", "status": "ACTIVE",
     "description": "Multiple AIS entries share the same category, source, and amount — possible duplicate reporting.",
     "data_sources_used": ["AISEntry"], "confidence_basis": CONFIDENCE_BASIS},
    {"rule_key": "TAX_DUPLICATE_TDS", "category": "TAX", "title": "Duplicate TDS entries", "status": "ACTIVE",
     "description": "Multiple Form 26AS entries share the same deductor, amount, and section.",
     "data_sources_used": ["Form26ASEntry"], "confidence_basis": CONFIDENCE_BASIS},
    {"rule_key": "TAX_REFUND_AVAILABLE", "category": "TAX", "title": "Refund opportunities", "status": "ACTIVE",
     "description": "Form 26AS indicates an available/claimed refund for the year.",
     "data_sources_used": ["Form26ASEntry"], "confidence_basis": CONFIDENCE_BASIS},
    {"rule_key": "TAX_DEMAND_EXISTS", "category": "TAX", "title": "Outstanding tax demand", "status": "ACTIVE",
     "description": "Form 26AS shows an active tax demand for the year.",
     "data_sources_used": ["Form26ASEntry"], "confidence_basis": CONFIDENCE_BASIS},
    {"rule_key": "TAX_HIGH_TDS_CONCENTRATION", "category": "TAX", "title": "High TDS concentration", "status": "ACTIVE",
     "description": "A single deductor accounts for over 70% of total TDS credit.",
     "data_sources_used": ["Form26ASEntry"], "confidence_basis": CONFIDENCE_BASIS},
    {"rule_key": "TAX_LARGE_SFT_TRANSACTION", "category": "TAX", "title": "Large SFT transactions", "status": "ACTIVE",
     "description": "Specified Financial Transactions reported in AIS exceed Rs.5,00,000.",
     "data_sources_used": ["AISEntry"], "confidence_basis": CONFIDENCE_BASIS},
    {"rule_key": "TAX_TIS_AIS_MISMATCH", "category": "TAX", "title": "TIS mismatch / AIS mismatch", "status": "ACTIVE",
     "description": "TIS and AIS report different values for the same income category.",
     "data_sources_used": ["TISEntry", "AISEntry"], "confidence_basis": CONFIDENCE_BASIS},
    {"rule_key": "TAX_TIS_FEEDBACK_MISMATCH", "category": "TAX", "title": "TIS feedback mismatch", "status": "ACTIVE",
     "description": "A TIS entry's feedback value differs from its derived value.",
     "data_sources_used": ["TISEntry"], "confidence_basis": CONFIDENCE_BASIS},
    {"rule_key": "TAX_TIS_HIGH_VALUE", "category": "TAX", "title": "High-value TIS transaction", "status": "ACTIVE",
     "description": "A single TIS entry exceeds Rs.5,00,000.",
     "data_sources_used": ["TISEntry"], "confidence_basis": CONFIDENCE_BASIS},
    {"rule_key": "TAX_MISSING_DEDUCTIONS", "category": "TAX", "title": "Missing deductions", "status": "NOT_YET_SUPPORTED",
     "description": "Would flag likely-eligible but unclaimed deductions (80C/80D/HRA/etc.).",
     "data_sources_used": [], "confidence_basis": CONFIDENCE_BASIS,
     "limitations": "No data source in this codebase captures a client's deduction eligibility or claims — nothing parses investment proofs, insurance premiums, or rent receipts into a structured deduction-claim record. Building this rule today would require inventing assumptions about the client's finances rather than reading them from real data."},

    # --- Compliance Rules (app/services/intelligence/rules_compliance.py) ---
    {"rule_key": "COMPLIANCE_MISSING_PROFILE", "category": "COMPLIANCE", "title": "Missing compliance profile", "status": "ACTIVE",
     "description": "Client has zero registered compliance types (GST, Income Tax, TDS, etc.).",
     "data_sources_used": ["ComplianceProfile"], "confidence_basis": CONFIDENCE_BASIS},
    {"rule_key": "COMPLIANCE_OVERDUE_TASK", "category": "COMPLIANCE", "title": "Overdue filings", "status": "ACTIVE",
     "description": "A compliance task's due date has passed without completion. Escalates to CRITICAL past 30 days overdue.",
     "data_sources_used": ["ComplianceTask", "ComplianceProfile"], "confidence_basis": CONFIDENCE_BASIS},
    {"rule_key": "COMPLIANCE_UPCOMING_DUE", "category": "COMPLIANCE", "title": "Upcoming due dates", "status": "ACTIVE",
     "description": "A compliance task is due within 7 days.",
     "data_sources_used": ["ComplianceTask", "ComplianceProfile"], "confidence_basis": CONFIDENCE_BASIS},
    {"rule_key": "COMPLIANCE_HIGH_RISK_CLIENT", "category": "COMPLIANCE", "title": "High-risk client", "status": "ACTIVE",
     "description": "A HIGH risk_level compliance profile has 2+ overdue tasks.",
     "data_sources_used": ["ComplianceProfile", "ComplianceTask"], "confidence_basis": CONFIDENCE_BASIS},
    {"rule_key": "COMPLIANCE_MISSING_REGISTRATION", "category": "COMPLIANCE", "title": "Missing registrations", "status": "NOT_YET_SUPPORTED",
     "description": "Would flag when a client appears to lack a required statutory registration (e.g. GSTIN).",
     "data_sources_used": [], "confidence_basis": CONFIDENCE_BASIS,
     "limitations": "Client.GSTIN/PAN/TAN are optional fields with no UI-enforced entry — a real audit found these are frequently NULL even for properly-registered clients simply because the create-client form doesn't collect them consistently. A NULL field can't be distinguished from 'not registered', so this would produce false positives. Covered indirectly today by COMPLIANCE_MISSING_PROFILE, which is grounded in an explicit user action (configuring a profile) rather than an ambiguous NULL."},

    # --- Document Rules (app/services/intelligence/rules_documents.py) ---
    {"rule_key": "DOCUMENT_MISSING", "category": "DOCUMENTS", "title": "Missing documents", "status": "ACTIVE",
     "description": "A document type expected given the client's type/compliance profiles (Form 16, Form 26AS, Bank Statement, GSTR-3B, Balance Sheet, Profit & Loss) has not been uploaded.",
     "data_sources_used": ["Document", "ComplianceProfile", "Client"], "confidence_basis": CONFIDENCE_BASIS},
    {"rule_key": "DOCUMENT_EXPIRED", "category": "DOCUMENTS", "title": "Expired supporting documents", "status": "NOT_YET_SUPPORTED",
     "description": "Would flag documents past a validity period.",
     "data_sources_used": [], "confidence_basis": CONFIDENCE_BASIS,
     "limitations": "The Document model captures no validity/expiry metadata, and document validity periods vary by type and are often not fixed in law at all. Only upload recency is trackable today; a generic staleness heuristic was deliberately not built here to avoid implying an authoritative 'expired' status that isn't grounded in real expiry rules."},

    # --- Authority Update Rules (app/services/intelligence/rules_authority_updates.py) ---
    {"rule_key": "RESEARCH_AUTHORITY_UPDATE_MATCH", "category": "RESEARCH", "title": "Relevant authority update", "status": "ACTIVE",
     "description": "A government update published in the last 30 days is category-matched to one of the client's compliance types.",
     "data_sources_used": ["GovernmentUpdate", "GovernmentSource", "ComplianceProfile"],
     "confidence_basis": "Deliberately pinned to MEDIUM regardless of evidence count — this is a category-string heuristic match, not a corroborated fact. Always pins a reminder to verify direct applicability.",
     "limitations": "Only covers compliance types with a real connector category to match against: GST, Income Tax, TDS, TCS, MCA/ROC. PF, ESI, and Professional Tax clients will never see a match here because no live connector covers EPFO/ESI/state Professional Tax sources yet."},

    # --- Research Rules (app/services/intelligence/rules_research.py) ---
    {"rule_key": "RESEARCH_LOW_CONFIDENCE_ANSWER", "category": "RESEARCH", "title": "Low-confidence research answer", "status": "ACTIVE",
     "description": "A saved research query for this client scored below 75% keyword-match confidence.",
     "data_sources_used": ["ResearchQuery", "ResearchResult"], "confidence_basis": CONFIDENCE_BASIS,
     "limitations": "The Research Workspace is a deterministic keyword-scoring engine over an 8-entry seed corpus, not an LLM — 'confidence' here reflects keyword overlap strength, not legal certainty."},

    # --- Client Health Rules (app/services/intelligence/rules_client_health.py) ---
    {"rule_key": "CLIENT_HEALTH_SCORE_DIVERGENCE", "category": "COMPLIANCE", "title": "Health score divergence", "status": "ACTIVE",
     "description": "The compliance-filing health score and the document/ITR-readiness health score disagree by 2+ bands.",
     "data_sources_used": ["ComplianceHistory", "ComplianceTask", "Document", "ITRReadiness", "ClientTaxInsight"], "confidence_basis": CONFIDENCE_BASIS},
    {"rule_key": "CLIENT_HEALTH_MULTIPLE_CRITICAL", "category": "COMPLIANCE", "title": "Multiple critical findings", "status": "ACTIVE",
     "description": "Rolls up 2+ same-cycle CRITICAL suggestions from any category into a single client-level flag.",
     "data_sources_used": ["Suggestion (this engine's own output)"], "confidence_basis": CONFIDENCE_BASIS},
]


def list_rules():
    return RULE_REGISTRY
