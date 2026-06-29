import json
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.services.connectors.base import BaseConnector
from app.services.connectors.registry import ConnectorRegistry


class BaseMockConnector(BaseConnector):
    """Provides common mock behavior for government compliance source ingestion"""
    def download(self, url: str) -> bytes:
        # Mock pdf download by generating structured text matching the connector category
        doc_name = url.split("/")[-1].replace("_", " ").upper()
        content = (
            f"GOVERNMENT OF INDIA - OFFICIAL NOTIFICATION PORTAL\n"
            f"Source Authority: {self.get_authority()}\n"
            f"Category: {self.get_category()}\n"
            f"Ingestion URL: {url}\n\n"
            f"Subject: Official directive guidelines for compliance.\n"
            f"Pursuant to the powers conferred by Section 143 and Section 148 of the Income-tax Act, 1961, "
            f"and Rule 12 of the GST Rules, the governing body hereby clarifies the following:\n\n"
            f"1. Paragraph One: Compliance dates are extended for the respective filing assessment cycle.\n"
            f"2. Paragraph Two: All filings must include validated GSTIN and PAN identifiers.\n"
            f"3. Paragraph Three: Failure to reconcile records under Section 119 will trigger interest liabilities."
        )
        return content.encode("utf-8")

    def validate(self, content: bytes) -> bool:
        return len(content) > 0

    def normalize(self, text: str) -> str:
        # Converts layout into markdown
        lines = text.split("\n")
        markdown_lines = []
        for line in lines:
            if line.startswith("Source Authority:") or line.startswith("Category:"):
                markdown_lines.append(f"**{line}**")
            elif line.startswith("Subject:"):
                markdown_lines.append(f"## {line}")
            elif line.strip() and line[1:3] == ". ":
                markdown_lines.append(f"- {line[3:]}")
            else:
                markdown_lines.append(line)
        return "\n\n".join(markdown_lines)

    def get_version(self, db: Session, doc_num: str) -> int:
        return 1

    def health_check(self) -> str:
        return "HEALTHY"

    def get_rate_limits(self) -> str:
        return "60/minute"

    def requires_auth(self) -> bool:
        return False

    def schedule(self) -> str:
        return "DAILY"


class IncomeTaxERIConnector(BaseMockConnector):
    def get_name(self) -> str: return "Income Tax ERI"
    def get_authority(self) -> str: return "Income Tax Department (ERI)"
    def get_category(self) -> str: return "Direct Tax"
    
    def discover(self, db: Session) -> List[Dict[str, Any]]:
        return [{
            "document_number": "ERI-API-2026-04",
            "title": "ERI filing schema validations updates",
            "source_url": "https://incometax.gov.in/downloads/schemas/ERI-API-2026-04.txt"
        }]

    def extract_metadata(self, content: bytes, text: str) -> Dict[str, Any]:
        return {
            "title": "ERI filing schema validations updates",
            "issue_date": datetime.utcnow(),
            "effective_date": datetime.utcnow(),
            "related_acts": ["Income Tax Act, 1961"],
            "referenced_sections": ["Section 139"],
            "keywords": ["ERI", "Schema", "Filing", "API"],
            "summary": "Updates to electronic return filing schema interfaces."
        }


class CBDTCircularsConnector(BaseMockConnector):
    def get_name(self) -> str: return "CBDT Circulars"
    def get_authority(self) -> str: return "Central Board of Direct Taxes (CBDT)"
    def get_category(self) -> str: return "Direct Tax"

    def discover(self, db: Session) -> List[Dict[str, Any]]:
        return [{
            "document_number": "Circular No. 14/2026",
            "title": "Clarifications on TDS deductions under Section 194Q",
            "source_url": "https://cbdt.gov.in/circulars/Circular_14_2026.txt"
        }]

    def extract_metadata(self, content: bytes, text: str) -> Dict[str, Any]:
        return {
            "title": "Clarifications on TDS deductions under Section 194Q",
            "issue_date": datetime.utcnow(),
            "effective_date": datetime.utcnow(),
            "related_acts": ["Income Tax Act, 1961"],
            "referenced_sections": ["Section 194Q", "Section 206C"],
            "keywords": ["TDS", "CBDT", "Direct Tax", "Section 194Q"],
            "summary": "Clarificatory circular regarding withholding tax rules on purchase of goods."
        }


