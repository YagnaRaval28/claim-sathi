# ClaimSathi: Engineering Standards

| Field | Value |
|---|---|
| Date | 15 October 2026 |
| Applies to | All human and AI contributors |
| Sources | `system-design.md` v1.1 (architecture), `design-system.md` v1.1 (UI), `testing-strategy.md` (quality gates), PRD v1.1 (scope) |

This document sets **how** code is written. It never changes **what** is built: that comes from the PRD and the approved decisions D-001 to D-008.

---

## 1. Working rules (every change)

1. **Read first.** Read the relevant requirement IDs (FR, NFR, AI) and the existing code before editing. Never edit a file you have not read.
2. **Small, reviewable changes.** One backlog task (or part of one) per pull request. Aim for ≤ 400 changed lines, excluding generated files and lock files.
3. **No invented requirements.** If the docs are silent or contradictory, stop. Record the gap in `docs/00-governance/development-readiness.md` §3 and ask.
4. **Tests come with the change.** For bugs, write the failing test first (testing strategy §9.3).
5. **Never weaken a gate to pass.** Do not skip, `xfail`, comment out, loosen thresholds, add `# type: ignore` or `eslint-disable`, or use `--no-verify` to make CI green. A justified exception needs an issue link and reviewer approval in the pull request.
6. **Report honestly.** List checks as **passed**, **failed** or **not run**, with the reason.
7. **Docs follow decisions.** If implementation changes a documented decision, update the governing doc in the same pull request, or open an issue.

---

## 2. Repository and code organisation

- Monorepo layout per system-design §C.5: `apps/web`, `apps/api`, `packages/*`, `eval/`, `infra/`, `docs/`.
- **No speculative structure.** Do not create empty modules, placeholder services, or abstractions with one implementation and no test double. Each adapter Protocol must have a real implementation and a fake used in tests.
- **API layering** (system-design §3.2): routers → services → repositories → database. Adapters are injected. Routers contain no SQL; repositories contain no business rules.

### 2.1 Naming

| Area | Convention |
|---|---|
| Python | `snake_case` modules and functions, `PascalCase` classes, `UPPER_SNAKE` constants. Pydantic schemas end in `In` / `Out` / `Schema`. |
| TypeScript | `camelCase` variables, `PascalCase` components and types. One component per file; the file is named after the component. |
| Database | `snake_case` tables (plural) and columns; `*_at` timestamps (UTC `timestamptz`); `*_paise` money (`bigint`); `*_enc` ciphertext; `*_hash` HMAC lookups |
| API | `/api/v1/` plus plural nouns, kebab-case paths. JSON fields in `snake_case` (same as the DB and Pydantic; the TypeScript client uses generated types). |
| Error codes | `snake_case` from the catalogue in system-design §3.7. New codes are added there first. |
| Requirement links | Tests carry the requirement ID in their name or marker, for example `test_fr015_no_clause_cited_precision` or `@pytest.mark.req("FR-015")` |

---

## 3. Type checking and linting

| Language | Tools | Rule |
|---|---|---|
| Python | ruff (lint and format), mypy | mypy `--strict` for `rules`, `verify`, `ai`, `security`, `auth`; standard elsewhere. No bare `except`. No f-string SQL (bandit/ruff rule). |
| TypeScript | eslint (`eslint-config-next`), `tsc --noEmit` | `strict: true`. No `any` without a justification comment. No hard-coded user-facing strings (NFR-018 lint rule). |
| CSS | stylelint + the design-token rule | No raw hex, px or ms values in components (design DAC-01) |

---

## 4. Frontend conventions

