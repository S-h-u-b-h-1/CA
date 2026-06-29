import re
from typing import List, Dict, Any

# Compile regular expressions for performance
PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b")
GSTIN_PATTERN = re.compile(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b")
CIN_PATTERN = re.compile(r"\b[ULH][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}\b")
DIN_PATTERN = re.compile(r"\b[0-9]{8}\b")
TAN_PATTERN = re.compile(r"\b[A-Z]{4}[0-9]{5}[A-Z]{1}\b")

SECTION_PATTERN = re.compile(r"\bSection\s+(\d+[A-Z]*(?:\(\d+\)[a-z]*)?(?:\([a-zA-Z0-9]+\))*)", re.IGNORECASE)
RULE_PATTERN = re.compile(r"\bRule\s+(\d+[A-Z]*(?:\(\d+\)[a-z]*)?(?:\([a-zA-Z0-9]+\))*)", re.IGNORECASE)
NOTIFICATION_PATTERN = re.compile(r"\bNotification\s+No\.\s*(\d+/\d+(?:-[A-Za-z0-9]+)?)", re.IGNORECASE)
CIRCULAR_PATTERN = re.compile(r"\bCircular\s+No\.\s*(\d+/\d+(?:-[A-Za-z0-9]+)?)", re.IGNORECASE)

AY_PATTERN = re.compile(r"\b(?:Assessment\s+Year|AY)\s*(\d{4}-\d{2,4})", re.IGNORECASE)
FY_PATTERN = re.compile(r"\b(?:Financial\s+Year|FY)\s*(\d{4}-\d{2,4})", re.IGNORECASE)

FORMS = ["GSTR-1", "GSTR-3B", "GSTR-2B", "Form 16", "Form 26AS", "AIS", "TIS"]

class LegalReferenceExtractor:
    @staticmethod
    def extract_all(text: str) -> Dict[str, List[str]]:
        """
        Extracts all identifiers, statutory references, and tax parameters from a given text.
        Returns a dictionary grouped by type.
        """
        if not text:
            return {}

        results = {
            "PAN": [],
            "GSTIN": [],
            "CIN": [],
            "DIN": [],
            "TAN": [],
            "SECTION": [],
            "RULE": [],
            "NOTIFICATION": [],
            "CIRCULAR": [],
            "ASSESSMENT_YEAR": [],
            "FINANCIAL_YEAR": [],
            "FORM": []
        }

        # Regex extractions
        results["PAN"] = sorted(list(set(PAN_PATTERN.findall(text))))
        results["GSTIN"] = sorted(list(set(GSTIN_PATTERN.findall(text))))
        results["CIN"] = sorted(list(set(CIN_PATTERN.findall(text))))
        
        # Guard DIN to prevent matching normal 8-digit numbers unless near DIN indicator keywords
        raw_dins = DIN_PATTERN.findall(text)
        dins = []
        for din in raw_dins:
            # Check context: search a window of 25 characters around the matched DIN
            idx = text.find(din)
            window = text[max(0, idx-30):min(len(text), idx+38)].lower()
            if "din" in window or "director" in window or "identification" in window:
                dins.append(din)
        results["DIN"] = sorted(list(set(dins)))

        results["TAN"] = sorted(list(set(TAN_PATTERN.findall(text))))
        results["SECTION"] = sorted(list(set([m.strip() for m in SECTION_PATTERN.findall(text)])))
        results["RULE"] = sorted(list(set([m.strip() for m in RULE_PATTERN.findall(text)])))
        results["NOTIFICATION"] = sorted(list(set([m.strip() for m in NOTIFICATION_PATTERN.findall(text)])))
        results["CIRCULAR"] = sorted(list(set([m.strip() for m in CIRCULAR_PATTERN.findall(text)])))
        results["ASSESSMENT_YEAR"] = sorted(list(set(AY_PATTERN.findall(text))))
        results["FINANCIAL_YEAR"] = sorted(list(set(FY_PATTERN.findall(text))))

        # Form check (case-insensitive check but return clean form name)
        found_forms = []
        for form in FORMS:
            if re.search(r"\b" + re.escape(form) + r"\b", text, re.IGNORECASE):
                found_forms.append(form)
        results["FORM"] = found_forms

        return {k: v for k, v in results.items() if v}
