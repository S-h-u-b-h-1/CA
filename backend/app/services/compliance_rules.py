"""
Registry of the 8 compliance types this product supports, with real
statutory due-date defaults where a genuinely nationally-uniform rule
exists in Indian law, and honest "no safe default" flags where the rule
is jurisdiction/scheme/client-specific.

Every rule and caveat below was independently researched against current
Indian statutory sources (Income-tax Act 1961/2025, CGST Act/CBIC
notifications, Companies Act 2013, EPF & MP Act 1952, ESI Act 1948) as of
2026-07-02 - not invented. Where a rule genuinely varies (GST filing
scheme + state, Professional Tax being a state subject, MCA/ROC being
tied to each company's own AGM date), this registry says so explicitly
rather than presenting a guess as a default. See docs/COMPLIANCE_RULES.md
for the full research notes and sources.

This registry only supplies *defaults* for the profile-creation form; the
underlying ComplianceProfile.frequency/due_day fields remain fully
user-configurable, exactly so a CA can override them for a specific
client's actual scheme/state/AGM date.
"""
from typing import Optional, TypedDict


class ComplianceTypeRule(TypedDict):
    label: str
    is_nationally_uniform: bool
    default_frequency: Optional[str]  # MONTHLY | QUARTERLY | ANNUALLY | None
    default_due_day: Optional[int]
    summary: str
    limitations: str


