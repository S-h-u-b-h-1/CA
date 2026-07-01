# CA Intelligence — Repository Cleanup Plan

**Date**: 2026-07-01
**Scope**: Repo hygiene, git/submodule integrity, and deployment configuration only — no feature work. Ordered by urgency. Bug numbers reference `MASTER_BUG_REPORT.md`.

---

## 0. Before anything else: back up the frontend submodule's history

`frontend/.git/config` has no remote configured — 22 commits exist only on this machine (Bug #1). Whatever else happens in this cleanup, this needs to stop being true before I touch the submodule structure at all, because several of the fixes below (§1) involve changing how `frontend/` is tracked.

**This is a decision, not just a fix, and I'll ask you directly before acting**: the repo's recurring "fix: update frontend submodule reference" commits (5 of them in history) show the submodule split has been actively causing pointer-drift bugs since it was introduced, for no benefit I can find — nothing in the deployment topology actually requires `frontend/` to be a separate git repo (Vercel just needs a Root Directory setting, not a submodule boundary). My recommendation is to **de-submodule it**: fold `frontend/`'s current working-tree content into the main repo as a normal tracked directory, preserving today's files exactly, and stop maintaining a second git history for it. The alternative is to keep it a submodule but properly wire it up (create a real GitHub remote for it, push its 22 commits there, add a correct `.gitmodules`). I'll ask which you want before doing either, since one of them makes the submodule's independent commit history unreachable from the main repo (recoverable via `frontend/.git`'s reflog for a while, but not forever).

## 1. Git/submodule integrity (Critical — Bugs #1, #2)

- Resolve per the decision above.
- If de-submoduling: `git rm --cached frontend`, remove the nested `frontend/.git`, `git add frontend`, one clean commit. Verify with `git ls-files frontend | head` that files are now tracked as regular blobs, not a gitlink.
- If keeping it a submodule: create a real remote, push, add a correct `.gitmodules` with the right URL/branch, re-add the submodule properly, verify a fresh `git clone --recursive` in a scratch directory actually populates `frontend/`.
- Either way: **verify a truly fresh clone works** before calling this done — clone into a throwaway directory, run `npm install && npm run build` and `pip install -r requirements.txt && pytest` from that clone, not this working copy.

## 2. Commit or discard the in-flight Compliance feature (Critical — Bug #3)

Right now the Compliance feature is uncommitted across 5 backend files and 3 frontend files. Before any further work on it, it needs a clean commit boundary (or, if it's not ready, an explicit decision to shelve it). This audit found real bugs in it (missing soft-delete filters, no Alembic migration, unreachable frontend UI) — those get fixed as part of Step 2/3 execution (see `IMPLEMENTATION_ROADMAP.md`), then committed together as one coherent, working feature rather than left in limbo.

## 3. Fix the Vercel deployment topology (Critical — Bugs #4, #5, #38)

- The "backend" Vercel project (`prj_nvkMwfYeAjJZ2briczkvG9iksjh9`) needs its dashboard **Root Directory** changed from the repo root to `backend/`, so it builds from `backend/vercel.json` (API-only) instead of the root monorepo config. This is a Vercel dashboard/API setting, not a file in this repo — I can attempt it via the Vercel API once we're at that step.
- Decide what to do with the orphaned "backend-chi" project (`prj_0qo0NFTiACK961gCggo5es6ts7rL`, domain `backend-chi-theta.vercel.app`) — recommend deleting it once confirmed unused, to stop the naming confusion.
- Decide what to do about `ca-intelligence.vercel.app` — it's not available to this account (Bug #5). Options: rename an existing project to try to claim a different available name, add a custom domain you own, or keep the current `ca-intelligence-frontend.vercel.app` domain as production and document that decision. I'll present the real options (and what the Vercel API actually allows) when we get to the deployment step, rather than assume one now.
- Simplify to two `vercel.json`s (`backend/vercel.json`, `frontend/vercel.json`) once the Root Directory settings are correct, and consider whether the root `vercel.json` monorepo config should be deleted entirely to remove the possibility of this drift recurring.

## 4. Fix or remove the Docker path (Critical — Bug #6; Low — Bug #95)

- Fix the `0.0.5.0` → `0.0.0.0` typo in `backend/Dockerfile`.
- Add a `backend/.dockerignore` excluding `.env*`, `venv/`, `__pycache__/` (Medium — Bug #57) before this path is trusted again.
- Actually run `docker compose up` end-to-end and confirm all three services come up healthy before treating this as a viable alternative deployment path — don't just fix the typo and assume it works.
- If nobody actually uses this path today, consider whether maintaining it is worth the ongoing cost, or whether it should be removed until someone needs it — a stale, broken "alternative deployment" is worse than no alternative deployment, because it looks like an option that silently isn't one.

## 5. Fix the broken test suite (Critical — Bugs #13, #14)

- Fix the `NoticeParser` import in `tests/test_platform.py` to reference the actual current parser classes (`GSTNoticeParser`/`IncomeTaxNoticeParser`).
- Fix the shared-global-state test-isolation bug: each test file should scope its `app.dependency_overrides[get_db]` per-test (or per-module with proper setup/teardown ordering) rather than mutating the same module-level `app` singleton at import time. The cleanest fix is a shared `conftest.py` with a single fixture-scoped engine/override, replacing the 7 files' duplicated ad hoc setup.
- Only after both of the above: re-run the full suite and get a real, reproducible pass/fail count — don't claim a number without running it.

## 6. Security/config hygiene (Critical/High — Bugs #18, #21, #23, #55, #56, #76)

- Remove the hardcoded `JWT_SECRET` fallback; fail fast at startup if it's not set when `ENV != development`.
- Fix `CORS_ORIGINS` to have a real, non-wildcard default, and document it in `.env.example`.
- Remove the literal Neon connection string and JWT secret value from `README.md`; replace with placeholders.
- Add `CORS_ORIGINS` and a `frontend/.env.example` (with `NEXT_PUBLIC_API_URL`) so a new environment can actually be provisioned from the example files as intended.
- Rotate any real secrets that were ever committed or are sitting in local `.env`/`.env.local` files, out of caution, once we've confirmed which (if any) are live credentials rather than dev-only placeholders.

## 7. Stray files and workspace hygiene (Medium/Low — Bugs #75, #92, #93)

- Add `backend/scratch_docs/` to `.gitignore` (or move its 4 fixture PDFs into a proper `backend/tests/fixtures/` directory and commit them intentionally as real test fixtures — probably the better move, since they're clearly being used for parser validation).
- Delete the stray root-level empty `caintelligence.db` and the empty top-level `uploads/` directory; confirm `DATABASE_URL` and `LOCAL_STORAGE_DIR` are always resolved relative to a consistent working directory so a duplicate doesn't reappear.
- Add a retention/cleanup story for `backend/uploads/` (currently 29 unbounded runtime artifacts) — at minimum a `.gitignore`-respecting cleanup script for local dev; production already redirects to ephemeral `/tmp` so this is a local-only concern.

## 8. Dead code and drift cleanup (Medium/Low — Bugs #52, #53, #77, #78)

- Fix `models/__init__.py` to export all current models, or delete it in favor of consistently importing from `app.models.models` everywhere (pick one convention, not both).
- Add the missing `ForeignKey()` constraints on `ComplianceTask.assigned_user_id`/`document_id` and `ComplianceAlert.task_id`.
- Remove the unused `RoleChecker` class, or actually adopt it and delete the duplicated inline role-check blocks — not both.
- Extract the 7-times-duplicated assessment-year normalization snippet in `clients.py` into one helper function.

## 9. CI (High — Bug #46)

- Add a minimal GitHub Actions workflow that runs on every push/PR: backend `pytest`, frontend `npm run build` + `npm run lint`, at minimum. This is the single highest-leverage fix to prevent this exact class of "claimed working, actually broken" drift from recurring — it should land early, once the test suite itself is fixed (§5), not before.

---

## Sequencing

Items 1–2 are prerequisites for everything else (you can't cleanly build on top of an unrecoverable git history or an uncommitted feature). Items 3–6 are the concrete "Step 2: Repository & Deployment Fixes" the roadmap treats as the first real implementation slice. Items 7–9 are lower-urgency and can land alongside or shortly after, without blocking feature work.