class CBICCircularsConnector(BaseMockConnector):
    def get_name(self) -> str: return "CBIC Circulars"
    def get_authority(self) -> str: return "Central Board of Indirect Taxes and Customs (CBIC)"
    def get_category(self) -> str: return "Indirect Tax"

    def discover(self, db: Session) -> List[Dict[str, Any]]:
        return [{
            "document_number": "Circular No. 204/2026-GST",
            "title": "Clarification on GST rate liability on corporate guarantees",
            "source_url": "https://cbic.gov.in/circulars/Circular_204_2026_GST.txt"
        }]

    def extract_metadata(self, content: bytes, text: str) -> Dict[str, Any]:
        return {
            "title": "Clarification on GST rate liability on corporate guarantees",
            "issue_date": datetime.utcnow(),
            "effective_date": datetime.utcnow(),
            "related_acts": ["CGST Act, 2017"],
            "referenced_sections": ["Section 15", "Rule 28"],
            "keywords": ["GST", "CBIC", "Corporate Guarantee", "Rate Change"],
            "summary": "Administrative guidelines on tax values calculation for financial guarantees."
        }


class GSTCouncilConnector(BaseMockConnector):
    def get_name(self) -> str: return "GST Council Updates"
    def get_authority(self) -> str: return "GST Council Secretariat"
    def get_category(self) -> str: return "Indirect Tax"

    def discover(self, db: Session) -> List[Dict[str, Any]]:
        return [{
            "document_number": "GSTC-53-DECISION",
            "title": "Decisions of the 53rd GST Council Meeting",
            "source_url": "https://gstcouncil.gov.in/meetings/GSTC_53_DECISION.txt"
        }]

    def extract_metadata(self, content: bytes, text: str) -> Dict[str, Any]:
        return {
            "title": "Decisions of the 53rd GST Council Meeting",
            "issue_date": datetime.utcnow(),
            "effective_date": datetime.utcnow(),
            "related_acts": ["CGST Act, 2017", "IGST Act, 2017"],
            "referenced_sections": ["Section 9", "Section 16"],
            "keywords": ["GST Council", "53rd Meeting", "Tax Decisions"],
            "summary": "Key compliance and policy decisions taken during the GST council meeting."
        }


class MCAPublicConnector(BaseMockConnector):
    def get_name(self) -> str: return "MCA Public Documents"
    def get_authority(self) -> str: return "Ministry of Corporate Affairs (MCA)"
    def get_category(self) -> str: return "Corporate Law"

    def discover(self, db: Session) -> List[Dict[str, Any]]:
        return [{
            "document_number": "MCA-DIR-REGS-2026",
            "title": "Relaxations in DIN KYC filings deadlines",
            "source_url": "https://mca.gov.in/notifications/MCA_DIR_REGS_2026.txt"
        }]

    def extract_metadata(self, content: bytes, text: str) -> Dict[str, Any]:
        return {
            "title": "Relaxations in DIN KYC filings deadlines",
            "issue_date": datetime.utcnow(),
            "effective_date": datetime.utcnow(),
            "related_acts": ["Companies Act, 2013"],
            "referenced_sections": ["Section 153", "Rule 12A"],
            "keywords": ["MCA", "DIN", "KYC", "Relaxation"],
            "summary": "Notification extending annual DIN verification timeline."
        }


class ICAIAnnouncementsConnector(BaseMockConnector):
    def get_name(self) -> str: return "ICAI Announcements"
    def get_authority(self) -> str: return "Institute of Chartered Accountants of India"
    def get_category(self) -> str: return "Professional Standards"

    def discover(self, db: Session) -> List[Dict[str, Any]]:
        return [{
            "document_number": "ICAI-BOS-2026-09",
            "title": "Revised Standards on Auditing SA 299 guidelines",
            "source_url": "https://icai.org/announcements/ICAI_BOS_2026_09.txt"
        }]

    def extract_metadata(self, content: bytes, text: str) -> Dict[str, Any]:
        return {
            "title": "Revised Standards on Auditing SA 299 guidelines",
            "issue_date": datetime.utcnow(),
            "effective_date": datetime.utcnow(),
            "related_acts": ["Chartered Accountants Act, 1949"],
            "referenced_sections": ["SA 299", "SA 600"],
            "keywords": ["ICAI", "Auditing Standard", "SA 299"],
            "summary": "Regulatory guidelines on joint auditor responsibilities."
        }


