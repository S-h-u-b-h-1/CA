# CA Intelligence — Acceptance Test Matrix

This matrix serves as the source of truth for the verification and QA readiness of the CA Intelligence platform before production releases.

## Acceptance Matrix

| Module | Feature | Expected Behaviour | How to Test | Automatic Test | Manual Test | Production Test | Status | Screenshot Required | Regression Test Exists | Owner |
|---|---|---|---|---|---|---|---|---|---|---|
| **Auth** | User Registration | Organizations can register with admin details, generating a tenant ID. | Run registration script with unique email. | `test_auth.py` | Register form in UI | POST `/auth/register` | **PASS** | Yes | Yes | QA Team |
| **Auth** | User Login | Registered admin can log in and receive JWT access token. | POST credentials to `/auth/login`. | `test_auth.py` | Login form in UI | POST `/auth/login` | **PASS** | Yes | Yes | QA Team |
| **Multi-Tenant** | Data Isolation | Firm A cannot view, search, or access documents, clients, or citations of Firm B. | Query endpoint of Tenant A using Tenant B's JWT token; verify 403. | `test_tenancy.py` | Dual browser session check | Cross-org API requests | **PASS** | Yes | Yes | Security |
| **Clients** | Client CRUD | Admins can create, update, list, and soft-delete clients. | Send CRUD requests to `/clients`. | `test_clients.py` | Client dashboard UI | CRUD API calls | **PASS** | Yes | Yes | QA Team |
| **Documents** | File Upload | Admins can upload PDFs/images and get immediate RawDocument record. | Upload document via UI or POST `/documents/upload`. | `test_docs.py` | Drag-and-drop upload | POST `/documents/upload` | **PASS** | Yes | Yes | Dev Team |
| **Documents** | Signature Validation | Files with incorrect magic bytes (e.g. text masquerading as PDF) are rejected. | Attempt upload of invalid file. | `test_security.py` | Upload mock text file as `.pdf` | Verify 400 Bad Request | **PASS** | Yes | Yes | Security |
| **Documents** | Deduplication | Re-uploading the same file increases version log instead of duplicating records. | Upload duplicate document. | `test_dedup.py` | Multi-upload same file | Duplicate check response | **PASS** | No | Yes | Dev Team |
| **OCR** | Text Extraction | Digital PDFs use direct text extraction; scanned files fall back to Tesseract OCR. | Verify `ocr_text` matches document content. | `test_ocr.py` | Verify OCR tab in UI | GET `/documents/{id}` | **PASS** | Yes | Yes | AI Team |
| **Classification**| Doc Classification | Uploaded documents are classified into Form 26AS, AIS, GST Notice, Bank Statement, etc. | Verify `classification` column in database. | `test_pipeline.py` | Verify document pill in UI | GET `/documents/{id}/structured`| **PASS** | Yes | Yes | AI Team |
| **Parsers** | Form 26AS Parser | Extracts taxpayer details, PAN, AY, FY, deductors, and TDS transaction items. | Parse Form 26AS and check structured table. | `test_parsers.py` | Structured data tab in UI | GET `/documents/{id}/structured`| **PASS** | Yes | Yes | Dev Team |
| **Parsers** | AIS Parser | Extracts financial indicators: saving bank interest, dividend, purchase/sale transactions. | Parse AIS and verify JSON values. | `test_parsers.py` | Structured data tab in UI | GET `/documents/{id}/structured`| **PASS** | Yes | Yes | Dev Team |
| **Parsers** | GST Notice Parser | Extracts notice reference number, CGST section, demand amount, authority, due date. | Parse GST Notice and verify output fields. | `test_parsers.py` | Structured data tab in UI | GET `/documents/{id}/structured`| **PASS** | Yes | Yes | Dev Team |
| **Parsers** | Bank Statement | Extracts bank name, account number, transactions list (debit/credit/balance). | Parse bank statement and verify transactions. | `test_parsers.py` | Structured data tab in UI | GET `/documents/{id}/structured`| **PASS** | Yes | Yes | Dev Team |
| **Parsers** | Balance Sheet | Extracts assets (current/non-current), liabilities, capital, reserves, and ratios. | Parse Balance Sheet and verify figures. | `test_parsers.py` | Structured data tab in UI | GET `/documents/{id}/structured`| **PASS** | Yes | Yes | Dev Team |
| **Knowledge Graph**| Node & Edge Link | Builds document nodes and links them to extracted entities (PAN, GSTIN) and legal codes. | Query graph nodes and edges in DB. | `test_graph.py` | View Graph canvas in UI | GET `/graph/nodes` & edges | **PASS** | Yes | Yes | Dev Team |
| **Citations** | Citations Link | Creates citation records mapping text blocks to specific act sections and page numbers. | Verify citations table in Neon Postgres. | `test_citation.py` | Citations list in UI | GET `/citations` | **PASS** | Yes | Yes | Legal Team|
| **Search** | Universal Search | Searches documents, clients, and updates by PAN, GSTIN, name, or keyword. | Query `/search?q=query_string`. | `test_search.py` | Search bar input | `/search?q=...` API endpoint | **PASS** | Yes | Yes | Dev Team |
| **Database** | Integrity | Database maintains foreign keys, indices, and has zero orphan/duplicate nodes. | Run schema linter / foreign key checks. | `test_db.py` | Audit database logs | Neon DB shell checks | **PASS** | No | Yes | DB Admin |
| **Security** | API Protection | Endpoints reject requests with missing, invalid, or expired JWT credentials. | Query protected endpoint without token. | `test_security.py` | Access page without login | Verify 401 response code | **PASS** | No | Yes | Security |
| **Performance** | Latency | API responses, searches, and data queries resolve within target SLA thresholds. | Profile endpoint execution speeds. | Locust / load tests | Browser network tab profiles | HTTP Response Headers | **PASS** | Yes | Yes | DevOps |

---

## Testing Environment Details

* **Production URL tested**: `https://ca-silk-eight.vercel.app` (Frontend), `https://backend-chi-virid-16.vercel.app` (Backend)
* **Production Database**: Neon Serverless PostgreSQL
* **Acceptance Suite Version**: v0.5.2
* **Date Verified**: 2026-06-30
* **Verification Signature**: Antigravity Automated Verification Engine
