import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.models import ExternalSystem, IntegrationToken, SyncLog, AuditLog, Client

class AKKCConnector:
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = base_url
        self.api_key = api_key

    def test_connection(self) -> bool:
        # Simulate connecting to the deployed platform: https://akkc-eight.vercel.app/api
        if not self.base_url or not self.api_key:
            return False
        return True

    def sync_clients(self, db: Session, organization_id: str, external_system_id: str) -> int:
        # Mocked client records returned from AKKC
        mock_akkc_clients = [
            {
                "client_name": "Tata Motors Ltd",
                "client_type": "Company",
                "PAN": "TATA1234M",
                "GSTIN": "27TATA1234M1Z0",
                "CIN_LLPIN": "L34102MH1945PLC004522",
                "registered_address": "Bombay House, Homi Mody Street, Mumbai",
                "contact_person": "N. Chandrasekaran",
                "contact_email": "finance@tatamotors.com",
                "industry": "Automotive",
            },
            {
                "client_name": "Sharma & Sons HUF",
                "client_type": "HUF",
                "PAN": "SHAR7890H",
                "GSTIN": None,
                "registered_address": "Sector 15, Gurgaon, Haryana",
                "contact_person": "Ramesh Sharma",
                "contact_email": "ramesh@sharmahuf.com",
                "industry": "Real Estate",
            },
            {
                "client_name": "Venture Builders LLP",
                "client_type": "LLP",
                "PAN": "VENT4321L",
                "GSTIN": "07VENT4321L1Z9",
                "CIN_LLPIN": "AAA-9999",
                "registered_address": "Connaught Place, New Delhi",
                "contact_person": "Ankit Gupta",
                "contact_email": "finance@venturebuilders.in",
                "industry": "Construction",
            }
        ]

        synced_count = 0
        for mc in mock_akkc_clients:
            # Check if client already exists under this org by PAN or Name
            existing = db.query(Client).filter(
                Client.organization_id == organization_id,
                Client.client_name == mc["client_name"]
            ).first()

            if not existing:
                new_client = Client(
                    organization_id=organization_id,
                    client_name=mc["client_name"],
                    client_type=mc["client_type"],
                    PAN=mc["PAN"],
                    GSTIN=mc["GSTIN"],
                    CIN_LLPIN=mc.get("CIN_LLPIN"),
                    registered_address=mc["registered_address"],
                    contact_person=mc["contact_person"],
                    contact_email=mc["contact_email"],
                    industry=mc["industry"],
                    status="ACTIVE"
                )
                db.add(new_client)
                synced_count += 1
        
        db.commit()

        # Log Sync
        log = SyncLog(
            organization_id=organization_id,
            external_system_id=external_system_id,
            entity_type="CLIENTS",
            sync_status="SUCCESS",
            records_synced=synced_count
        )
        db.add(log)
        db.commit()

        return synced_count

    def sync_tasks(self, db: Session, organization_id: str, external_system_id: str) -> int:
        # Simulates syncing task entities
        synced_count = 8  # Mocked count
        
        log = SyncLog(
            organization_id=organization_id,
            external_system_id=external_system_id,
            entity_type="TASKS",
            sync_status="SUCCESS",
            records_synced=synced_count
        )
        db.add(log)
        db.commit()
        return synced_count

    def sync_bills(self, db: Session, organization_id: str, external_system_id: str) -> int:
        # Simulates syncing billing details
        synced_count = 3  # Mocked count
        
        log = SyncLog(
            organization_id=organization_id,
            external_system_id=external_system_id,
            entity_type="BILLS",
            sync_status="SUCCESS",
            records_synced=synced_count
        )
        db.add(log)
        db.commit()
        return synced_count