class RBINotificationsConnector(BaseMockConnector):
    def get_name(self) -> str: return "RBI Notifications"
    def get_authority(self) -> str: return "Reserve Bank of India (RBI)"
    def get_category(self) -> str: return "Banking Regulation"

    def discover(self, db: Session) -> List[Dict[str, Any]]:
        return [{
            "document_number": "RBI/2026-27/05",
            "title": "Master Direction on KYC compliance updates",
            "source_url": "https://rbi.org.in/notifications/RBI_2026_27_05.txt"
        }]

    def extract_metadata(self, content: bytes, text: str) -> Dict[str, Any]:
        return {
            "title": "Master Direction on KYC compliance updates",
            "issue_date": datetime.utcnow(),
            "effective_date": datetime.utcnow(),
            "related_acts": ["Banking Regulation Act, 1949", "PMLA, 2002"],
            "referenced_sections": ["Section 35A"],
            "keywords": ["RBI", "KYC", "Master Direction", "Banking"],
            "summary": "Mandatory periodic updates to Customer Due Diligence norms for banks."
        }


class SEBICircularsConnector(BaseMockConnector):
    def get_name(self) -> str: return "SEBI Circulars"
    def get_authority(self) -> str: return "Securities and Exchange Board of India (SEBI)"
    def get_category(self) -> str: return "Securities Law"

    def discover(self, db: Session) -> List[Dict[str, Any]]:
        return [{
            "document_number": "SEBI/HO/IMD/2026/12",
            "title": "Risk disclosures framework for portfolio managers",
            "source_url": "https://sebi.gov.in/circulars/SEBI_HO_IMD_2026_12.txt"
        }]

    def extract_metadata(self, content: bytes, text: str) -> Dict[str, Any]:
        return {
            "title": "Risk disclosures framework for portfolio managers",
            "issue_date": datetime.utcnow(),
            "effective_date": datetime.utcnow(),
            "related_acts": ["SEBI Act, 1992"],
            "referenced_sections": ["Section 11(1)"],
            "keywords": ["SEBI", "PMS", "Disclosure", "Risk Management"],
            "summary": "Mandated risk disclosure template modifications for portfolio managers."
        }


class EGazetteConnector(BaseMockConnector):
    def get_name(self) -> str: return "e-Gazette"
    def get_authority(self) -> str: return "Department of Publication, Ministry of Urban Development"
    def get_category(self) -> str: return "Federal Legislation"

    def discover(self, db: Session) -> List[Dict[str, Any]]:
        return [{
            "document_number": "Gazette No. DL-33/2026",
            "title": "Notification of the Insolvency Code Amendment Act",
            "source_url": "https://egazette.nic.in/publications/Gazette_DL_33_2026.txt"
        }]

    def extract_metadata(self, content: bytes, text: str) -> Dict[str, Any]:
        return {
            "title": "Notification of the Insolvency Code Amendment Act",
            "issue_date": datetime.utcnow(),
            "effective_date": datetime.utcnow(),
            "related_acts": ["IBC, 2016"],
            "referenced_sections": ["Section 7", "Section 9"],
            "keywords": ["Gazette", "IBC", "Amendment", "Federal"],
            "summary": "Federal gazette publication enacting insolvency threshold changes."
        }


class SupremeCourtConnector(BaseMockConnector):
    def get_name(self) -> str: return "Supreme Court Judgments"
    def get_authority(self) -> str: return "Supreme Court of India"
    def get_category(self) -> str: return "Judicial Precedents"

    def discover(self, db: Session) -> List[Dict[str, Any]]:
        return [{
            "document_number": "2026 INSC 482",
            "title": "Commissioner of Income Tax vs. M/s ABC Builders",
            "source_url": "https://supremecourtofindia.nic.in/judgments/2026_INSC_482.txt"
        }]

    def extract_metadata(self, content: bytes, text: str) -> Dict[str, Any]:
        return {
            "title": "Commissioner of Income Tax vs. M/s ABC Builders",
            "issue_date": datetime.utcnow(),
            "effective_date": datetime.utcnow(),
            "related_acts": ["Income Tax Act, 1961"],
            "referenced_sections": ["Section 80-IA"],
            "keywords": ["Supreme Court", "CIT", "Tax Exemption", "Construction"],
            "summary": "Supreme Court decision holding that construction developers are eligible for infrastructural deductions."
        }


class HighCourtConnector(BaseMockConnector):
    def get_name(self) -> str: return "High Court Judgments"
    def get_authority(self) -> str: return "State High Courts of India"
    def get_category(self) -> str: return "Judicial Precedents"

    def discover(self, db: Session) -> List[Dict[str, Any]]:
        return [{
            "document_number": "2026 BOMHC 1092",
            "title": "State of Maharashtra vs. M/s Reliance Retail",
            "source_url": "https://bombayhighcourt.nic.in/judgments/2026_BOMHC_1092.txt"
        }]

    def extract_metadata(self, content: bytes, text: str) -> Dict[str, Any]:
        return {
            "title": "State of Maharashtra vs. M/s Reliance Retail",
            "issue_date": datetime.utcnow(),
            "effective_date": datetime.utcnow(),
            "related_acts": ["MVAT Act, 2002", "CGST Act, 2017"],
            "referenced_sections": ["Section 16"],
            "keywords": ["Bombay High Court", "VAT", "Input Tax Credit"],
            "summary": "High Court ruling clarifying transition criteria for VAT inputs credits into GST systems."
        }


