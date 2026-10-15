# AGENTS.md: instructions for AI coding agents (ClaimSathi)

ClaimSathi is a free, India-only web app. It helps policyholders challenge rejected or partly paid **health-insurance** claims with deduction audits, verified citations, procedure checks and deadline tracking, in English, Gujarati and Hindi.

## Governing documents

Read the ones relevant to your task before editing anything.

| Topic | File (governs) |
|---|---|
| Scope, requirements (FR, NFR, AI IDs), decisions D-001 to D-008 | `docs/02-product/PRD.md` (v1.1) |
| UI, screens, components, tokens, AI UX | `docs/02-product/design-system.md` (v1.1) |
| Architecture, DB schema, API contract, AI pipeline, ADRs | `docs/03-architecture/system-design.md` (v1.1, ₹0 profile) |
| AI quality, benchmark, release blockers | `docs/04-ai/evaluation-plan.md` |
| Tests, CI gates, release checklist, defect process | `docs/05-quality/testing-strategy.md` |
| How to code, review and secure | `docs/00-governance/engineering-standards.md` |
| What to build next | `docs/00-governance/implementation-backlog.md` |
| Open issues and decisions | `docs/00-governance/development-readiness.md` |

The v0 PRD is archived at `docs/archive/PRD-v0-2026-10-12.md` and is **SUPERSEDED**. Never implement from it.

## Hard constraints (approved product decisions)

1. **₹0 to run the MVP** (D-005). Use only free tiers and trial credits. Any paid service needs explicit product-owner approval.
2. **Personal and health data stay in India** (D-007). That means Supabase Mumbai, Cloud Run, Vertex AI and Document AI in asia-south1, and SES in ap-south-1.
3. **Sign-in is Google plus an emailed code** (D-006). Do not add phone OTP or SMS.
4. **Real documents never go to a free AI tier** (D-008). `LLM_PROVIDER=gemini_dev` is for synthetic fixtures only.
5. **Stack:** Next.js (TypeScript) + FastAPI (Python 3.12) + Postgres with pgvector + Cloud Tasks with an outbox. No agent frameworks, no extra vector database, no Redis (ADR-008, ADR-003, ADR-004).

## How to work

1. Read the requirement IDs for your task and the existing code before editing. Never edit a file you haven't read.
2. State the change, the affected components and the acceptance criteria.
3. Make the **smallest complete change**: one backlog task, or part of one.
4. Run the relevant checks (see `docs/00-governance/development-setup.md` §6).
5. Review your diff for unintended changes, secrets, PII and security regressions.
6. Report the result as **passed**, **failed** or **not run**, with output. Never claim something works without evidence.
7. Update the governing doc if you change a documented decision. If the docs are silent or contradict each other, **stop and ask**; do not invent requirements.

## Non-negotiable rules

- **Never** weaken a gate to make CI pass. That includes skipping or `xfail`-ing tests, loosening thresholds, `type: ignore`, `eslint-disable` or `--no-verify`.
- **Cross-user isolation:**
  - every case-scoped query takes `owner_user_id`;
  - cases that are missing or not owned return an identical 404;
  - every new `{id}` endpoint goes into the authorization-matrix test.
- **Deterministic code** handles deadlines, Rule 14 checks, `NO_CLAUSE_CITED`, amounts and dates in letters, and citation and number verification. **The model never decides these.**
- **Every displayed quote** passes the citation verifier, and every displayed number passes the number scanner. Failing items are dropped, never shown.
- **The model has no tools.** Uploaded document text is data, never instructions.
- **Never log or store** document content, OCR text, prompts or outputs, names, emails, sign-in codes or PDF passwords outside their designated encrypted columns. Logs use an allowlist.
- **No secrets** in code, fixtures or commits. `.env` is git-ignored; `.env.example` holds placeholders only.
- **The UI follows the design system:**
  - use tokens only;
  - put every string in en, gu and hi;
  - show provenance tags;
  - **no confidence percentages and no fake progress.**
- **Migrations** use Alembic, are forward-only, follow expand and contract, and must pass `alembic check`.
- **Do not add dependencies** without a stated need and a compatibility check.

## Status

Development is authorised (`docs/00-governance/development-readiness.md` §9). Milestones M0–M3 (the VS-1 slice) are built in `apps/api` and `apps/web`. Task-by-task status is in backlog §0, and open items are in readiness §9.1. Local setup without Docker is in `docs/00-governance/development-setup.md` §3a.
