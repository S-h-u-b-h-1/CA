from abc import ABC, abstractmethod
from app.core.config import settings

class OCRProvider(ABC):
    @abstractmethod
    def extract_text(self, file_content: bytes, file_name: str) -> str:
        """Extract text from document bytes"""
        pass


class MockOCRProvider(OCRProvider):
    def extract_text(self, file_content: bytes, file_name: str) -> str:
        name_lower = file_name.lower()
        if "gstr-3b" in name_lower or "gstr3b" in name_lower:
            return (
                "GST Return - Form GSTR-3B\n"
                "GSTIN: 27AAACA1234A1Z5\n"
                "Tax Period: May 2026\n"
                "Legal Name: Apex Tax Advisory LLP\n"
                "Section 3.1: Tax on Outward Supplies: Integrated Tax: INR 2,40,000, Central Tax: INR 1,20,000, State Tax: INR 1,20,000\n"
                "Section 4: Eligible Input Tax Credit (ITC): Integrated Tax: INR 1,80,000, Central Tax: INR 90,000, State Tax: INR 90,000\n"
                "Net Tax Payable: Integrated Tax: INR 60,000, Central Tax: INR 30,000, State Tax: INR 30,000"
            )
        elif "form 16" in name_lower or "form16" in name_lower:
            return (
                "FORM NO. 16 - Certificate under section 203 of the Income-tax Act, 1961\n"
                "Assessment Year: 2025-26\n"
                "PAN of Employee: ABCDE1234F\n"
                "TAN of Employer: MNO12345P\n"
                "Employer Name: Infosys Limited\n"
                "Employee Name: Rajesh Kumar\n"
                "Gross Salary under Section 17(1): INR 12,45,000\n"
                "Total Deductions under Chapter VI-A: Section 80C: INR 1,50,000, Section 80D: INR 25,000\n"
                "Total Taxable Income: INR 10,70,000\n"
                "Total Tax Deposited: INR 1,24,000"
            )
        elif "notice" in name_lower:
            return (
                "INCOME TAX DEPARTMENT OF INDIA - NOTICE OF DEMAND UNDER SECTION 156\n"
                "DIN: ITN/2026/29103982\n"
                "Assessment Year: 2024-25\n"
                "PAN: AXCPD9081K\n"
                "Notice Date: June 15, 2026\n"
                "Subject: Notice of demand under section 156 for Outstanding Tax Liability\n"
                "Outstanding Tax Demand: INR 45,200\n"
                "Reason: Mismatch in Form 26AS TDS credits vs claimed deductions under Section 80G.\n"
                "Please submit your response within 30 days of receipt of this notice."
            )
        elif "balance sheet" in name_lower or "bs" in name_lower:
            return (
                "Balance Sheet as of March 31, 2026\n"
                "Particulars | Note No. | Figures as of 31-03-2026\n"
                "I. EQUITY AND LIABILITIES\n"
                "1. Shareholders' Funds\n"
                "   (a) Share Capital | 1 | INR 10,00,000\n"
                "   (b) Reserves & Surplus | 2 | INR 24,50,000\n"
                "2. Non-Current Liabilities | 3 | INR 12,00,000\n"
                "3. Current Liabilities | 4 | INR 6,50,000\n"
                "TOTAL EQUITY & LIABILITIES: INR 53,00,000\n"
                "II. ASSETS\n"
                "1. Non-Current Assets (Fixed Assets) | 5 | INR 35,00,000\n"
                "2. Current Assets | 6 | INR 18,00,000\n"
                "TOTAL ASSETS: INR 53,00,000"
            )
        else:
            return (
                f"Extracted content from {file_name}:\n"
                "This is a placeholder for OCR extracted text. The application has run the document through "
                "the MockOCR service. In production, this text will be extracted by Google Cloud Document AI, "
                "AWS Textract, Tesseract, or Gemini Vision API depending on the configured OCR_PROVIDER."
            )


def get_ocr_provider() -> OCRProvider:
    if settings.OCR_PROVIDER == "mock":
        return MockOCRProvider()
    else:
        # Extend here for external OCR engines
        return MockOCRProvider()
