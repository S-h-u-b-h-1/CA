# CA Intelligence — Project Analysis

**Author**: Principal Engineer audit (Claude Code)
**Date**: 2026-07-01
**Method**: Every backend/frontend/config/doc file read in full by dedicated audit agents (12 areas), cross-checked by importing the live FastAPI app and calling `app.openapi()`, running the real pytest suite, running a real `npm run build`, curling live production URLs, and querying the real Vercel API for project/deployment ground truth. Nothing in this document is taken from `docs/VERIFICATION_REPORT.md` or any other prior self-report without independent re-verification.

---

## 1. Executive Summary

CA Intelligence is a genuinely substantial FastAPI + Next.js codebase — 69 SQLAlchemy models, ~80 API routes, 20+ services, 17 frontend components, 41 markdown design docs, 46 commits. The CRUD/workspace plumbing layer (auth, clients, documents, notes, tasks, citations, graph nodes) is real and mostly wired correctly end-to-end.

But the product's actual differentiator — the "AI Operating System" / "Intelligence" layer that the vision document promises — **is almost entirely fabricated**. The LLM provider, the embeddings provider, the government-update connectors (all 17 of them), the AKKC practice-management sync, and the "AI-drafted" reply/citation UI are mock implementations with zero real external I/O, hardcoded to return canned data. This is disclosed honestly in exactly one doc (`AKKC_INTEGRATION_PLAN.md`, which says "Phase 1 Placeholder") and not disclosed anywhere else — the other docs and the UI present these as working integrations.

On top of that, the database schema has drifted badly (21 of 69 tables have no Alembic migration and only exist because of an unconditional `create_all()` at startup), the local pytest suite currently fails to even collect, the live "backend" Vercel deployment is serving the wrong app at its root path, and there is a real, non-feature risk: **the frontend's entire git history exists only on this machine, with no remote configured at all.**

`docs/VERIFICATION_REPORT.md`'s "10/10 Production Ready" verdict does not hold up against any of this and should be treated as void.

---

## 2. Architecture Overview

### Stack
- **Backend**: FastAPI (monolith), SQLAlchemy 2.0, Alembic, Pydantic v2, JWT auth (python-jose + bcrypt), SQLite (local) / Postgres-Neon (intended production).
- **Frontend**: Next.js 16.2.9 (Turbopack, App Router), React 19.2.4, TypeScript, Tailwind v4. Single-page app — one route (`/`), all "workspaces" are client-side tab state inside `page.tsx`.
- **Deployment**: Vercel, split across **three** separate Vercel projects for what is architecturally a two-service app (see §6).
- **Local alt path**: `docker-compose.yml` (Postgres+pgvector, backend, frontend) — present but stale, and currently broken (see §6).

### Folder structure
```
backend/app/
  api/v1/        11 routers (auth, clients, documents, compliance, search, integrations, observability, citations, graph, research)
  core/          config, database, security, seeds
  models/        models.py — 69 SQLAlchemy models, 1249 lines (single file)
  schemas/       Pydantic request/response schemas
  services/      ~20 service modules (ocr, parsers, pipeline, storage, tax_intelligence, itr_preparation,
                 compliance_service, research, llm, akkc, graph, search, citation, embeddings,
                 deduplication, verification, versioning, scheduler, connectors/)
  alembic/       6 linear migrations
  tests/         7 test files, FastAPI TestClient + in-memory SQLite
frontend/src/
  app/           layout.tsx, page.tsx (the entire app shell + global state)
  components/    16 components, each a "workspace" tab
  lib/api.ts     single ApiClient class, ~70 methods, one per backend endpoint
docs/            41 markdown design docs
```

### Data flow (as designed and as it actually runs)
Upload → `StorageProvider.save_file()` → `RawDocument` row → `DocumentPipelineOrchestrator.process_document()` → OCR → classify → parse into structured fact tables (Form26AS/AIS/TIS/GST Notice/Bank Statement/…) → `TaxIntelligenceService.recompute()` cross-references Form26AS/AIS/TIS → `ITRPreparationService.recompute()` derives a readiness score → `WorkspaceService.get_workspace_data()` aggregates everything into one "Client 360" payload the frontend renders.

This pipeline **is real** in the sense that every step calls the next and persists to real tables. Where it breaks down is *within* several of the steps (see §5) — e.g., the OCR step depends on a system `tesseract` binary that isn't installed by the Vercel Python builder, several parsers are stubs, and two real parser bugs (Form26AS TDS total, AIS `bank_interest`) mean even the "working" parsers produce wrong numbers today.