- **Components** follow the design-system §9.2 hierarchy: `primitives/`, `patterns/`, `evidence/`, `features/*`, `layouts/`. **Reuse before creating.** Search the inventory first.
- **Tokens:** consume CSS variables generated from `packages/design-tokens`.
- **i18n:** every string goes in `messages/{en,gu,hi}.json`. A missing key fails CI (NFR-021). Embedded English quotes get `lang="en"`.
- **Data fetching:** TanStack Query with the generated OpenAPI types. **Never hand-write API types.**
- **Required states:** loading, empty, error, success, stale and offline, where the design lists them (DAC-09).
- **AI honesty (design §7):**
  - every fact, quote or AI sentence carries a ProvenanceTag or a CitationTab;
  - no confidence percentages;
  - no fake progress (`ProcessingSteps` shows real steps only).
- **Accessibility:** WCAG 2.2 AA; 44 px targets; visible focus (double ring); keyboard paths; `aria-live` only where specified.
- **Performance budget** (design §9.7): ≤ 170 KB gzip of initial JS per route (PROVISIONAL). Load only the active script's font.

---

## 5. API and database conventions

- **Validation:** Pydantic v2 with `extra="forbid"`, length limits on every string, and enums for every PRD enumeration.
- **Errors:** RFC 9457 problem+json **only**. No stack traces, SQL or paths in responses. A case that is missing or not owned returns **404 with an identical body**.
- **Idempotency:** `Idempotency-Key` is required on endpoints marked IK (system-design §5.1).
- **Concurrency:** optimistic `version` / `If-Match` on mutable resources.
- **Pagination:** cursor-based for admin lists.
- **Migrations:**
  - Alembic only; one revision per pull request; forward-only in production;
  - destructive changes use **expand → migrate → contract** across two releases, with the `expand-contract` pull-request label;
  - `alembic check` must pass;
  - never edit an applied migration.
- **Money and time:** amounts in paise (`int`). Dates as `date` in IST, using the `core.clock` injection; never call `datetime.now()` directly in rules code. Timestamps are UTC.
- **Seeds** are idempotent upserts and contain **no** production data.

---

## 6. Authentication, authorization and cross-user isolation (non-negotiable)

1. **Every case-scoped repository function takes `owner_user_id`.** There is no "get case by id" without an owner.
2. Route dependencies:
   - `CaseAccess` returns 404 for cases the caller does not own;
   - `ConsentGuard` runs on processing endpoints **and at the start of every task handler**.
3. **Every new case-scoped endpoint must be added to the authorization-matrix test** (owner, other user, anonymous, admin, reviewer with grant, reviewer without grant). CI fails if an OpenAPI path with `{id}` is missing from the matrix.
4. **Retrieval filters** (system-design §4.9) live only in the `retrieval` module, and a test proves there is no cross-case retrieval.
5. **Admins** reach case content only through the grant-checked, audited service.
6. **Supabase:**
   - the Data API is disabled (or RLS deny-all);
   - the browser **never** receives the `service_role` key;
   - the `anon` key goes to the browser only if spike S-2 approves it explicitly (CI-04);
   - buckets are private.
7. **Worker endpoints** accept only OIDC-authenticated Cloud Tasks and Scheduler calls (in-process locally).

---

## 7. Uploaded content and AI safety

**Uploads**

- Validate type by **magic bytes**, size and case caps before accepting.
- Scan with ClamAV, failing closed.
- Re-encode images with Pillow (strips EXIF).
- Parse PDFs only in the worker.
- **Never** execute, render as HTML, or follow links from uploaded content.

**PDF passwords** are used in memory for one synchronous request. They are never logged, persisted, enqueued or sent to Sentry. A grep test enforces this.

**Model calls**

- All model calls go through `ModelGateway`. There are no direct SDK calls elsewhere.
- Each call has a versioned prompt file, a Pydantic or JSON output schema, a timeout, retries, and an `ai_calls` row (no content).
- Document text is wrapped as **data**. Instructions found in documents are ignored.
- The model has **no tools**.
- Every displayed quote passes the **citation verifier**. Every number passes the **number scanner** (AI-004, AI-005). Dropped items are logged to `review_items`.
- **PII masking:** after facts are confirmed, identity fields become placeholders. The extraction-call exception requires decision D-B (CI-02).
- **Real documents never go to a free AI tier** (D-008). `LLM_PROVIDER=gemini_dev` is for **synthetic fixtures only**. Startup refuses `gemini_dev` when `APP_ENV` is `staging` or `prod`.

