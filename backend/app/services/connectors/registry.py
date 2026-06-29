from typing import Dict, List, Type
from app.services.connectors.base import BaseConnector

class ConnectorRegistry:
    _connectors: Dict[str, BaseConnector] = {}
    _loaded = False

    @classmethod
    def _load_connectors(cls):
        if not cls._loaded:
            try:
                import app.services.connectors.sources.compliance_sources
            except ImportError:
                pass
            cls._loaded = True

    @classmethod
    def register(cls, connector: BaseConnector):
        cls._connectors[connector.get_name().lower()] = connector

    @classmethod
    def get_connector(cls, name: str) -> BaseConnector | None:
        cls._load_connectors()
        return cls._connectors.get(name.lower())

    @classmethod
    def list_all(cls) -> List[BaseConnector]:
        cls._load_connectors()
        return list(cls._connectors.values())