### Authentication
JWT-based, `python-jose` + `bcrypt`. Every route except `POST /auth/register` and `POST /auth/login` requires `Depends(get_current_user)` — verified by importing the live app and enumerating all ~80 routes; coverage is consistent. Role-gating for sensitive writes is done ad-hoc per-route (`if current_user.role not in [...]`) rather than via the `RoleChecker` class defined for that purpose in `deps.py`, which is dead code. Multi-tenant isolation (`organization_id` scoping) is present on almost every query and is explicitly exercised by two of the seven test files — but two new in-flight compliance endpoints are missing the standard `deleted_at.is_(None)` filter other client-scoped queries use (see bug report).

### Deployment architecture
Three Vercel projects exist in the account for this app:
- **`backend`** (`prj_nvkMwfYeAjJZ2briczkvG9iksjh9`) — domain `backend-chi-virid-16.vercel.app`. Its local `.vercel/project.json` link exists at **both** the repo root and `backend/`, proving its dashboard Root Directory is the repo root, not `backend/`. It therefore builds from the **root** `vercel.json` (which bundles both FastAPI and the entire Next.js app) instead of the clean, correct `backend/vercel.json` (API-only). Result: its own root path serves the Next.js loading screen, not the FastAPI health check, and it redundantly rebuilds the whole frontend a second time.
- **`ca-intelligence-frontend`** (`prj_c9sOZKwwx8E8qmKfs7sCtaKc8wkV`) — domain `ca-intelligence-frontend.vercel.app`. This is the correct, standalone Next.js deployment and appears to work as intended.
- **`backend-chi`** (`prj_0qo0NFTiACK961gCggo5es6ts7rL`) — domain `backend-chi-theta.vercel.app`. An orphaned duplicate, unrelated to the live `backend-chi-virid-16` domain despite the similar name.

`ca-intelligence.vercel.app`, the domain requested for production, **belongs to neither this account nor this app** — confirmed against the full Vercel project list (15 projects, none named `ca-intelligence`); the URL resolves to an unrelated static page.

`docker-compose.yml` + both `Dockerfile`s have not been touched since the first commit of the project despite 10+ feature phases since, and the backend `Dockerfile` has a fatal typo (`0.0.5.0` instead of `0.0.0.0`) confirmed to fail a socket bind — this path is currently non-functional, not merely stale.

---

## 3. Database Design

69 SQLAlchemy model classes in a single 1249-line `models.py`, UUID string PKs, consistent `organization_id` tenancy FK, `created_at`/`updated_at` conventions. Alembic is present (6 linear revisions) and `env.py` is wired correctly — but **schema management is not actually migration-driven**:

- `app/main.py`'s startup event calls `Base.metadata.create_all(bind=engine)` unconditionally, which is what actually provisions any table added after the last migration.
- **21 of 69 tables have no Alembic migration at all** (`client_tasks`, `client_tax_insights/profiles/summaries`, `client_timeline_events`, all 4 new `compliance_*` tables, `document_matches/relationships`, all 4 `itr_*` tables, all 5 `research_*` tables, `tis_entries`). `alembic upgrade head` alone does **not** produce a working schema; the migration chain is decorative for a third of the schema.
- Worse, the **`ais_entries` migration and the current `AISEntry` model define two completely different, non-overlapping column sets.** A database that only ran `alembic upgrade head` would have an `ais_entries` table with 11 columns the code never queries, and would be missing every column the code actually needs (`client_id`, `reported_value`, `derived_value`, etc.) — every AIS query would fail with "column does not exist."
- `app/models/__init__.py` only exports 28 of the 69 models; anything past "Phase 3" isn't importable via `from app.models import X` (every real call site works around this by importing from `app.models.models` directly, which is why nothing has broken yet — but it's a landmine).
- The 4 new compliance tables added this session repeat the same pattern the project's own `VERIFICATION_REPORT.md` flags as "Bug 1" (a live Postgres 500 from a missing migration) — with no regression test and no migration, only `create_all()`.

**This is the single most systemic technical-debt item in the codebase** and should be fixed before any further schema changes are layered on top.

---

## 4. Frontend Architecture

Single-page app: `page.tsx` holds all global state (user, clients, documents, compliance sources, config), gates on `api.getMe()`, then fires `Promise.all([...])` to load everything else. Child components are mostly prop-driven "dumb" components; `ClientWorkspace` and `DataPipelineDashboard` independently fetch their own data on demand. Every component talks to the backend exclusively through one `ApiClient` class in `src/lib/api.ts` (~70 methods) — cross-checked against the live FastAPI router table and **every method maps to a real, existing endpoint** with the correct path and verb. There are no dead/broken frontend→backend wires in the audited components.