class CESTATConnector(BaseMockConnector):
    def get_name(self) -> str: return "CESTAT Orders"
    def get_authority(self) -> str: return "Customs, Excise and Service Tax Appellate Tribunal"
    def get_category(self) -> str: return "Tribunal Appeals"

    def discover(self, db: Session) -> List[Dict[str, Any]]:
        return [{
            "document_number": "CESTAT-GST-A-12-2026",
            "title": "M/s Taj Hotels vs. Commissioner of Central Excise",
            "source_url": "https://cestat.gov.in/orders/CESTAT_GST_A_12_2026.txt"
        }]

    def extract_metadata(self, content: bytes, text: str) -> Dict[str, Any]:
        return {
            "title": "M/s Taj Hotels vs. Commissioner of Central Excise",
            "issue_date": datetime.utcnow(),
            "effective_date": datetime.utcnow(),
            "related_acts": ["Finance Act, 1994", "CGST Act, 2017"],
            "referenced_sections": ["Section 66B"],
            "keywords": ["CESTAT", "Service Tax", "Hotel", "Luxury Tax"],
            "summary": "Tribunal order deleting double service tax demand on luxury amenities."
        }


class AdvanceRulingsConnector(BaseMockConnector):
    def get_name(self) -> str: return "Advance Rulings"
    def get_authority(self) -> str: return "Authority for Advance Rulings (AAR)"
    def get_category(self) -> str: return "Indirect Tax"

    def discover(self, db: Session) -> List[Dict[str, Any]]:
        return [{
            "document_number": "AAR-GST-03/2026",
            "title": "Ruling in application of M/s Tech Services Pvt Ltd",
            "source_url": "https://aar.gov.in/rulings/AAR_GST_03_2026.txt"
        }]

    def extract_metadata(self, content: bytes, text: str) -> Dict[str, Any]:
        return {
            "title": "Ruling in application of M/s Tech Services Pvt Ltd",
            "issue_date": datetime.utcnow(),
            "effective_date": datetime.utcnow(),
            "related_acts": ["CGST Act, 2017"],
            "referenced_sections": ["Section 97"],
            "keywords": ["AAR", "Advance Ruling", "Export", "Intermediary"],
            "summary": "Ruling classifying software consulting services as export instead of intermediary services."
        }


class FinMinPressConnector(BaseMockConnector):
    def get_name(self) -> str: return "Finance Ministry Press Releases"
    def get_authority(self) -> str: return "Ministry of Finance, Government of India"
    def get_category(self) -> str: return "Ministry Directives"

    def discover(self, db: Session) -> List[Dict[str, Any]]:
        return [{
            "document_number": "PIB-FINMIN-2026-92",
            "title": "GST revenue collections cross landmark figures",
            "source_url": "https://pib.gov.in/pressreleases/PIB_FINMIN_2026_92.txt"
        }]

    def extract_metadata(self, content: bytes, text: str) -> Dict[str, Any]:
        return {
            "title": "GST revenue collections cross landmark figures",
            "issue_date": datetime.utcnow(),
            "effective_date": datetime.utcnow(),
            "related_acts": ["CGST Act, 2017"],
            "referenced_sections": ["Section 9"],
            "keywords": ["PIB", "Finance Ministry", "Revenue", "GST Collections"],
            "summary": "Press note detailing monthly compliance metrics and collections data."
        }


class UnionBudgetConnector(BaseMockConnector):
    def get_name(self) -> str: return "Union Budget Documents"
    def get_authority(self) -> str: return "Ministry of Finance (Budget Division)"
    def get_category(self) -> str: return "Federal Budget"

    def discover(self, db: Session) -> List[Dict[str, Any]]:
        return [{
            "document_number": "BUDGET-SPEECH-2026",
            "title": "Union Budget Speech of 2026-27",
            "source_url": "https://indiabudget.gov.in/budget2026/BUDGET_SPEECH_2026.txt"
        }]

    def extract_metadata(self, content: bytes, text: str) -> Dict[str, Any]:
        return {
            "title": "Union Budget Speech of 2026-27",
            "issue_date": datetime.utcnow(),
            "effective_date": datetime.utcnow(),
            "related_acts": ["Constitution of India"],
            "referenced_sections": ["Article 112"],
            "keywords": ["Budget", "Finance Minister", "Fiscal Policy", "Annual Speech"],
            "summary": "Annual financial budget document outlining tax structures and allocations."
        }


