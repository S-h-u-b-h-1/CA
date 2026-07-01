# CA Intelligence — Implementation Roadmap

**Date**: 2026-07-01
**Principle**: Never build a higher layer before the layer below it is verified working. Every phase below ends with a concrete, reproducible proof requirement — a fresh test run, a real curl, a screenshot — not a claim. A phase isn't "done" until that proof exists.

This roadmap assumes `PROJECT_ANALYSIS.md`, `MASTER_BUG_REPORT.md`, and `REPOSITORY_CLEANUP_PLAN.md` are read first; bug numbers below reference the bug report.

---

## Open decisions that need your input before certain phases can proceed

These aren't things I can responsibly decide unilaterally — flagging them now so they don't block later:

1. **Frontend submodule**: de-submodule into a normal directory, or properly re-wire as a real submodule with its own pushed remote? (See `REPOSITORY_CLEANUP_PLAN.md` §0.) I'll ask before touching it.
2. **`ca-intelligence.vercel.app`**: not available to this account. Do you want me to attempt claiming a different close name, add a custom domain you own, or keep `ca-intelligence-frontend.vercel.app` as the documented production URL?
3. **Real LLM provider**: the entire LLM layer is currently dead code. Making "Tax Intelligence" or "AI Drafted Reply" genuinely AI-backed requires picking a real provider and you supplying an API key (Anthropic/OpenAI/Gemini). Until that decision is made, the honest move per your own Step instructions is to **hide** any UI that claims to be AI-generated, not fake it further.
4. **Real government connectors**: implementing even one real connector (e.g. an actual CBDT RSS feed or e-Gazette listing) is real per-source research and engineering, not a config flag — scope and priority order for which authorities matter most to your firm needs your input.
5. **AKKC integration**: is this an active partnership with a real API contract, or should it be hidden from the UI until one exists? Right now it fabricates data into your database, which is worse than not having the feature at all.
6. **Docker path**: keep and fix, or drop entirely? (See cleanup plan §4.)

---

## Phase 0 — Repository & Deployment Fixes ("Step 2")

*Everything in `REPOSITORY_CLEANUP_PLAN.md`.* Nothing above this layer is trustworthy until it's done. Concrete exit criteria:
- [ ] Fresh `git clone` into a scratch directory populates `frontend/` correctly and both `pip install -r requirements.txt` + `npm install` succeed from that clone.
- [ ] `pytest` collects and runs (0 collection errors) with a real, reproducible pass count.
- [ ] `curl https://<backend-domain>/` returns the FastAPI health JSON, not frontend HTML.
- [ ] `CORS_ORIGINS` is a real, non-wildcard value in the deployed environment; a curl from an arbitrary origin is rejected.
- [ ] No hardcoded secret fallback is reachable when `ENV=production`.
- [ ] `docker compose up` either works end-to-end or the path is explicitly removed.
- [ ] GitHub Actions runs pytest + frontend build on every push.

## Phase 1 — Authentication (foundation for everything else)

