from sqlalchemy.orm import Session
from app.models.models import ResearchSource

def seed_research_sources(db: Session):
    initial_sources = [
        {
            "title": "Section 143(1) - Intimation and Summary Adjustments",
            "authority": "Income Tax Act",
            "section": "143(1)",
            "category": "Direct Tax",
            "keywords": "143(1), intimation, mismatch, summary assessment, adjustment",
            "url": "https://incometaxindia.gov.in/pages/acts/income-tax-act.aspx",
            "content": "Section 143(1) governs the processing of income tax returns. Upon filing, the Income Tax Department computes total income or loss, tax, and interest, and makes summary adjustments (arithmetical errors, incorrect claims, or mismatches between form 26AS, AIS, and ITR declarations). An intimation is issued showing details of tax payable or refund due."
        },
        {
            "title": "Section 194A - TDS on Interest other than Interest on Securities",
            "authority": "Income Tax Act",
            "section": "194A",
            "category": "Direct Tax",
            "keywords": "194a, interest mismatch, tds on interest, savings bank, fixed deposit",
            "url": "https://incometaxindia.gov.in/pages/acts/income-tax-act.aspx",
            "content": "Section 194A requires any person (other than individuals/HUFs not subject to tax audit) paying interest income (excluding interest on securities) to deduct tax at source (TDS) if the interest exceeds specified thresholds. Bank savings/fixed interest mismatches between AIS and Form 26AS are governed under this section."
        },
        {
            "title": "Section 154 - Rectification of Mistakes",
            "authority": "Income Tax Act",
            "section": "154",
            "category": "Direct Tax",
            "keywords": "154, rectification, mismatch correction, error apparent, return correction",
            "url": "https://incometaxindia.gov.in/pages/acts/income-tax-act.aspx",
            "content": "Section 154 permits the income tax authority to rectify any mistake apparent from the record in any order passed by them, including processing intimations under Section 143(1). Rectification applications are typically filed for Form 26AS/AIS credit mismatches or incorrect calculations."
        },
        {
            "title": "Section 139(1) - Due Date for Filing Income Tax Returns",
            "authority": "Income Tax Act",
            "section": "139(1)",
            "category": "Direct Tax",
            "keywords": "139(1), due date, filing deadline, tax audit, company return",
            "url": "https://incometaxindia.gov.in/pages/acts/income-tax-act.aspx",
            "content": "Section 139(1) mandates the statutory due dates for filing income tax returns. For corporate taxpayers or non-corporates subject to tax audit, the due date is October 31st. For individual taxpayers, it is July 31st."
        },
        {
            "title": "Rule 36(4) - Input Tax Credit Restrictions",
            "authority": "CGST Rules",
            "rule_number": "36(4)",
            "category": "Indirect Tax",
            "keywords": "rule 36(4), input tax credit, itc matching, gstr-2b, gstr-1",
            "url": "https://cbic-gst.gov.in/cgst-rules.html",
            "content": "Rule 36(4) restricts the input tax credit (ITC) that a taxpayer can claim. Under CGST amendments, a taxpayer can only claim ITC if the corresponding supplier invoices have been uploaded in GSTR-1 and reflect in the taxpayer's GSTR-2B statement."
        },
        {
            "title": "CBDT Circular No. 21/2024 - Handling of Mismatches between AIS and ITR declarations",
            "authority": "CBDT Circulars",
            "circular_number": "21/2024",
            "category": "Direct Tax",
            "keywords": "circular 21/2024, cbdt circular, ais mismatch, tis mismatch, ao directive",
            "url": "https://incometaxindia.gov.in/pages/communications/circulars.aspx",
            "content": "CBDT Circular 21/24 directs assessing officers and taxpayers on reconciling income mismatches flagged in the Annual Information Statement (AIS) and Taxpayer Information Summary (TIS). It explains that where the taxpayer provides clarification/feedback or proves the credit corresponds to a different PAN/Year, AO must not initiate assessment under Section 147 without verifying feedback."
        },
        {
            "title": "Section 135 - Corporate Social Responsibility (CSR)",
            "authority": "Companies Act",
            "section": "135",
            "category": "Corporate Law",
            "keywords": "section 135, companies act, csr, corporate social responsibility, net profit limit",
            "url": "https://www.mca.gov.in/content/mca/global/en/acts-rules.html",
            "content": "Section 135 mandates that every company having net worth of ₹500 crore or more, or turnover of ₹1000 crore or more, or a net profit of ₹5 crore or more during any financial year must spend at least 2% of the average net profits of the company made during the three immediately preceding financial years on Corporate Social Responsibility (CSR) activities."
        },
        {
            "title": "ICAI Guidance Note on Tax Audit under Section 44AB",
            "authority": "ICAI Guidance Notes",
            "category": "Accounting Standards",
            "keywords": "icai, tax audit, 44ab, guidance note, ca checklist",
            "url": "https://www.icai.org",
            "content": "Provides guidance on standard operating procedures for conducting tax audits under Section 44AB of the Income Tax Act. It specifies audit checklists for verifying gross turnover, deductions under Chapter VI-A, and checking tax credit matches against Form 26AS/AIS."
        }
    ]

    for src_data in initial_sources:
        existing = db.query(ResearchSource).filter(
            ResearchSource.title == src_data["title"]
        ).first()

        if not existing:
            new_source = ResearchSource(
                title=src_data["title"],
                authority=src_data["authority"],
                section=src_data.get("section"),
                rule_number=src_data.get("rule_number"),
                circular_number=src_data.get("circular_number"),
                notification_number=src_data.get("notification_number"),
                category=src_data["category"],
                keywords=src_data["keywords"],
                url=src_data["url"],
                content=src_data["content"]
            )
            db.add(new_source)
    
    db.commit()
    print("Database Seeding: Research sources seeded successfully.")