class FinanceBillsConnector(BaseMockConnector):
    def get_name(self) -> str: return "Finance Bills"
    def get_authority(self) -> str: return "Parliament of India (Lok Sabha / Rajya Sabha)"
    def get_category(self) -> str: return "Federal Legislation"

    def discover(self, db: Session) -> List[Dict[str, Any]]:
        return [{
            "document_number": "Bill No. 12 of 2026",
            "title": "The Finance Bill of 2026",
            "source_url": "https://sansad.in/bills/Bill_12_2026.txt"
        }]

    def extract_metadata(self, content: bytes, text: str) -> Dict[str, Any]:
        return {
            "title": "The Finance Bill of 2026",
            "issue_date": datetime.utcnow(),
            "effective_date": datetime.utcnow(),
            "related_acts": ["Income Tax Act, 1961", "CGST Act, 2017"],
            "referenced_sections": ["Section 2", "Section 10"],
            "keywords": ["Finance Bill", "Parliament", "Taxation Rates", "Amendments"],
            "summary": "Legislative bill specifying direct and indirect tax rate amendments."
        }


class OfficialFAQsConnector(BaseMockConnector):
    def get_name(self) -> str: return "Official FAQs"
    def get_authority(self) -> str: return "GSTN / CBIC Helpdesk"
    def get_category(self) -> str: return "Helpdesk FAQ"

    def discover(self, db: Session) -> List[Dict[str, Any]]:
        return [{
            "document_number": "GSTN-FAQ-ITC-2026",
            "title": "FAQ on claiming input tax credits in GSTR-3B",
            "source_url": "https://tutorial.gst.gov.in/faq/GSTN_FAQ_ITC_2026.txt"
        }]

    def extract_metadata(self, content: bytes, text: str) -> Dict[str, Any]:
        return {
            "title": "FAQ on claiming input tax credits in GSTR-3B",
            "issue_date": datetime.utcnow(),
            "effective_date": datetime.utcnow(),
            "related_acts": ["CGST Act, 2017"],
            "referenced_sections": ["Section 16", "Rule 36(4)"],
            "keywords": ["FAQ", "GSTN", "GSTR-3B", "Input Tax Credit"],
            "summary": "Official questions and answers addressing GSTR-3B reconciliation."
        }


class GovPressNotesConnector(BaseMockConnector):
    def get_name(self) -> str: return "Government Press Notes"
    def get_authority(self) -> str: return "DPIIT, Ministry of Commerce & Industry"
    def get_category(self) -> str: return "FDI Regulation"

    def discover(self, db: Session) -> List[Dict[str, Any]]:
        return [{
            "document_number": "Press Note No. 1 (2026 Series)",
            "title": "Revised FDI policies in e-commerce segments",
            "source_url": "https://dpiit.gov.in/notifications/Press_Note_1_2026.txt"
        }]

    def extract_metadata(self, content: bytes, text: str) -> Dict[str, Any]:
        return {
            "title": "Revised FDI policies in e-commerce segments",
            "issue_date": datetime.utcnow(),
            "effective_date": datetime.utcnow(),
            "related_acts": ["FEMA, 1999"],
            "referenced_sections": ["Section 6"],
            "keywords": ["Press Note", "DPIIT", "FDI", "E-commerce"],
            "summary": "Policy directives laying down criteria for foreign investments in e-commerce marketplaces."
        }


# Register all 18 connectors
ConnectorRegistry.register(IncomeTaxERIConnector())
ConnectorRegistry.register(CBDTCircularsConnector())
ConnectorRegistry.register(CBICCircularsConnector())
ConnectorRegistry.register(GSTCouncilConnector())
ConnectorRegistry.register(MCAPublicConnector())
ConnectorRegistry.register(ICAIAnnouncementsConnector())
ConnectorRegistry.register(RBINotificationsConnector())
ConnectorRegistry.register(SEBICircularsConnector())
ConnectorRegistry.register(EGazetteConnector())
ConnectorRegistry.register(SupremeCourtConnector())
ConnectorRegistry.register(HighCourtConnector())
ConnectorRegistry.register(CESTATConnector())
ConnectorRegistry.register(AdvanceRulingsConnector())
ConnectorRegistry.register(FinMinPressConnector())
ConnectorRegistry.register(UnionBudgetConnector())
ConnectorRegistry.register(FinanceBillsConnector())
ConnectorRegistry.register(OfficialFAQsConnector())
ConnectorRegistry.register(GovPressNotesConnector())