What *is* broken is that several components render **fabricated UI content that never came from any API call**, sitting inside otherwise-real, wired components — see §5.2. There is also a fully-built, unreachable "Compliance Workspace" screen (uncommitted, and even if committed, never imported and missing its tab's render block) — a complete feature that a user can never open.

`npm run build` succeeds cleanly (TypeScript compiles, static export completes) — the frontend build itself is solid.

---

## 5. Strengths (verified, not assumed)

- Live-imported the FastAPI app and confirmed all ~80 routes resolve with no import errors, no unmounted routers, no missing handlers, under the current (uncommitted) code.
- Consistent JWT auth coverage across every route except the two that must be public; passwords are bcrypt-hashed correctly.
- Document upload validates extension, size, and magic-byte file signatures, and computes SHA256/MD5 hashes for dedup before persisting.
- `TaxIntelligenceService` and `ITRPreparationService` compute their outputs from real ingested `Document`/`Form26ASEntry`/`AISEntry`/`TISEntry` rows per client — not random or hardcoded per client (though several of the matching rules have logic bugs — see bug report).
- `research.py` explicitly refuses to fabricate an answer when zero sources match — a deliberate, sound anti-hallucination guard given there's no real LLM behind it.
- Entity resolution/merge in `graph.py` implements genuine 3-tier dedup (exact → alias table → normalized name) with correct FK rewiring on merge, not a stub.
- `Form26ASParser`, `AISParser`, `TISParser` do real line-based regex extraction from OCR text (not hardcoded fields) — even though two of them have concrete bugs today.
- `TesseractProvider` genuinely works for local/dev: real pypdf text extraction, page-image OCR fallback, real subprocess call to the tesseract binary.
- Test assertions (where the suite runs) are concrete — exact parsed values, exact row counts, byte-level file-signature checks — not superficial status-code-range checks.
- Frontend build is clean; TypeScript compiles with zero errors.
- Git hygiene is genuinely good in one respect: `.gitignore` correctly excludes `venv/`, `node_modules/`, `.env*`, `*.db` — confirmed via full history search that none of these were ever committed.

---

## 6. Weaknesses, Technical Debt, and What Only Appears Implemented

### 6.1 The "Intelligence" layer is mocked end-to-end
- **LLM**: `get_llm_provider()` always returns `MockLLMProvider` regardless of `LLM_PROVIDER` setting. No code path anywhere calls OpenAI/Gemini/Anthropic. `analyze_notice()` returns a hardcoded demand amount, DIN, and reply text keyed on a keyword match.
- **Embeddings**: `MockEmbeddingProvider` returns `random.uniform` vectors seeded by `hash(text)`. Nothing in the codebase ever reads these vectors back for similarity search — they're write-only.
- **Search**: "Universal search" is SQL `ILIKE '%query%'` across 9 tables. No ranking, no full-text index, no use of the embeddings computed elsewhere.
- **Government connectors (all 17, not the 18 the docs claim)**: every one subclasses a class literally named `BaseMockConnector`. Zero HTTP/network calls exist anywhere under `services/connectors/`. `download()` fabricates boilerplate text; `discover()` returns one hardcoded dict per connector; `health_check()` unconditionally returns `"HEALTHY"`.
- **AKKC practice-management integration**: `test_connection()` returns `True` for any non-empty strings. `sync_clients()` inserts 3 hardcoded fictional companies into the real `Clients` table. `sync_tasks`/`sync_bills` return literal integers with a `# Mocked count` comment, and still write a `SyncLog` row with `status="SUCCESS"` — fabricated success records live in the audit table.
- **Research "AI answer engine"**: keyword-frequency scoring over a static 8-row seed table; summary/risks/considerations are f-string templates; "confidence" is a hardcoded 90.0/75.0/0.0 constant.
- **Storage cloud providers** (S3/Azure/GCS/Supabase): all fabricate a fake URI and silently read/write local disk underneath.
- **OCR cloud providers** (Google/AWS/Azure/Gemini/OpenAI): all unconditionally raise "not configured", regardless of credentials present.

None of this is disclosed in the product docs or the UI (which markets these as live integrations), except `AKKC_INTEGRATION_PLAN.md`, which honestly labels itself "Phase 1 Placeholder."

### 6.2 Frontend fabricated content inside real components
- `DataPipelineDashboard`'s "Invoices" and "Gov Notices" tabs render entirely fabricated per-row data (fake vendor, GSTIN, amounts, DIN) for every matching document, unrelated to the document's real content.
- `DocumentIntelligence`'s "Citations" tab renders two static hardcoded citation cards for every document.
- The "AI Drafted Reply" preview is a static JSX template ending in a fixed fictitious firm name, not LLM output.
- `page.tsx` hardcodes `const akkcConnected = true` — the dashboard's AKKC status tile can never show disconnected.
- `ResearchWorkspace`'s notes feature has no backend list endpoint, so it falls back to `localStorage` and seeds a fake fixture note on first load.

### 6.3 Real bugs in parsers that are otherwise genuine
- **Form26AS parser**: `total_tds` computes to `0.0` against the documented test fixture (should be `10000.0`) — confirmed by running the actual test.
- **AIS parser**: never populates `bank_interest` (or `dividend`, `salary`, `sale_transactions`) — confirmed `KeyError` in the real test, and the AI-summary code that reads these keys will always show ₹0 regardless of document content.
- **AIS parser** assigns counterparty names (bank, employer, fund house) from a static category-keyword table, not from the document text at all.
- **GST/Income Tax notice parsers** hardcode `issue_date`/`reply_due_date`/`response_deadline` to "now" instead of extracting them — a real risk of miscalculating a statutory deadline.
- 7 of ~18 registered document parsers (GSTR-1, GSTR-2B, P&L, Trial Balance, Audit Report, Assessment Order, Appeal Order) are pure stubs returning fixed nulls/zeros/status strings regardless of input.
- Two of `tax_intelligence.py`'s discrepancy rules have matching-logic bugs that make them fire far less often (or never) than intended.
- Two independent services (`tax_intelligence.py`/`itr_preparation.py` vs. `workspace.py`) compute the financial-year label from an assessment year with two different, disagreeing formulas — one of them is simply wrong per Indian tax convention.

### 6.4 Deployment and repo integrity
- Root `vercel.json` vs. `backend/vercel.json` conflict (§2) is live and currently misrouting the "backend" project.
- `docker-compose.yml`'s backend `Dockerfile` has a fatal bind-address typo; the whole compose stack is currently non-functional as committed.
- **No `.gitmodules` file exists**, yet `frontend` is tracked as a submodule gitlink. A fresh clone cannot populate `frontend/` at all.
- **The frontend submodule's own git config has no remote at all** — 22 commits exist only on this machine. This is a data-loss risk independent of every feature bug in this report.
- No `.github` directory — zero CI, no automated test/build/lint gate on any push.
- `CORS_ORIGINS` defaults to `"*"` and is set nowhere in the repo; combined with `allow_credentials=True`, the deployed API currently accepts credentialed requests from any origin.
- `JWT_SECRET` has a hardcoded fallback value baked into source and `docker-compose.yml`; nothing validates a real secret was supplied in production.
- A Neon Postgres connection string and a JWT secret value are embedded directly in `README.md`.
- An in-flight Compliance feature (backend + frontend) is completely uncommitted, spanning both repos, and is what the audit had to evaluate "as currently sitting on disk" rather than at any commit.

### 6.5 Prior verification artifacts are unreliable
`docs/VERIFICATION_REPORT.md`'s "10/10 Production Ready" verdict and `docs/ACCEPTANCE_TEST_MATRIX.md`'s all-PASS matrix (citing test files — `test_auth.py`, `test_tenancy.py`, `test_dedup.py` — that do not exist anywhere in `backend/tests/`) do not survive independent re-verification:
- Its headline live health-check claim is reproducibly false today, and is provably unreproducible even at the time it was written, since the routing file it depends on has been unchanged since a much earlier commit.
- Its claimed "32 passed" pytest result cannot be reproduced — the suite doesn't currently collect.
- It never tested roughly a third of the current feature surface (Phase 7–10: ITR Preparation, TIS, Research Workspace, Client 360, Compliance) at all.
- Where it did test AKKC/connectors, it validated that the mock returns its hardcoded value — not that any real integration works — without disclosing the distinction.

Treat both documents as void. They should not inform any future completeness claim.

---

## 7. Code Quality, Maintainability, Scalability, Performance

- **Maintainability**: A 1249-line single `models.py` and a `parsers.py` with ~18 parser classes are workable today but will not scale gracefully; the `models/__init__.py` partial-export trap and duplicated logic (assessment-year normalization copy-pasted 7 times in `clients.py`) are the kind of debt that compounds. The `RoleChecker` dead-code/inline-role-check duplication is a smaller instance of the same pattern.
- **Scalability**: Default `DATABASE_URL` is file-based SQLite with no pool configuration and no guard against `ENV=production` falling back to it; a real multi-worker production deployment on SQLite risks "database is locked" errors and silent data loss on redeploy if the filesystem isn't persistent (which it isn't on Vercel serverless). The in-memory `ConnectorScheduler` is never invoked from any startup hook, cron, or task queue — there is no autonomous background processing anywhere in the app; everything is request-triggered.
- **Performance**: Not a primary concern yet given how much of the "intelligence" layer is inert, but the naive `ILIKE` search across 9 tables with no index will not scale past a small dataset, and the SimHash dedup logic decodes binary files (PDF/JPG/PNG/XLSX) as UTF-8 with errors ignored, which silently produces near-empty hashes for the most common CA document types.
- **Security**: See §6.4 — CORS, JWT secret fallback, secrets in README, missing `.dockerignore`. None are exploited-in-the-wild issues found, but all are real, fixable misconfigurations, not theoretical.
- **Testing**: 7 test files exist with generally well-written, concrete assertions (a genuine strength) — but the suite currently fails to collect at all, and once fixed to collect, has a real 10/34 failure rate against current code, including a systemic cross-file test-isolation bug (multiple files mutate the same global `app.dependency_overrides[get_db]` at import time).