Current state: real and mostly solid (see analysis §5) — JWT issuance/validation, bcrypt, consistent route coverage, multi-tenant scoping. Work here is narrow:
- Fix the 2 missing `deleted_at` filters in the new compliance endpoints (Bug #50 and its `create_` sibling).
- Decide: adopt `RoleChecker` and delete inline duplication, or delete `RoleChecker` — not both (Bug #77).
- Add a `conftest.py`-based test fixture so auth tests exercise the real `/login` endpoint rather than minting JWTs directly (Bug #85), and cover the missing-`deleted_at` fix with a regression test.

**Proof required**: register → login → logout → `/me` → protected-route-401-without-token, all exercised against a **running local server** with real curl output pasted into the PR/commit description, plus the fixed test passing.

## Phase 2 — Client Management

Real and working today. Only fix: the 2 soft-delete filter gaps above (shared with Phase 1's fix). No structural work needed — this is a "verify and move on" phase, not a rebuild.

**Proof required**: create/edit/view/archive a client via curl against a running server; confirm an archived client is excluded from list and from the new compliance endpoints.

## Phase 3 — Document Upload & Storage

- Decide the real production storage story. Given cloud providers are entirely fake (Bug #15) and Vercel's local `/tmp` is not durable across invocations, the honest options are: (a) implement one real cloud provider for real (e.g. actual S3 or Supabase Storage via their real SDK), or (b) clearly document that document storage is local-dev-only until a real provider is implemented, and make sure the retry/reprocessing flow degrades honestly (a clear "unavailable, please re-upload" error) rather than a silent `FileNotFoundError`.
- Remove the 4 fake cloud storage provider classes or clearly gate them so `STORAGE_PROVIDER` can't silently be set to something non-functional in production (fail startup validation instead).

**Proof required**: upload a real PDF against a running server pointed at whatever storage backend is chosen, confirm retrieval works from a **second, independent process invocation** (not just the same request), not just the initial upload response.

## Phase 4 — OCR

- Confirm whether Tesseract is actually viable on the target production platform; if Vercel's Python builder can't install it, either switch the production OCR default to something that works out of the box, or add the necessary build step, and validate on an actual deployed instance, not just locally (Bug #26).
- Remove or clearly gate the 5 "cloud OCR" stubs that unconditionally raise (Bug #27) — same principle as storage: don't let a config value silently select a non-functional path.

**Proof required**: upload a real scanned (non-digital-text) PDF or image to the **actual deployed** backend and confirm real extracted text comes back, not a canned string.

## Phase 5 — Classification & Parsers

- Fix the 2 confirmed parser bugs: Form26AS `total_tds` (Bug #16), AIS `bank_interest`/`dividend`/`salary`/etc. (Bug #17) — these already have failing tests; make them pass.
- Fix AIS counterparty-name fabrication (Bug #24) — extract from document text or clearly mark the field as unavailable when it can't be extracted, never substitute a fixed fake name.
- Fix GST/IT notice date hardcoding (Bug #25) — extract from text; if extraction fails, leave null and flag it rather than silently defaulting to "now."
- For the 7 stub parsers (Bug #28): either implement real extraction, or make them return an explicit `not_yet_supported` status the UI can honestly render as "Coming Soon" rather than fabricated zeros/nulls.

**Proof required**: `pytest tests/test_document_intelligence.py` passing with the real fixture values, plus one real (not test-fixture) sample document per document type run through the actual pipeline with output manually inspected.

## Phase 6 — Database

- Close all 21 missing-migration gaps (Bug #7) with real Alembic revisions — including the 4 new compliance tables — and stop relying on `create_all()` for anything beyond initial bootstrap of a brand-new dev DB.
- Fix the `ais_entries` model/migration mismatch (Bug #8) with a corrective migration.
- Add the missing `ForeignKey()` constraints (Bug #52).
- Fix or delete `models/__init__.py`'s partial export list (Bug #53).

**Proof required**: `alembic downgrade base && alembic upgrade head` against a fresh Postgres instance produces a schema that the app can run against with zero `create_all()` fallback — verify by temporarily disabling `create_all()` and confirming nothing breaks.

## Phase 7 — Frontend

- Remove or clearly label the fabricated UI sections as "Coming Soon" until backed by real data (Bugs #33, #34, #35, #64, #68 — Invoices tab, Gov Notices tab, Citations tab, AKKC status tile, "AI Drafted Reply").
- Wire in `ComplianceWorkspace.tsx` properly (import it, add the missing render block) once the backend compliance feature is committed and tested — or delete it if the compliance UI is being redesigned as part of Phase 12/Step 5 anyway.
- Add user-facing error banners for the currently console-only-logged fetch failures (Bug #65).
- Fix the dead `assignedManager`/`assignedPartner` form fields (Bug #86) and the scaffold metadata (Bug #87).

**Proof required**: for each fixed/hidden component, a before/after screenshot and a note of which real API call now backs it (or confirmation it's hidden, with the reason documented).

## Phase 8 — Search

Current state is a naive `ILIKE` filter presented as "universal search" (Bug #31), with random-vector embeddings that are never read (Bug #11). Decide: implement real Postgres full-text search (`tsvector`/`tsquery`, a real and proportionate upgrade) now, or explicitly relabel the feature as basic keyword search in the UI until a real search strategy is built. Building a full vector-search stack is a bigger, separate decision (ties into the LLM provider decision above) — don't silently promise "semantic search" without one.

**Proof required**: a search query against real ingested data returns ranked, relevant results demonstrably better than plain substring match — or the UI honestly says "keyword search."

## Phase 9 — Tax Intelligence

- Fix the FY-formula disagreement between `tax_intelligence.py`/`itr_preparation.py` and `workspace.py` (Bug #43) — pick the correct formula, apply it everywhere, add a regression test asserting AY→FY mapping for several real assessment years.
- Fix Rules 3 and 4's matching-logic bugs (Bug #44) so discrepancy detection actually correlates the right AIS entry to the right Form26AS entry rather than matching on "any entry exists."

**Proof required**: a test client with deliberately mismatched Form26AS/AIS data produces the *correct*, specific discrepancy warnings — not just "some warning fired."

## Phase 10 — ITR Preparation

Mostly real; depends on Phase 9's fixes for correct upstream data. Fix the hardcoded "4 total" required-documents count (Bug #89) to derive from the real document requirements list.

**Proof required**: readiness score and action items visibly change when a required document is added/removed for a real test client.

## Phase 11 — Research Workspace

- Either relabel this honestly as keyword-based reference lookup (matching what `research.py` actually does), or scope real LLM-backed synthesis as its own project once the LLM provider decision is made. Don't ship a "Confidence: X%" badge backed by a hardcoded constant (Bug #42).
- Give notes a real backend list endpoint and remove the `localStorage` fixture-note fallback (Bugs #69, #70) — this is a straightforward, real fix regardless of the LLM decision.

**Proof required**: notes persist server-side per-organization (verified by logging in as a second user in the same org and seeing the same notes), and the confidence/summary language in the UI matches what the backend actually computes.

## Phase 12 — Compliance (your Step 4, Compliance Engine half)

- Commit the in-flight backend compliance feature after fixing its soft-delete gaps and adding its missing Alembic migration (Phase 6 dependency) and test coverage (it currently has none).
- Wire the frontend `ComplianceWorkspace.tsx` in properly (Phase 7 dependency) or redesign it as part of Step 5.
- Build out the remaining compliance types your Step 4 lists (PF, ESI, Professional Tax) if not already covered by the current `compliance_type` field's scope — verify against what `compliance_service.py` actually supports today rather than assuming full coverage.

**Proof required**: a real compliance profile with real recurring tasks, due dates, overdue alerts, and filing history for a test client, verified end-to-end through the UI, not just the API.

## Phase 13 — Authority Updates / Government Connectors (your Step 4, first half)

This is the single largest piece of real, non-mock engineering left in the whole roadmap. Current state: 17 connectors, 100% simulated, zero network I/O (Bug #10). Real implementation, one authority at a time, per your Step 4 spec (title/authority/category/dates/source_url/summary/tags/applicability/status/fetched_at), preferring official RSS/API where it exists, respectful rate-limited scraping otherwise, honest "unavailable" marking when a source can't be fetched reliably. **This needs your input on which authorities to prioritize first** (open decision #4 above) — I'd suggest starting with whichever official source has the most reliable public feed (e.g. an RSS-based one) as the first real end-to-end proof of the pattern, then repeating it per source.

**Proof required, per connector**: a real fetched update from the real official source, with its real `source_url`, stored and rendered in the UI — and the connector's `health_check()` reflecting real reachability, not a hardcoded "HEALTHY."

## Phase 14 — Firm Intelligence / Dashboard polish, then Step 5 (UI redesign), Step 6 (testing incl. Playwright), Step 7 (production verification), Step 8 (documentation)

These come last, after the layers above are real, per your own stated ordering — a premium redesign of a dashboard that's still displaying fabricated data doesn't move the product forward. Once Phases 0–13 (or the subset you prioritize) are genuinely done:
- UI redesign to the professional spec in your Step 5, informed by which features actually exist by then (hide anything not done).
- Playwright E2E covering the golden path per feature, plus the backend/API test coverage gaps this audit found.
- Production verification with real API responses, screenshots, console/network status, and DB confirmation for every claimed-working flow — the standard this whole audit was held to, applied going forward.
- Rewrite `README.md`/`DEPLOYMENT.md`/`ARCHITECTURE.md`/`TESTING.md`/`ENVIRONMENT_VARIABLES.md`/`KNOWN_LIMITATIONS.md` to reflect what's actually true at that point, including an honest `KNOWN_LIMITATIONS.md` for anything still mocked or deferred.

---

## How I'll actually execute this

Given the size of this program, I'm not going to attempt Phases 3 onward in one sitting. My plan is: finish Phase 0 next (repository/deployment fixes — I can do essentially all of it directly, no subagents needed, since every bug in it is already fully diagnosed with file:line evidence), report back with real proof at each sub-step, then proceed phase by phase, checking in with you at natural boundaries (especially the 6 open decisions above) rather than batching silent progress across phases.
