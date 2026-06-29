import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Type, List
from datetime import datetime

class BaseParser(ABC):
    @abstractmethod
    def parse(self, text: str) -> Dict[str, Any]:
        """Parses extracted document text and returns structured facts"""
        pass

    @abstractmethod
    def get_document_type(self) -> str:
        """Returns the supported category name"""
        pass


class InvoiceParser(BaseParser):
    def get_document_type(self) -> str:
        return "Invoice"

    def parse(self, text: str) -> Dict[str, Any]:
        facts = {
            "GSTIN": None,
            "vendor_name": None,
            "invoice_number": None,
            "invoice_date": None,
            "hsn_code": None,
            "taxable_value": 0.0,
            "cgst": 0.0,
            "sgst": 0.0,
            "igst": 0.0,
            "cess": 0.0,
            "total_amount": 0.0,
            "currency": "INR",
            "place_of_supply": None,
            "payment_status": "PENDING"
        }

        # 1. Regex GSTIN extraction
        gstin_match = re.search(r"GSTIN:\s*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})", text, re.IGNORECASE)
        if gstin_match:
            facts["GSTIN"] = gstin_match.group(1)

        # 2. Invoice number
        inv_match = re.search(r"(?:Invoice\s*(?:No|Number|#)?|Inv)\s*[:\-]?\s*([A-Za-z0-9/\-]+)", text, re.IGNORECASE)
        if inv_match:
            facts["invoice_number"] = inv_match.group(1).strip()

        # 3. Vendor extraction
        vendor_match = re.search(r"Legal Name:\s*([^\n]+)", text, re.IGNORECASE)
        if vendor_match:
            facts["vendor_name"] = vendor_match.group(1).strip()
        else:
            # Fallback check first lines
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if lines:
                facts["vendor_name"] = lines[0]

        # 4. Tax values
        taxable_match = re.search(r"Taxable Value:\s*(?:INR|Rs\.?|₹)?\s*([0-9,]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
        if taxable_match:
            facts["taxable_value"] = float(taxable_match.group(1).replace(",", ""))

        igst_match = re.search(r"Integrated Tax:\s*(?:INR|Rs\.?|₹)?\s*([0-9,]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
        if igst_match:
            facts["igst"] = float(igst_match.group(1).replace(",", ""))

        cgst_match = re.search(r"Central Tax:\s*(?:INR|Rs\.?|₹)?\s*([0-9,]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
        if cgst_match:
            facts["cgst"] = float(cgst_match.group(1).replace(",", ""))

        sgst_match = re.search(r"State Tax:\s*(?:INR|Rs\.?|₹)?\s*([0-9,]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
        if sgst_match:
            facts["sgst"] = float(sgst_match.group(1).replace(",", ""))

        # Calculate Total if missing
        total_match = re.search(r"Total Amount:\s*(?:INR|Rs\.?|₹)?\s*([0-9,]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
        if total_match:
            facts["total_amount"] = float(total_match.group(1).replace(",", ""))
        else:
            facts["total_amount"] = facts["taxable_value"] + facts["igst"] + facts["cgst"] + facts["sgst"]

        facts["invoice_date"] = datetime.utcnow()
        return facts


class NoticeParser(BaseParser):
    def get_document_type(self) -> str:
        return "Notice"

    def parse(self, text: str) -> Dict[str, Any]:
        facts = {
            "assessment_year": None,
            "section": None,
            "din": None,
            "issuing_authority": "Income Tax Department of India",
            "tax_demand_amount": 0.0,
            "due_date": None,
            "issues_identified": [],
            "response_deadline": None,
            "reply_draft": None
        }

        # AY
        ay_match = re.search(r"Assessment Year:\s*([0-9]{4}-[0-9]{2,4})", text, re.IGNORECASE)
        if ay_match:
            facts["assessment_year"] = ay_match.group(1)

        # Section
        sec_match = re.search(r"section\s+([0-9A-Z\(\)]+)", text, re.IGNORECASE)
        if sec_match:
            facts["section"] = f"Section {sec_match.group(1)}"

        # DIN
        din_match = re.search(r"DIN:\s*([A-Za-z0-9/]+)", text, re.IGNORECASE)
        if din_match:
            facts["din"] = din_match.group(1).strip()

        # Demand Amount
        demand_match = re.search(r"(?:Outstanding Tax Demand|Demand Amount|Demand):\s*(?:INR|Rs\.?|₹)?\s*([0-9,]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
        if demand_match:
            facts["tax_demand_amount"] = float(demand_match.group(1).replace(",", ""))

        # Deadlines
        facts["due_date"] = datetime.utcnow()
        facts["response_deadline"] = datetime.utcnow()
        
        # Mocks
        facts["issues_identified"] = ["Mismatch in Form 26AS TDS credits vs claimed deductions."]
        facts["reply_draft"] = "Rectification submission under Section 154 drafted."
        
        return facts


class BalanceSheetParser(BaseParser):
    def get_document_type(self) -> str:
        return "Balance Sheet"

    def parse(self, text: str) -> Dict[str, Any]:
        facts = {
            "financial_year": "2025-26",
            "equity_share_capital": 0.0,
            "reserves_and_surplus": 0.0,
            "non_current_liabilities": 0.0,
            "current_liabilities": 0.0,
            "total_liabilities": 0.0,
            "fixed_assets": 0.0,
            "current_assets": 0.0,
            "total_assets": 0.0,
            "auditor_name": None
        }

        # Capital
        capital_match = re.search(r"Share Capital\s*(?:\| \d+ \|)?\s*(?:INR|Rs\.?|₹)?\s*([0-9,]+)", text, re.IGNORECASE)
        if capital_match:
            facts["equity_share_capital"] = float(capital_match.group(1).replace(",", ""))

        # Reserves
        res_match = re.search(r"Reserves\s*&\s*Surplus\s*(?:\| \d+ \|)?\s*(?:INR|Rs\.?|₹)?\s*([0-9,]+)", text, re.IGNORECASE)
        if res_match:
            facts["reserves_and_surplus"] = float(res_match.group(1).replace(",", ""))

        # Liabilities
        ncl_match = re.search(r"Non-Current Liabilities\s*(?:\| \d+ \|)?\s*(?:INR|Rs\.?|₹)?\s*([0-9,]+)", text, re.IGNORECASE)
        if ncl_match:
            facts["non_current_liabilities"] = float(ncl_match.group(1).replace(",", ""))

        cl_match = re.search(r"Current Liabilities\s*(?:\| \d+ \|)?\s*(?:INR|Rs\.?|₹)?\s*([0-9,]+)", text, re.IGNORECASE)
        if cl_match:
            facts["current_liabilities"] = float(cl_match.group(1).replace(",", ""))

        # Assets
        fa_match = re.search(r"(?:Fixed Assets|Non-Current Assets)\s*(?:\| \d+ \|)?\s*(?:INR|Rs\.?|₹)?\s*([0-9,]+)", text, re.IGNORECASE)
        if fa_match:
            facts["fixed_assets"] = float(fa_match.group(1).replace(",", ""))

        ca_match = re.search(r"Current Assets\s*(?:\| \d+ \|)?\s*(?:INR|Rs\.?|₹)?\s*([0-9,]+)", text, re.IGNORECASE)
        if ca_match:
            facts["current_assets"] = float(ca_match.group(1).replace(",", ""))

        facts["total_assets"] = facts["fixed_assets"] + facts["current_assets"]
        facts["total_liabilities"] = facts["equity_share_capital"] + facts["reserves_and_surplus"] + facts["non_current_liabilities"] + facts["current_liabilities"]

        return facts


class ParserRegistry:
    _parsers: Dict[str, Type[BaseParser]] = {}

    @classmethod
    def register(cls, category: str, parser_cls: Type[BaseParser]):
        cls._parsers[category.lower()] = parser_cls

    @classmethod
    def get_parser(cls, category: str) -> BaseParser | None:
        parser_cls = cls._parsers.get(category.lower())
        if parser_cls:
            return parser_cls()
        
        # Soft match
        for key, p_cls in cls._parsers.items():
            if key in category.lower() or category.lower() in key:
                return p_cls()
        return None

    @classmethod
    def list_registered(cls) -> List[Dict[str, Any]]:
        return [
            {
                "parser_name": f"{parser_cls.__name__}",
                "category": category,
                "status": "ACTIVE"
            }
            for category, parser_cls in cls._parsers.items()
        ]


# Register standard parsers
ParserRegistry.register("Invoice", InvoiceParser)
ParserRegistry.register("Notice", NoticeParser)
ParserRegistry.register("Balance Sheet", BalanceSheetParser)
