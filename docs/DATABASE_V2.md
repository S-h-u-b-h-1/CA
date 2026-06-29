# Database V2 Schema Documentation

This document describes the V2 relational database schema for **CA Intelligence**, including the 21 new tables added to build the Enterprise Data Platform.

---

## Complete Table Directory

The database consists of 33 tables (12 from Phase 1, 21 added in Phase 2). All tables are fully compatible with local SQLite (`String(36)` representation for UUIDs) and production PostgreSQL instances.

### Layer 1: Ingestion
1. **`raw_documents`**: Raw document ingestion metadata.
   - `id` (PK, UUID String 36)
   - `organization_id` (FK, `organizations.id`)
   - `client_id` (FK, `clients.id`, Nullable)
   - `name` (String 255)
   - `file_path` (String 512)
   - `file_size` (Integer)
   - `mime_type` (String 100)
   - `sha256_hash` (String 64, Indexed)
   - `md5_hash` (String 32)
   - `similarity_hash` (String 64, Nullable)
   - `file_fingerprint` (String 255, Nullable)
   - `version` (Integer, default 1)
   - `status` (String 50, default ACTIVE)
   - `created_at` / `updated_at` (DateTime)
   - `deleted_at` (DateTime, Nullable)

2. **`document_versions`**: Tracking changes and replacement paths.
   - `raw_document_id` (FK, `raw_documents.id`)
   - `version_number` (Integer)
   - `file_path` (String 512)
   - `change_summary` (Text)

### Layer 2: Transcriptions
3. **`processed_documents`**: Full-text and normalized coordinates.
   - `raw_document_id` (FK, `raw_documents.id`)
   - `ocr_text` (Text)
   - `cleaned_tables_json` (JSON)
   - `normalized_text` (Text)
   - `language` (String 10)
   - `metadata_json` (JSON)

### Layer 3: Structured Facts
4. **`structured_documents`**: General indexing link.
   - `raw_document_id` (FK, `raw_documents.id`)
   - `parser_name` (String 100)
   - `extraction_date` (DateTime)

5. **`structured_invoice_data`**: Row-level invoice details.
   - `raw_document_id` (FK, `raw_documents.id`)
   - `GSTIN` (String 15, Nullable)
   - `vendor_name` (String 255, Nullable)
   - `invoice_number` (String 100, Nullable)
   - `invoice_date` (DateTime, Nullable)
   - `hsn_code` (String 20, Nullable)
   - `taxable_value` / `cgst` / `sgst` / `igst` / `cess` / `total_amount` (Float, Nullable)
   - `place_of_supply` (String 100, Nullable)
   - `payment_status` (String 50, default PENDING)

6. **`structured_notice_data`**: Row-level tax notice details.
   - `raw_document_id` (FK, `raw_documents.id`)
   - `assessment_year` (String 10, Nullable)
   - `section` (String 100, Nullable)
   - `din` (String 100, Nullable)
   - `issuing_authority` (String 255, Nullable)
   - `tax_demand_amount` (Float, Nullable)
   - `due_date` (DateTime, Nullable)
   - `issues_identified` (JSON)
   - `response_deadline` (DateTime, Nullable)
   - `reply_draft` (Text, Nullable)

7. **`structured_return_data`**: General tax filing forms (GSTR, ITR).
   - `raw_document_id` (FK, `raw_documents.id`)
   - `return_type` (String 50)
   - `filing_date` (DateTime, Nullable)
   - `tax_period` (String 20)
   - `total_tax_payable` / `total_itc_claimed` (Float, Nullable)

8. **`structured_bank_statement`**: Bank transaction logs.
   - `raw_document_id` (FK, `raw_documents.id`)
   - `bank_name` (String 255)
   - `account_number` (String 100)
   - `transaction_date` (DateTime, Nullable)
   - `particulars` (Text)
   - `transaction_type` (String 10)  # DEBIT / CREDIT
   - `amount` / `balance` (Float)

### Layer 4: Knowledge Base
9. **`knowledge_chunks`**: Semantic paragraph blocks.
   - `processed_document_id` (FK, `processed_documents.id`)
   - `chunk_index` (Integer)
   - `text_content` (Text)

10. **`embeddings`**: High-dimensional vector blocks.
    - `knowledge_chunk_id` (FK, `knowledge_chunks.id`)
    - `embedding_vector` (JSON)

11. **`entities`**: Compliance identifier cache.
    - `entity_type` (String 100) # PAN, GSTIN, CIN, DIN, TAN
    - `value` (String 512)
    - `metadata_json` (JSON)

12. **`entity_relationships`**: Semantic entity links.
    - `source_entity_id` (FK, `entities.id`)
    - `target_entity_id` (FK, `entities.id`)
    - `relationship_type` (String 100)

13. **`citations`**: Audit citation links.
    - `source_document_id` (String 36)
    - `target_entity_id` (FK, `entities.id`)
    - `text_reference` (Text)

### Layer 5: Knowledge Graph
14. **`knowledge_graph_nodes`**: Graph nodes.
    - `node_type` (String 50)
    - `label` (String 255)
    - `properties_json` (JSON)

15. **`knowledge_graph_edges`**: Relational directed graph links.
    - `source_node_id` (FK, `knowledge_graph_nodes.id`)
    - `target_node_id` (FK, `knowledge_graph_nodes.id`)
    - `relationship` (String 100)
    - `properties_json` (JSON)

### Infrastructure & Pipeline Stats
16. **`processing_pipeline`**: State tracker for active queues.
    - `raw_document_id` (FK, `raw_documents.id`)
    - `current_step` (String 50) # UPLOAD, OCR, PARSE, ENTITIES, EMBEDDINGS, GRAPH
    - `status` (String 50) # PENDING, PROCESSING, SUCCESS, FAILED
    - `retries` (Integer, default 0)

17. **`processing_errors`**: Detailed failures and traces.
    - `pipeline_id` (FK, `processing_pipeline.id`)
    - `step_name` (String 50)
    - `error_message` (Text)
    - `stack_trace` (Text, Nullable)

18. **`government_sources`**: Compliance crawlers register.
    - `source_name` (String 255)
    - `category` (String 100)
    - `official_url` (String 512)
    - `requires_auth` (Boolean)

19. **`government_updates`**: Parsed official tax circulars.
    - `source_id` (FK, `government_sources.id`)
    - `title` (String 512)
    - `issue_date` / `effective_date` (DateTime)
    - `summary` (Text)
    - `related_acts` / `referenced_sections` (JSON)

20. **`parser_registry`**: Available system parsers.
    - `parser_name` (String 100)
    - `parser_class` (String 255)
    - `supported_categories` (JSON)

21. **`ai_jobs`**: Job status for heavy operations.
    - `job_type` (String 50)
    - `status` (String 50)
    - `payload_json` / `result_json` (JSON)

---

## Constraints, Indexing, and Isolation

1. **Foreign Key Integrity**: Cascade deletion is avoided on document-related logs to preserve historic audit data.
2. **Multi-Tenant Partitioning**: Every record holds an `organization_id` column. There are no composite cross-tenant keys.
3. **Database Performance Indexing**:
   - `idx_raw_documents_sha256_hash`: Standard lookup index to enable fast duplicate checks during file upload.
   - Foreign key indexes are automatically compiled by SQLite/PostgreSQL to speed up join routes.
