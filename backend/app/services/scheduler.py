import threading
import time
import logging
from datetime import datetime
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from app.services.connectors.registry import ConnectorRegistry
from app.models.models import GovernmentSource
from app.core.database import SessionLocal

logger = logging.getLogger("scheduler")

class ConnectorScheduler:
    _schedules: Dict[str, Dict[str, Any]] = {}
    _running_threads: Dict[str, threading.Thread] = {}
    _stop_events: Dict[str, threading.Event] = {}

    @classmethod
    def initialize_schedules(cls, db: Session):
        """Pre-populates the schedule configs based on registered connectors"""
        connectors = ConnectorRegistry.list_all()
        for conn in connectors:
            name = conn.get_name()
            # Fetch from DB or write defaults
            source = db.query(GovernmentSource).filter(GovernmentSource.source_name == name).first()
            
            freq = source.sync_frequency if source else conn.schedule()
            status = source.connector_status if source else "RUNNING"
            
            cls._schedules[name.lower()] = {
                "connector_name": name,
                "frequency": freq,
                "status": status,
                "last_run": source.last_success if source else None,
            }

    @classmethod
    def get_schedules(cls) -> List[Dict[str, Any]]:
        return list(cls._schedules.values())

    @classmethod
    def trigger_sync(cls, connector_name: str, db: Session) -> Dict[str, Any]:
        """Triggers sync execution synchronously for a given connector"""
        conn = ConnectorRegistry.get_connector(connector_name)
        if not conn:
            return {"status": "error", "message": f"Connector '{connector_name}' not found."}

        # Run direct sync
        result = conn.sync(db)
        
        # Update cache last run
        name_lower = connector_name.lower()
        if name_lower in cls._schedules:
            cls._schedules[name_lower]["last_run"] = datetime.utcnow()

        return result

    @classmethod
    def trigger_sync_async(cls, connector_name: str):
        """Spawns a background thread to execute sync"""
        def job_wrapper():
            db = SessionLocal()
            try:
                cls.trigger_sync(connector_name, db)
            except Exception as e:
                logger.error(f"Async sync error on {connector_name}: {e}")
            finally:
                db.close()

        thread = threading.Thread(target=job_wrapper, daemon=True)
        thread.start()

    @classmethod
    def pause_schedule(cls, connector_name: str, db: Session) -> bool:
        name_lower = connector_name.lower()
        if name_lower in cls._schedules:
            cls._schedules[name_lower]["status"] = "PAUSED"
            
            # Persist to database
            source = db.query(GovernmentSource).filter(GovernmentSource.source_name == cls._schedules[name_lower]["connector_name"]).first()
            if source:
                source.connector_status = "PAUSED"
                db.commit()
            return True
        return False

    @classmethod
    def resume_schedule(cls, connector_name: str, db: Session) -> bool:
        name_lower = connector_name.lower()
        if name_lower in cls._schedules:
            cls._schedules[name_lower]["status"] = "RUNNING"
            
            # Persist to database
            source = db.query(GovernmentSource).filter(GovernmentSource.source_name == cls._schedules[name_lower]["connector_name"]).first()
            if source:
                source.connector_status = "RUNNING"
                db.commit()
            return True
        return False

    @classmethod
    def update_frequency(cls, connector_name: str, frequency: str, db: Session) -> bool:
        name_lower = connector_name.lower()
        if name_lower in cls._schedules:
            cls._schedules[name_lower]["frequency"] = frequency
            
            # Persist to database
            source = db.query(GovernmentSource).filter(GovernmentSource.source_name == cls._schedules[name_lower]["connector_name"]).first()
            if source:
                source.sync_frequency = frequency
                db.commit()
            return True
        return False