---

## 8. Estimated Completeness

A single "% complete" number would be misleading given how unevenly complete this codebase is. Breaking it down by layer, weighted toward what a CA firm would actually notice:

| Layer | Real completeness | Basis |
|---|---|---|
| Auth, multi-tenancy, RBAC | ~85% | Fully wired, consistent, tested; role-check duplication is the only debt |
| Client management CRUD | ~80% | Fully wired; minor soft-delete filter gaps in 2 new endpoints |
| Document upload & storage (local) | ~65% | Real for local disk; cloud storage entirely fake; Vercel `/tmp` is not durable across invocations |
| OCR | ~40% | Real for local Tesseract; will very likely fail on Vercel (binary not installed); all 5 cloud OCR providers are stubs |
| Document parsers | ~45% | 8-9 of ~18 are genuinely functional (with 2 confirmed bugs); 7 are pure stubs |
| Tax Intelligence / ITR Preparation | ~55% | Real DB-driven computation; 2 confirmed matching-logic bugs and an FY-formula bug that disagrees with itself |
| Client 360 Workspace | ~60% | Aggregation is real; several sub-panels display hardcoded fields (version, confidence, processing_time) |
| Compliance Engine | ~30% | Backend logic is genuinely real, but entirely uncommitted, untested, unmigrated, and its frontend UI is unreachable |
| Research Workspace | ~25% | Real DB search over a tiny static seed set; "AI answer" is templated, not generated; notes are localStorage-only |
| Knowledge Graph / Search | ~35% | Entity resolution logic is real; search is naive ILIKE; embeddings are random noise |
| Government Updates / Connectors | ~5% | Framework/scaffolding is real engineering; every actual data source is a mock with zero network I/O |
| AKKC Integration | ~2% | UI and DB wiring real; the integration itself fabricates all data |
| Deployment / CI / repo integrity | ~30% | Frontend deploy works; backend deploy is misconfigured; no CI; submodule has no remote |

