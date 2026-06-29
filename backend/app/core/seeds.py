from sqlalchemy.orm import Session
from app.models.models import ComplianceSource

def seed_compliance_sources(db: Session):
    initial_sources = [
        {
            "source_name": "Income Tax e-Filing API",
            "category": "Income Tax",
            "official_url": "https://api.incometax.gov.in/efiling/v2",
            "access_type": "Paid API",
            "requires_auth": True,
            "update_frequency": "Real-time on request",
            "notes": "Official API specs for ERI integration, Form 26AS, AIS/TIS pulling.",
        },
        {
            "source_name": "GSTN API Platform (via GSP)",
            "category": "GST",
            "official_url": "https://api.gst.gov.in/taxpayerapi/v1.0",
            "access_type": "GSP",
            "requires_auth": True,
            "update_frequency": "Real-time on request",
            "notes": "Handles GSTR-1, GSTR-3B, GSTR-2B client data.",
        },
        {
            "source_name": "CBIC GST Circulars",
            "category": "Indirect Tax",
            "official_url": "https://www.cbic.gov.in/htdocs-cbec/gst/circulars-sec",
            "access_type": "Scraping",
            "requires_auth": False,
            "update_frequency": "Daily",
            "notes": "Circulars, notifications, and custom tariff decisions issued by CBIC.",
        },
        {
            "source_name": "GST Council Portal",
            "category": "GST",
            "official_url": "https://gstcouncil.gov.in/decisions-council",
            "access_type": "Scraping",
            "requires_auth": False,
            "update_frequency": "Weekly",
            "notes": "GST Council recommendations, press releases, and meeting highlights.",
        },
        {
            "source_name": "MCA V3 Data Services",
            "category": "MCA / ROC",
            "official_url": "https://www.mca.gov.in/content/mca/global/en/home.html",
            "access_type": "Paid API",
            "requires_auth": True,
            "update_frequency": "Daily",
            "notes": "Director listings, company information, charge records, and filings.",
        },
        {
            "source_name": "e-Gazette India",
            "category": "e-Gazette",
            "official_url": "https://egazette.gov.in",
            "access_type": "Manual Upload",
            "requires_auth": False,
            "update_frequency": "Daily",
            "notes": "Central government bills, rules, and gazetted notifications.",
        },
        {
            "source_name": "RBI Notifications",
            "category": "RBI",
            "official_url": "https://www.rbi.org.in/Scripts/NotificationUser.aspx",
            "access_type": "RSS",
            "requires_auth": False,
            "update_frequency": "Daily",
            "notes": "Banking notifications, FEMA guidelines, and external commercial borrow updates.",
        },
        {
            "source_name": "eCourts Services",
            "category": "eCourts",
            "official_url": "https://ecourts.gov.in/ecourts_home",
            "access_type": "API",
            "requires_auth": True,
            "update_frequency": "Daily",
            "notes": "Tracking ITAT and High Court litigation listings for clients.",
        },
        {
            "source_name": "data.gov.in Platform",
            "category": "data.gov.in",
            "official_url": "https://api.data.gov.in",
            "access_type": "API",
            "requires_auth": True,
            "update_frequency": "Monthly",
            "notes": "Open government database API for economic statistics and indexes.",
        }
    ]

    for src_data in initial_sources:
        existing = db.query(ComplianceSource).filter(
            ComplianceSource.source_name == src_data["source_name"]
        ).first()

        if not existing:
            new_source = ComplianceSource(
                source_name=src_data["source_name"],
                category=src_data["category"],
                official_url=src_data["official_url"],
                access_type=src_data["access_type"],
                requires_auth=src_data["requires_auth"],
                update_frequency=src_data["update_frequency"],
                status="ACTIVE",
                notes=src_data["notes"]
            )
            db.add(new_source)
    db.commit()