COMPLIANCE_TYPE_REGISTRY: dict[str, ComplianceTypeRule] = {
    "GST": {
        "label": "GST (GSTR-3B)",
        "is_nationally_uniform": False,
        "default_frequency": "MONTHLY",
        "default_due_day": 20,
        "summary": (
            "Regular monthly filers: GSTR-3B due on the 20th of the following "
            "month (nationally uniform for this filer category)."
        ),
        "limitations": (
            "Only applies to taxpayers NOT on the QRMP scheme. QRMP filers "
            "(turnover up to Rs 5 crore who opted in) file quarterly, due on "
            "the 22nd or 24th of the month after quarter-end depending on "
            "their registered state/UT (CBIC Notification No. 84/2020-Central "
            "Tax). GSTR-1 has separate due dates (11th monthly / 13th "
            "quarterly-IFF) - track it as its own profile if needed. Confirm "
            "the client's actual scheme and state before relying on the "
            "prefilled default."
        ),
    },
    "Income Tax": {
        "label": "Income Tax (Advance Tax Installments)",
        "is_nationally_uniform": True,
        "default_frequency": "QUARTERLY",
        "default_due_day": 15,
        "summary": (
            "Advance tax installments due 15 Jun / 15 Sep / 15 Dec / 15 Mar "
            "(cumulative 15% / 45% / 75% / 100% of estimated liability) - "
            "nationally uniform under the Income-tax Act for taxpayers with "
            "net tax liability over Rs 10,000."
        ),
        "limitations": (
            "Presumptive-taxation filers under Sections 44AD/44ADA may pay "
            "100% in a single installment by 15 March instead of following "
            "the 4-installment schedule. This profile tracks advance tax, NOT "
            "the annual ITR filing deadline - the ITR due date varies by "
            "taxpayer/audit category and is extended by the government most "
            "years, so it is not safe to hardcode and is out of scope for "
            "this recurring-task rule; track it manually or as a one-off task."
        ),
    },
    "TDS": {
        "label": "TDS (Monthly Deposit)",
        "is_nationally_uniform": True,
        "default_frequency": "MONTHLY",
        "default_due_day": 7,
        "summary": (
            "TDS deposit due by the 7th of the month following deduction - "
            "nationally uniform for all non-government deductors and all "
            "TDS sections."
        ),
        "limitations": (
            "March-deducted TDS is due 30 April instead of the 7th (year-end "
            "extension) - this recurring rule does not special-case that "
            "month; adjust the March task manually. Government deductors "
            "paying via book entry must deposit the same day. Quarterly TDS "
            "return filing (Form 24Q/26Q, due ~31 Jul/Oct/Jan/May) is a "
            "separate obligation - set up a second QUARTERLY profile for it "
            "if you want it tracked distinctly from the monthly deposit."
        ),
    },
    "TCS": {
        "label": "TCS (Monthly Deposit)",
        "is_nationally_uniform": True,
        "default_frequency": "MONTHLY",
        "default_due_day": 7,
        "summary": (
            "TCS deposit due by the 7th of the month following collection - "
            "nationally uniform, no March extension (unlike TDS)."
        ),
        "limitations": (
            "Quarterly TCS return filing (Form 27EQ, being replaced by Form "
            "143 for collections from 1 April 2026 onward) is a separate "
            "obligation - set up a second QUARTERLY profile if you want it "
            "tracked distinctly from the monthly deposit."
        ),
    },
    "MCA/ROC": {
        "label": "MCA/ROC Annual Filing (AOC-4 / MGT-7)",
        "is_nationally_uniform": False,
        "default_frequency": "ANNUALLY",
        "default_due_day": None,
        "summary": (
            "No fixed national calendar date exists - due dates are computed "
            "relative to each company's own AGM date (AOC-4 due AGM+30 days, "
            "MGT-7/7A due AGM+60 days)."
        ),
        "limitations": (
            "This is a client-specific trigger, not a calendar rule. AGM must "
            "be held within 6 months of financial year-end (9 months for a "
            "company's first AGM), so due dates commonly fall around Oct/Nov "
            "for a 31 March year-end - but always confirm the client's actual "
            "AGM date and set due_day/frequency manually rather than relying "
            "on any prefilled value."
        ),
    },
    "PF": {
        "label": "PF (Provident Fund - Monthly Contribution/ECR)",
        "is_nationally_uniform": True,
        "default_frequency": "MONTHLY",
        "default_due_day": 15,
        "summary": (
            "EPF contribution deposit and ECR filing due within 15 days of "
            "month-end - nationally uniform under EPFO rules, no state "
            "variation."
        ),
        "limitations": (
            "The prior 5-day grace period was withdrawn in Jan 2016 - due "
            "date is strictly the 15th, not the 20th. If the 15th falls on a "
            "weekend/holiday, EPFO commonly shifts to the next working day; "
            "confirm for the specific month rather than assuming."
        ),
    },
    "ESI": {
        "label": "ESI (Monthly Contribution)",
        "is_nationally_uniform": True,
        "default_frequency": "MONTHLY",
        "default_due_day": 15,
        "summary": (
            "ESI contribution payment due within 15 days of month-end - "
            "nationally uniform under ESI (General) Regulations, no state "
            "variation."
        ),
        "limitations": (
            "Half-yearly ESI return (Form 5) has separate due dates (11 May "
            "and 11 November) - track it as its own profile if needed. "
            "Weekend/holiday shifts are an administrative accommodation, not "
            "a guaranteed rule - confirm for the specific month."
        ),
    },
    "Professional Tax": {
        "label": "Professional Tax",
        "is_nationally_uniform": False,
        "default_frequency": None,
        "default_due_day": None,
        "summary": "No safe national default exists - Professional Tax is a state subject.",
        "limitations": (
            "Levied and administered entirely by individual state "
            "governments under Article 276 of the Constitution. Roughly 20 "
            "states/UTs levy it, each with its own registration thresholds, "
            "slab rates, and due dates/frequency (monthly, quarterly, "
            "half-yearly, or annual); several states (Haryana, Punjab, "
            "Rajasthan, UP, Delhi, and most of the North-East) levy no PT at "
            "all. You must set frequency and due_day yourself based on the "
            "client's registered state - there is no product-wide default."
        ),
    },
}

# Accept a couple of common alternate spellings used elsewhere in the app/UI.
_ALIASES = {
    "ROC / MCA": "MCA/ROC",
    "ROC/MCA": "MCA/ROC",
    "MCA": "MCA/ROC",
    "ROC": "MCA/ROC",
}


def normalize_compliance_type(compliance_type: str) -> str:
    return _ALIASES.get(compliance_type.strip(), compliance_type.strip())


def get_compliance_type_rule(compliance_type: str) -> Optional[ComplianceTypeRule]:
    return COMPLIANCE_TYPE_REGISTRY.get(normalize_compliance_type(compliance_type))


def list_compliance_types() -> list[dict]:
    return [{"key": key, **rule} for key, rule in COMPLIANCE_TYPE_REGISTRY.items()]