**Overall**: the plumbing/CRUD substrate is roughly two-thirds real; the "AI Operating System" differentiators that justify the product's name are, today, almost entirely simulated. This is not a product that is "mostly done with some bugs" — it is a well-structured skeleton with real workspace management, wrapped around an intelligence layer that has not actually been built yet.

## 9. What Should Be Rewritten vs. Fixed

**Fix in place** (architecture is sound, bugs are local): auth, clients, documents, parsers with real bugs (Form26AS/AIS), tax intelligence matching rules, deployment config, CORS/JWT hygiene, Alembic migration debt, test suite.

**Rewrite from scratch, don't patch**: LLM integration (needs a real provider decision + implementation, not a bigger mock), embeddings/search (needs a real strategy — Postgres full-text or a real vector store — not a bigger ILIKE), every government connector (needs real per-authority ingestion, likely one connector at a time against real RSS/APIs), AKKC integration (needs a real API contract or should be hidden from the UI until one exists).

**Remove from visible UI until real**: `DataPipelineDashboard` Invoices/Notices tabs, `DocumentIntelligence` Citations tab and "AI Drafted Reply", the AKKC status tile, `ComplianceWorkspace.tsx` (until wired in and tested), Government Knowledge Center connector health/latency metrics.

See `MASTER_BUG_REPORT.md` for the itemized, file:line-cited defect list, `REPOSITORY_CLEANUP_PLAN.md` for repo hygiene, and `IMPLEMENTATION_ROADMAP.md` for the priority-ordered execution plan.
