import os
import re
import traceback
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from app.models.models import (
    RawDocument, ProcessedDocument, StructuredDocument,
    StructuredInvoiceData, StructuredNoticeData, StructuredReturnData, StructuredBankStatement,
    KnowledgeChunk, Embedding, Entity, EntityRelationship,
    Citation, DocumentVersion, ProcessingPipeline, ProcessingError,
    KnowledgeGraphNode, KnowledgeGraphEdge
)
from app.services.deduplication import DeduplicationEngine
from app.services.storage import get_storage_provider
from app.services.ocr import get_ocr_provider
from app.services.embeddings import get_embedding_provider
from app.services.parsers import ParserRegistry
from app.services.graph import GraphService
from app.services.citation import CitationEngine
from app.services.extractor import LegalReferenceExtractor


# Regex helpers for Indian regulatory identifiers
PAN_REGEX = r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b"
GSTIN_REGEX = r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b"
CIN_REGEX = r"\b[ULH][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}\b"
DIN_REGEX = r"\b[0-9]{8}\b"
TAN_REGEX = r"\b[A-Z]{4}[0-9]{5}[A-Z]{1}\b"


class DocumentPipelineOrchestrator:
    @staticmethod
    def process_document(db: Session, raw_doc_id: str) -> bool:
        """Executes the modular pipeline steps for a RawDocument. Fully retryable."""
        raw_doc = db.query(RawDocument).filter(RawDocument.id == raw_doc_id).first()
        if not raw_doc:
            return False

        # Fetch or create pipeline state
        pipeline = db.query(ProcessingPipeline).filter(
            ProcessingPipeline.raw_document_id == raw_doc_id
        ).first()

        if not pipeline:
            pipeline = ProcessingPipeline(
                organization_id=raw_doc.organization_id,
                raw_document_id=raw_doc_id,
                current_step="VALIDATE",
                status="PROCESSING"
            )
            db.add(pipeline)
            db.commit()
            db.refresh(pipeline)
        else:
            pipeline.status = "PROCESSING"
            pipeline.retries += 1
            db.commit()

        try:
            # 1. OCR text extraction
            pipeline.current_step = "OCR"
            db.commit()
            
            # Check if processed document already exists (from a previous retry or run)
            proc_doc = db.query(ProcessedDocument).filter(
                ProcessedDocument.raw_document_id == raw_doc_id
            ).first()

            if not proc_doc:
                storage = get_storage_provider()
                file_bytes = storage.read_file(raw_doc.file_path)
                
                ocr = get_ocr_provider()
                ocr_text = ocr.extract_text(file_bytes, raw_doc.name)
                
                proc_doc = ProcessedDocument(
                    organization_id=raw_doc.organization_id,
                    raw_document_id=raw_doc_id,
                    ocr_text=ocr_text,
                    normalized_text=ocr_text.strip(),
                    language="en",
                    metadata_json={"extracted_at": datetime.utcnow().isoformat()}
                )
                db.add(proc_doc)
                db.flush()
            else:
                ocr_text = proc_doc.ocr_text

            # 2. Parsing (Structured Facts)
            pipeline.current_step = "PARSE"
            db.commit()

            parser = ParserRegistry.get_parser(raw_doc.name) or ParserRegistry.get_parser(raw_doc.status) # fallback
            
            if parser and ocr_text:
                structured_facts = parser.parse(ocr_text)
                
                # Create StructuredDocument link
                struct_link = db.query(StructuredDocument).filter(
                    StructuredDocument.raw_document_id == raw_doc_id
                ).first()
                if not struct_link:
                    struct_link = StructuredDocument(
                        organization_id=raw_doc.organization_id,
                        raw_document_id=raw_doc_id,
                        parser_name=parser.get_document_type()
                    )
                    db.add(struct_link)

                # Store fact tables scoped by type
                doc_type = parser.get_document_type()
                if doc_type == "Invoice":
                    inv_data = db.query(StructuredInvoiceData).filter(
                        StructuredInvoiceData.raw_document_id == raw_doc_id
                    ).first()
                    if not inv_data:
                        inv_data = StructuredInvoiceData(
                            organization_id=raw_doc.organization_id,
                            raw_document_id=raw_doc_id,
                            **structured_facts
                        )
                        db.add(inv_data)
                elif doc_type == "Notice":
                    notice_data = db.query(StructuredNoticeData).filter(
                        StructuredNoticeData.raw_document_id == raw_doc_id
                    ).first()
                    if not notice_data:
                        notice_data = StructuredNoticeData(
                            organization_id=raw_doc.organization_id,
                            raw_document_id=raw_doc_id,
                            **structured_facts
                        )
                        db.add(notice_data)
                elif doc_type == "Balance Sheet":
                    # Store balance sheets inside processed doc tables JSON or similar structured data
                    proc_doc.cleaned_tables_json = structured_facts
                    db.add(proc_doc)

            # 3. Entity Extraction
            pipeline.current_step = "ENTITIES"
            db.commit()

            if ocr_text:
                extracted_entities = DocumentPipelineOrchestrator.extract_entities(ocr_text)
                for etype, evalue in extracted_entities:
                    # Deduplicate and resolve entity using GraphService
                    ent = GraphService.resolve_entity(db, raw_doc.organization_id, etype, evalue)

                    # Connect raw document to entity via Relationship
                    rel = db.query(EntityRelationship).filter(
                        EntityRelationship.organization_id == raw_doc.organization_id,
                        EntityRelationship.source_entity_id == ent.id,
                        EntityRelationship.target_entity_id == raw_doc_id,
                        EntityRelationship.relationship_type == "MENTIONS"
                    ).first()
                    
                    if not rel:
                        rel = EntityRelationship(
                            organization_id=raw_doc.organization_id,
                            source_entity_id=ent.id,
                            target_entity_id=raw_doc_id,
                            relationship_type="MENTIONS"
                        )
                        db.add(rel)

                    # Add Citation log
                    CitationEngine.create_citation(
                        db=db,
                        organization_id=raw_doc.organization_id,
                        source_type="CLIENT_DOCUMENT",
                        source_document_id=raw_doc_id,
                        client_id=raw_doc.client_id,
                        target_entity_id=ent.id,
                        text_reference=f"Extracted {etype} match: {evalue}",
                        quote_text=evalue,
                        confidence_score=1.0
                    )

            # 4. Embeddings Generation & Citation chunks
            pipeline.current_step = "EMBEDDINGS"
            db.commit()

            if ocr_text:
                # Text splitter (paragraphs)
                paragraphs = [p.strip() for p in ocr_text.split("\n\n") if p.strip()]
                if not paragraphs:
                    paragraphs = [ocr_text]

                embedder = get_embedding_provider()
                for idx, para in enumerate(paragraphs):
                    chunk = db.query(KnowledgeChunk).filter(
                        KnowledgeChunk.processed_document_id == proc_doc.id,
                        KnowledgeChunk.chunk_index == idx
                    ).first()

                    if not chunk:
                        chunk = KnowledgeChunk(
                            organization_id=raw_doc.organization_id,
                            processed_document_id=proc_doc.id,
                            chunk_index=idx,
                            text_content=para
                        )
                        db.add(chunk)
                        db.flush()

                        vector = embedder.get_embedding(para)
                        emb = Embedding(
                            organization_id=raw_doc.organization_id,
                            knowledge_chunk_id=chunk.id,
                            embedding_vector=vector
                        )
                        db.add(emb)

                        # Extract legal references and create citations for this chunk
                        CitationEngine.extract_and_create_citations(
                            db=db,
                            organization_id=raw_doc.organization_id,
                            text=para,
                            source_type="CLIENT_DOCUMENT",
                            source_document_id=raw_doc_id,
                            client_id=raw_doc.client_id,
                            paragraph_number=idx
                        )

            # 5. Knowledge Graph Node & Edges
            pipeline.current_step = "GRAPH"
            db.commit()

            # Build full knowledge graph connections for the document
            GraphService.build_graph_for_document(db, raw_doc.organization_id, raw_doc_id)

            # Complete Pipeline
            pipeline.current_step = "COMPLETE"
            pipeline.status = "SUCCESS"
            db.commit()

            # Sync V1 legacy document status if exists
            from app.models.models import Document
            legacy_doc = db.query(Document).filter(Document.id == raw_doc.id).first()
            if legacy_doc:
                legacy_doc.processing_status = "COMPLETED"
                legacy_doc.embedding_status = "COMPLETED"
                legacy_doc.extracted_text = ocr_text
                db.commit()
            return True

        except Exception as e:
            db.rollback()
            pipeline.status = "FAILED"
            db.commit()

            # Log detailed stack trace to processing_errors table
            error_log = ProcessingError(
                organization_id=raw_doc.organization_id,
                pipeline_id=pipeline.id,
                step_name=pipeline.current_step,
                error_message=str(e),
                stack_trace=traceback.format_exc()
            )
            db.add(error_log)
            db.commit()

            # Sync V1 legacy document status if exists
            from app.models.models import Document
            legacy_doc = db.query(Document).filter(Document.id == raw_doc.id).first()
            if legacy_doc:
                legacy_doc.processing_status = "FAILED"
                legacy_doc.embedding_status = "FAILED"
                db.commit()

            return False

    @staticmethod
    def extract_entities(text: str) -> List[tuple]:
        """Regex matches Direct/Indirect tax entity codes inside text content"""
        results = []
        
        # PAN
        for m in re.findall(PAN_REGEX, text):
            results.append(("PAN", m))
        
        # GSTIN
        for m in re.findall(GSTIN_REGEX, text):
            results.append(("GSTIN", m))
        
        # CIN
        for m in re.findall(CIN_REGEX, text):
            results.append(("CIN", m))

        # DIN
        for m in re.findall(DIN_REGEX, text):
            results.append(("DIN", m))

        # TAN
        for m in re.findall(TAN_REGEX, text):
            results.append(("TAN", m))

        return list(set(results)) # Unique tuples