---

## 8. Logging, sensitive data and errors

- Use structlog with an **allowlist** of fields (system-design §3.8). Adding a field needs review.
- **Never log:** bodies, OCR text, field values, emails, names, prompts, model outputs, sign-in codes, passwords or tokens.
- Sentry: `send_default_pii=False`, a scrubbing `before_send`, and an EU organisation.
- Analytics: whitelisted event names and properties only (PRD §7). Amounts are bucketed.
- Exceptions map to catalogue codes, and unexpected ones become `internal_error` with a `request_id`.

---

## 9. Secrets and dependencies

**Secrets**

- Locally, secrets live in `.env` (git-ignored). In the cloud, they live in one Secret Manager bundle per environment.
- gitleaks runs in CI. A secret committed by mistake is **rotated**, not just deleted.

**Dependencies**

- Add a dependency only when the architecture needs it. State why in the pull request.
- Prefer the standard library or existing dependencies.
- Pin through lock files (`uv.lock`, `pnpm-lock.yaml`). Keep `@tiptap/*` packages on one version.
- pip-audit or osv-scanner and npm audit run in CI. High or critical findings block the merge unless waived with an issue and an expiry date.
- No major upgrades without a compatibility check and a green full suite.

---

## 10. Testing expectations

| Code | Required tests |
|---|---|
| Deterministic rules, deadlines, verifier, masker, money and date utilities | Unit tests; **100%** of the rule fixtures (NFR-017) |
| Services and repositories | Integration tests against a real Postgres |
| Endpoints | Contract tests + authorization-matrix entries + error-code assertions |
| UI flows | Playwright E2E for critical journeys (SCN-J*), with the fake AI and OCR adapters |
| AI prompts, schemas, retrieval, knowledge base | Add the `eval-required` label; benchmark run per the evaluation plan §13 before production |

- **Coverage:** ≥ 70% lines on the back end; ≥ 95% branches on `rules`, `verify`, `ai/masking`, `security` (PROVISIONAL).
- **Flaky tests** are fixed or quarantined with an issue within 48 hours. They are never silently retried.

---

## 11. Git workflow and code review

**Branches and commits**

- `main` is always deployable. Work happens on short-lived branches: `feat/T-104-db-migrations`, `fix/DEF-0007-...`.
- Commits follow **Conventional Commits** (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`) and reference the task ID.

**Pull request checklist:**

- [ ] Task ID and requirement IDs linked
- [ ] Tests added or updated; CI green (no skipped gates)
- [ ] Authorization matrix updated (if an endpoint changed)
- [ ] OpenAPI diff reviewed (if the API changed)
- [ ] Migration follows the expand/contract rule (if the schema changed)
- [ ] No secrets, PII or content added to logs or fixtures
- [ ] i18n keys present in en, gu and hi
- [ ] Docs updated if a decision changed
- [ ] `eval-required` label if AI behaviour changed

**Review**

- Self-review the diff for unintended changes before requesting review.
- The solo developer may self-merge after CI passes, **except** for changes to auth, authorization, `verify`, masking, rules or migrations. Those need a second review: an AI reviewer pass plus a documented human read-through.

---

## 12. Documentation requirements

- Governing docs: PRD (scope), design-system (UI), system-design (architecture), evaluation-plan (AI quality), testing-strategy (quality), and this folder (governance).
- Decisions are recorded as `D-xxx` (product owner) or `ADR-xxx` / `UD-xxx` (architecture) **in the governing doc**, never only in chat or commits.
- The README and the setup guide must stay runnable. If a command changes, the doc changes in the same pull request.
