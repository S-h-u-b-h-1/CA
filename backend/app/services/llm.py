from abc import ABC, abstractmethod
from app.core.config import settings

class LLMProvider(ABC):
    @abstractmethod
    def generate_summary(self, text: str) -> str:
        """Generate high-level text summary"""
        pass

    @abstractmethod
    def analyze_notice(self, notice_text: str) -> dict:
        """Analyze a tax notice and extract structured insights"""
        pass


class MockLLMProvider(LLMProvider):
    def generate_summary(self, text: str) -> str:
        if not text:
            return "No text available to summarize."
        # Generate simple summarized snippet
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        snippet = lines[0] if lines else "Document"
        return f"Summary of Document: This document appears to be related to {snippet}. It has been parsed and indexed by CA Intelligence."

    def analyze_notice(self, notice_text: str) -> dict:
        # Generate mock notice analysis
        text_lower = notice_text.lower()
        
        # Check if it looks like an income tax notice
        if "outstanding tax demand" in text_lower or "section 156" in text_lower:
            return {
                "assessment_year": "2024-25",
                "authority": "Income Tax Department of India",
                "notice_type": "Section 156 Demand Notice",
                "tax_demand_amount": "₹45,200",
                "issue_description": "Mismatch in Form 26AS TDS credits vs claimed deductions under Section 80G.",
                "response_deadline": "Within 30 days of notice date",
                "suggested_actions": [
                    "Verify Form 26AS matching with the corresponding 80G donations certificates.",
                    "Verify if the recipient institution has filed Form 10BD statement of donations.",
                    "Draft disagreement stating donation receipts are fully verified."
                ],
                "draft_reply_preview": (
                    "To,\n"
                    "The Assessing Officer,\n"
                    "Income Tax Department\n\n"
                    "Subject: Response to Demand Notice under Section 156 for AY 2024-25 (DIN: ITN/2026/29103982)\n\n"
                    "Dear Sir/Madam,\n\n"
                    "With reference to the notice of demand issued under Section 156, we would like to submit that "
                    "the taxpayer has valid receipts for all donations claimed under Section 80G. "
                    "We request a rectification under Section 154 to verify the Form 10BD filed by the donee institutions."
                )
            }
        
        # Otherwise return generic response analysis
        return {
            "assessment_year": "N/A",
            "authority": "Direct/Indirect Tax Authority",
            "notice_type": "General Inquiry/Notice",
            "tax_demand_amount": "To be determined",
            "issue_description": "General review or verification request.",
            "response_deadline": "Check document body",
            "suggested_actions": [
                "Scan the document for specific section references.",
                "Collate bank statements and corresponding invoices for the specified period."
            ],
            "draft_reply_preview": "Draft response template not available for this notice category."
        }


def get_llm_provider() -> LLMProvider:
    if settings.LLM_PROVIDER == "mock":
        return MockLLMProvider()
    else:
        # Extend here for OpenAI, Gemini, Anthropic
        return MockLLMProvider()
