import time
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.models import GovernmentSource, GovernmentUpdate, GovernmentUpdateVersion, ConnectorSyncLog, Organization
from app.services.citation import CitationEngine
from app.services.graph import GraphService


class BaseConnector(ABC):
    @abstractmethod
    def get_name(self) -> str:
        """Returns unique connector name"""
        pass

    @abstractmethod
    def get_authority(self) -> str:
        """Returns governing authority (e.g. CBDT, CBIC, RBI)"""
        pass

    @abstractmethod
    def get_category(self) -> str:
        """Returns category (e.g. Direct Tax, Indirect Tax, Banking, Corporate Law)"""
        pass

    @abstractmethod
    def discover(self, db: Session) -> List[Dict[str, Any]]:
        """Scrapes or queries target portal to discover recent updates metadata"""
        pass

    @abstractmethod
    def download(self, url: str) -> bytes:
        """Downloads document file bytes from source URL"""
        pass

    @abstractmethod
    def extract_metadata(self, content: bytes, text: str) -> Dict[str, Any]:
        """Extracts document number, title, dates, references from contents"""
        pass

    @abstractmethod
    def validate(self, content: bytes) -> bool:
        """Verifies file size and checks signature integrity"""
        pass

    @abstractmethod
    def normalize(self, text: str) -> str:
        """Converts layout raw text into standardized Markdown layout"""
        pass

    @abstractmethod
    def get_version(self, db: Session, doc_num: str) -> int:
        """Determines version index based on document number database checks"""
        pass

    @abstractmethod
    def schedule(self) -> str:
        """Returns task schedule (e.g., 'DAILY', 'HOURLY', or cron)"""
        pass

    @abstractmethod
    def health_check(self) -> str:
        """Checks if the target endpoint is reachable. Returns HEALTHY or DEGRADED"""
        pass

    @abstractmethod
    def get_rate_limits(self) -> str:
        """Returns rate limits configuration (e.g. 60/minute)"""
        pass

    @abstractmethod
    def requires_auth(self) -> bool:
        """Returns if the source requires active authentication credentials"""
        pass

    def get_official_url(self) -> str:
        """The real URL this connector fetches from. Real connectors should
        override this with their actual feed/listing URL; defaults to a
        placeholder pattern for connectors that don't (yet) have one."""
        return "https://gov.in/" + self.get_name().lower().replace(" ", "_")

    def sync(self, db: Session) -> Dict[str, Any]:
        """Runs the complete ingestion pipeline cycle for this source"""
        start_time = time.time()

        # 1. Fetch Source entry from Database (or seed it)
        source = db.query(GovernmentSource).filter(
            GovernmentSource.source_name == self.get_name()
        ).first()

        if not source:
            source = GovernmentSource(
                source_name=self.get_name(),
                category=self.get_category(),
                official_url=self.get_official_url(),
                requires_auth=self.requires_auth(),
                sync_frequency=self.schedule(),
                rate_limits=self.get_rate_limits()
            )
            db.add(source)
            db.commit()
            db.refresh(source)
        else:
            # Keep official_url/rate_limits current for pre-existing rows too -
            # otherwise a source created under a stale/mock implementation would
            # display the wrong URL forever, only ever set once at creation time.
            source.official_url = self.get_official_url()
            source.rate_limits = self.get_rate_limits()
            db.commit()

        if source.connector_status == "PAUSED":
            return {"status": "PAUSED", "documents_downloaded": 0, "message": "Connector sync is paused."}

        # 2. Check Health
        health_status = self.health_check()
        source.health = health_status
        db.commit()

        if health_status == "DOWN":
            source.last_failure = datetime.utcnow()
            source.retry_count += 1
            db.commit()
            
            # Log failure
            duration = int((time.time() - start_time) * 1000)
            log = ConnectorSyncLog(
                source_id=source.id,
                status="FAILED",
                documents_downloaded=0,
                error_message="Target government endpoint healthcheck failed (Status DOWN)",
                duration_ms=duration
            )
            db.add(log)
            db.commit()
            return {"status": "FAILED", "documents_downloaded": 0, "error": "Health check failed"}

        docs_downloaded = 0
        try:
            # 3. Discover updates
            discovered_items = self.discover(db)
            
            for item in discovered_items:
                doc_num = item.get("document_number")
                doc_url = item.get("source_url")
                doc_title = item.get("title")

                # Validate discovery metadata
                if not doc_num or not doc_url:
                    continue

                # Check if this exact update already exists (MD5 check or Doc Number + Version check)
                existing_update = db.query(GovernmentUpdate).filter(
                    GovernmentUpdate.source_id == source.id,
                    GovernmentUpdate.document_number == doc_num,
                    GovernmentUpdate.status == "ACTIVE"
                ).first()

                # 4. Download document
                content_bytes = self.download(doc_url)
                if not self.validate(content_bytes):
                    # Invalidate file size / executable check
                    continue

                checksum = hashlib.sha256(content_bytes).hexdigest()
                raw_text = content_bytes.decode("utf-8", errors="ignore")
                
                # Check version diff if update exists
                if existing_update:
                    # Compare checksums. If identical, skip to avoid redundant database writes
                    prev_version = db.query(GovernmentUpdateVersion).filter(
                        GovernmentUpdateVersion.government_update_id == existing_update.id
                    ).order_by(GovernmentUpdateVersion.version_number.desc()).first()

                    if prev_version and prev_version.checksum == checksum:
                        continue  # No modification detected

                    # Ingestion version increment path
                    next_ver = existing_update.version + 1
                    
                    # Run Change Detection Engine
                    from app.services.versioning import VersioningEngine
                    diff_data = VersioningEngine.compare_texts(prev_version.markdown_content, self.normalize(raw_text))

                    # Update main registry pointer
                    existing_update.version = next_ver
                    existing_update.title = doc_title or existing_update.title
                    db.commit()

                    # Save version revision log
                    ver_log = GovernmentUpdateVersion(
                        government_update_id=existing_update.id,
                        version_number=next_ver,
                        markdown_content=self.normalize(raw_text),
                        checksum=checksum,
                        added_paragraphs=diff_data.get("added_paragraphs"),
                        removed_paragraphs=diff_data.get("removed_paragraphs"),
                        changed_sections=diff_data.get("changed_sections"),
                        structured_differences=diff_data.get("differences")
                    )
                    db.add(ver_log)
                    db.commit()
                    
                    # Phase 4 Ingestion: Extract citations and build graph
                    orgs = db.query(Organization).filter(Organization.deleted_at.is_(None)).all()
                    for org in orgs:
                        CitationEngine.extract_and_create_citations(
                            db=db,
                            organization_id=org.id,
                            text=self.normalize(raw_text),
                            source_type="GOVERNMENT_UPDATE",
                            government_update_id=existing_update.id,
                            source_url=existing_update.source_url
                        )
                    GraphService.build_graph_for_government_update(db, existing_update.id)
                    
                    docs_downloaded += 1
                    source.version_count += 1
                else:
                    # 5. Extract metadata & Create New Document
                    meta = self.extract_metadata(content_bytes, raw_text)
                    normalized_markdown = self.normalize(raw_text)

                    new_update = GovernmentUpdate(
                        source_id=source.id,
                        title=doc_title or meta.get("title", "Untitled Government Circular"),
                        issuing_authority=self.get_authority(),
                        issue_date=meta.get("issue_date", datetime.utcnow()),
                        effective_date=meta.get("effective_date", datetime.utcnow()),
                        source_url=doc_url,
                        document_number=doc_num,
                        version=1,
                        related_acts=meta.get("related_acts", []),
                        referenced_sections=meta.get("referenced_sections", []),
                        keywords=meta.get("keywords", []),
                        summary=meta.get("summary"),
                        html_content=raw_text,
                        status="ACTIVE"
                    )
                    db.add(new_update)
                    db.commit()
                    db.refresh(new_update)

                    # Save Initial Version Log
                    ver_log = GovernmentUpdateVersion(
                        government_update_id=new_update.id,
                        version_number=1,
                        markdown_content=normalized_markdown,
                        checksum=checksum,
                        added_paragraphs=[],
                        removed_paragraphs=[],
                        changed_sections=[],
                        structured_differences={}
                    )
                    db.add(ver_log)
                    db.commit()
                    
                    # Phase 4 Ingestion: Extract citations and build graph
                    orgs = db.query(Organization).filter(Organization.deleted_at.is_(None)).all()
                    for org in orgs:
                        CitationEngine.extract_and_create_citations(
                            db=db,
                            organization_id=org.id,
                            text=normalized_markdown,
                            source_type="GOVERNMENT_UPDATE",
                            government_update_id=new_update.id,
                            source_url=new_update.source_url
                        )
                    GraphService.build_graph_for_government_update(db, new_update.id)
                    
                    docs_downloaded += 1
                    source.total_documents_count += 1

            # 6. Update Sync metrics on Success
            source.last_success = datetime.utcnow()
            source.retry_count = 0
            # Calculate dynamic dummy response latency
            source.average_response_time = (source.average_response_time * 0.8) + ((time.time() - start_time) * 1000 * 0.2)
            db.commit()

            duration = int((time.time() - start_time) * 1000)
            log = ConnectorSyncLog(
                source_id=source.id,
                status="SUCCESS",
                documents_downloaded=docs_downloaded,
                duration_ms=duration
            )
            db.add(log)
            db.commit()
            return {"status": "SUCCESS", "documents_downloaded": docs_downloaded}

        except Exception as e:
            db.rollback()
            source.last_failure = datetime.utcnow()
            source.retry_count += 1
            db.commit()

            duration = int((time.time() - start_time) * 1000)
            log = ConnectorSyncLog(
                source_id=source.id,
                status="FAILED",
                documents_downloaded=0,
                error_message=str(e),
                duration_ms=duration
            )
            db.add(log)
            db.commit()
            return {"status": "FAILED", "documents_downloaded": 0, "error": str(e)}
