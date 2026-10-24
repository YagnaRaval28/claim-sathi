# ClaimSathi: Development Readiness Assessment

| Field | Value |
|---|---|
| Date | 15 October 2026 |
| Scope | Every file in `C:\Users\yagna\ClaimSathi` (inspected, not assumed) |
| Companion documents | `repository-audit.md`, `development-setup.md`, `engineering-standards.md`, `implementation-backlog.md`, `/AGENTS.md`, `/.env.example` |
| Verdict | **NOT READY for feature implementation.** Readiness is blocked by 2 product decisions and 2 technical verifications (§4). Repository setup (milestone M0) and two zero-cost technical spikes **can start** once the product owner approves this report. |

**Labels used in this document**

| Label | Meaning |
|---|---|
| **VERIFIED** | Checked during this audit (file inspected, command run, official page read) |
| **RECOMMENDATION** | My proposal |
| **ASSUMPTION** | Not checked |
| **OPEN** | Needs a human decision |

---

## 1. Overall assessment

The **documentation is unusually complete for a pre-build project**: research, PRD, design system, architecture, AI evaluation plan and testing strategy all exist, are cross-referenced, and were updated together for the ₹0 MVP constraints (D-005 to D-008).

**No code exists.** The folder is not a git repository (VERIFIED), so it is not under version control.

**What stops implementation today:**

1. **The PRD's own gate (PRD §10.1).** It says implementation may start only after the validation sprint: competitor teardown, 15–20 interviews, a legal opinion, and the OCR and data spikes. None of these has happened, and no evidence files exist. This is a product-owner decision: run the sprint, or explicitly waive or scope it (for example, "build for a closed beta while validating in parallel").
2. **The PII-masking rule cannot be met for extraction as written (PRD AI-002 versus system-design UD-02).** The first AI step has to see names in order to extract them. It needs a PRD amendment before any real document reaches the model.
3. **Two zero-cost assumptions are unverified:**
   - Whether Supabase Free can host a project in Mumbai with pgvector (UD-12).
   - Whether browser uploads can go directly to Supabase Storage without exposing a Supabase key (CI-04).

   Both are cheap spikes.
4. **A hidden cost conflicts with D-005 (₹0).** Reliable email delivery (SES out of the sandbox, SPF and DKIM) and a production Google OAuth consent screen both appear to require a **domain you own**. Buying one costs about ₹700–1,000 a year (ESTIMATE). This needs a decision (CI-22, CI-23).

**What is ready:**

- MVP scope and priorities;
- screen inventory and states;
- data model and API contract;
- AI pipeline, verifier and evaluation design;
- test traceability;
- the ₹0 stack.

The **first vertical slice** is defined with acceptance criteria (§7 and `implementation-backlog.md` M3).

---

## 2. Documentation inventory

| # | Document | Path | Purpose | Exists | Complete enough? | Depends on | Missing sections / unresolved |
|---|---|---|---|---|---|---|---|
| 1 | Competitor and novelty research | `docs/01-discovery/competitor-research.md` | Opportunity, competitors, validation plan | Yes (VERIFIED, 608 lines) | Yes for discovery. **Its validation plan has not been executed.** | — | Results of the §11 validation sprint (teardown, interviews) |
| 2 | Product opportunity / user-validation report | — | Evidence that users want this | **No** | — | 1 | Whole document (PRD §10.1 gate). Personas remain hypotheses. |
| 3 | PRD v1.1 | `docs/02-product/PRD.md` | Scope, FR/NFR/AI requirements, metrics, risks, release criteria | Yes (1,663 lines) | Yes | 1 | OQ-02 to OQ-08, OQ-10, OQ-13 to OQ-15 open; AI-002 amendment (CI-02); NFR-011/014 restatement (CI-08, CI-09) |
| 4 | Original PRD v0 | `ClaimSathi — Product Requirements Document.md` (repository root) | Superseded first draft | Yes | **Superseded.** It contradicts v1.1 (phone OTP, Celery, awards). | — | Should be marked superseded and archived (CI-18; needs permission) |
| 5 | UI/UX design system v1.1 | `docs/02-product/design-system.md` | IA, routes, wireframes, tokens, components, AI UX, accessibility | Yes (1,685 lines) | Yes | 3 | DQ-01, 04, 06, 07 open (non-blocking); CI-11, CI-12, CI-15 fixes |
| 6 | System architecture v1.1 (₹0 profile) | `docs/03-architecture/system-design.md` | Stack, diagrams, modules, DB schema, API contract, RAG, workflow, security, ADRs, environment variables, staged plan | Yes (1,687 lines; 7 Mermaid diagrams validated with the mermaid 11.4.1 parser, VERIFIED) | Yes | 3, 5 | UD-01 to UD-12; CI-04, CI-05, CI-21 to CI-23 |
| 7 | Database schema and API contract | Inside 6 (§4, §5) | — | Yes | Yes. No separate file is needed. | 6 | OpenAPI file to be generated from code (by design) |
| 8 | AI/GenAI design, RAG and workflow | Inside 6 (Part B) | — | Yes | Yes. No agents by design (ADR-008). | 6 | — |
| 9 | AI evaluation plan | `docs/04-ai/evaluation-plan.md` | Metrics, dataset, baselines, blockers, bake-off | Yes (417 lines) | Yes | 3, 6 | `eval/ANNOTATION_GUIDE.md`, the `SAMPLE-WORDING-001` fixture and the runner don't exist (CI-17); reviewers not sourced (CI-20) |
| 10 | Benchmark schema and samples | `eval/schema/benchmark-case.schema.json`, `eval/fixtures/synthetic/cases.jsonl` | Dataset format | Yes. Earlier in this session, 10 cases validated against the schema and 6 deliberately broken cases were rejected. | Sample only (by design) | 9 | Full 100-case set |
| 11 | Software testing strategy | `docs/05-quality/testing-strategy.md` | Traceability, scenarios, security, performance, gates, release checklist, defect process | Yes (687 lines) | Yes | 3, 5, 6 | — |
| 12 | Security and privacy requirements | Distributed: PRD NFR-004–009, architecture §3.4/§10/§C.8, testing §4 | — | Yes (distributed) | Yes | — | Privacy notice text and breach runbook (needs legal, OQ-10) |
| 13 | Implementation roadmap | PRD §12 backlog, architecture §C.10 stages | — | Yes (high level) | Now detailed in `implementation-backlog.md` | 3, 6 | — |
| 14 | README / AGENTS.md / project instructions | — | Agent and contributor guidance | **No** (created now: `AGENTS.md`) | — | all | — |
| 15 | `.env.example` | — | Environment contract | **No** (created now) | — | 6 | — |

---

## 3. Consistency audit

The "Governs" principle follows the brief: **approved product-owner decisions (D-001 to D-008) and the PRD come first**. For UI, the design system governs. For how things are built, the architecture governs.

| ID | Affected documents | Description | Severity | Consequence if unresolved | Recommended resolution | Human decision? |
|---|---|---|---|---|---|---|
| **CI-01** | PRD §10.1; research §11 | The PRD states "implementation may start only when" the validation sprint passes. No sprint evidence exists. | **Blocker** | Building without the gate contradicts the approved PRD. The kill test (are competitors already accurate?) is unanswered. | Either run the sprint (2–6 weeks, mostly non-code), **or** have the product owner record an explicit waiver or scope change, for example: "build to closed beta; teardown and interviews in parallel; the kill test still applies before public launch". | **Yes, product owner** |
| **CI-02** | PRD AI-002; architecture §10.1 / UD-02 | AI-002 says identity fields are masked before **any** model call. Extraction must see names to find them. | **Blocker** (for real documents) | Either AI-002 is violated, or extraction cannot work | Amend AI-002: "Extraction calls may include names and policy identifiers, because processing stays in India (Vertex asia-south1) with abuse-logging opted out. All later calls use placeholders." Synthetic-data development can proceed meanwhile. | **Yes, product owner (+ legal)** |
| **CI-03** | Architecture UD-12, §4.9 | Supabase Free allowing **Mumbai** and **pgvector** is not confirmed in the docs (the region list and extension docs say nothing about plan limits). | **High** (blocks cloud set-up, not local development) | The ₹0 plus India-residency database could fail | Spike S-1: create a Free project, pick Mumbai, run `create extension vector`. Fallback: Cloud SQL on trial credit (90 days), then a decision. | No (verification) |
| **CI-04** | Architecture ADR-012, §3.9, §5 (uploads); design CASE-01 | Supabase resumable (TUS) uploads accept a signed upload token in an `x-signature` header (VERIFIED on Supabase docs). Its examples also send an `apikey`/authorization header. The architecture forbids Supabase keys in the browser. | **High** | The upload design may not work as written | Spike S-2. **Default if unresolved:** upload through our API (one request per file of 20 MB or less, client retries up to 3 times per FR-009). This keeps every key server-side. Cloud Run's request-size limit must be confirmed in the spike (believed 32 MiB on HTTP/1; UNVERIFIED). Update ADR-012 after the spike. | No |
| **CI-05** | Architecture §C.10 Stage 4b; PRD D-005 | Cloud Run needs a billing account. Opening the GCP trial starts the 90-day clock, which also governs the AI credit. | High | The trial may expire before the beta | **Build M0–M8 locally** (₹0, no cloud). Open GCP only at M9. For AI work before M9, use the Gemini Developer API free tier **with synthetic data only** (allowed by D-008, which bans free tiers only for real documents). | **Yes, product owner** (confirm timing) |
| **CI-06** | PRD FR-005; architecture UD-01 | The consent notice must name the AI provider and processors. The model is still "proposed". | High | Consent copy cannot be finalised | Approve UD-01: Google (Vertex AI Gemini 2.5 Flash, Document AI), Supabase and Amazon SES as processors | **Yes, product owner** |
| **CI-07** | PRD OQ-10 | No legal review of disclaimers, consent, retention, deadline interpretation ("one month"), or unauthorised-practice risk | High (blocks beta, not development) | Launch-blocking legal risk | Engage a lawyer before M10. Development uses PROVISIONAL rule parameters. | **Yes, product owner** |
| **CI-08** | PRD NFR-014; architecture §1.4 | NFR-014 requires 2,000 cases a month and 50 concurrent jobs. The ₹0 stack holds about 50 active cases (1 GB storage), roughly 1,200 AI cases of credit, and AI queue concurrency of 4. | High | A test target can never pass under D-005 | Reclassify NFR-014 as a scale-up target, and add an MVP capacity target: about 50 active cases and 10 concurrent pipelines (PROVISIONAL). D-005 governs. | **Yes, product owner** (confirm) |
| **CI-09** | PRD NFR-011; architecture §0.2 | 99.5% availability versus free tiers with no SLA, project pausing and cold starts | Medium | A misleading commitment | Restate as "best effort, measured" for the beta. Keep 99.5% as a scale-up target. | Yes (confirm with CI-08) |
| **CI-10** | PRD FR-007/FR-008; architecture §4.5 | 10 open cases × 50 MB = 500 MB per user, against a **1 GB global** storage tier. There is no requirement to refuse uploads when storage is nearly full. | High | One or two heavy users could exhaust storage for everyone | Add a **global storage guard**: refuse new uploads at 95% storage (`503 storage_full`) and alert at 80%. Optionally lower open cases to 3 per user for the beta. | Yes, for the per-user cap; the guard itself is technical |
| **CI-11** | Design ADM-01; architecture §3.4 | The design says admin sign-in is "Email/password and a TOTP code". The architecture uses a Google allowlist plus TOTP, with no passwords. | Medium | UI built wrongly | The architecture governs (no password storage). Fix design ADM-01. | No |
| **CI-12** | Design ONB-02; PRD D-006 | The consent screen reveals "an email field when reminders are ticked". The email is now the sign-in identity, so it is always known. | Low | Redundant field | Show the sign-in email read-only, with a "Change in Settings" link | No |
| **CI-13** | PRD FR-036; architecture §5 | The PRD says email change is "verification by a link". The architecture uses a 6-digit code (`/me/email/verify`). | Low | Inconsistent implementation | Use the code, which is consistent with sign-in. Edit PRD FR-036. | No |
| **CI-14** | PRD §7.1 analytics | `signup_completed` property `method (otp / google)` should be `(email / google)` | Low | Wrong analytics enum | Edit the PRD | No |
| **CI-15** | Design route table; architecture §5 | The design lists `/auth/google/callback` as a web route. The architecture's callback is `/api/v1/auth/google/callback`. | Low | OAuth redirect misconfiguration | The OAuth redirect URI is the API path, proxied through the web origin. Fix the design route table. | No |
| **CI-16** | Architecture §1.1 (TypeScript) | The npm `typescript@latest` is **7.0.2** (VERIFIED), the native rewrite. Its compatibility with Next.js 16.4.1 tooling is **UNVERIFIED**. | Medium | Broken builds or type-checking | Use the TypeScript version that `create-next-app@16.4.1` installs, and pin it. Re-evaluate TS 7 separately. | No |
| **CI-17** | Evaluation plan §9; testing §1.4 | Referenced artefacts don't exist: `eval/ANNOTATION_GUIDE.md`, the `SAMPLE-WORDING-001` v1/v2 fixture, the eval runner, the insurer seed list, glossary seeds, consent-notice text, and email template text. | Medium | Tests and evaluation cannot run | Backlog tasks T-305, T-306, T-1001 to T-1003 | No (content needs native/legal review later) |
| **CI-18** | Root `ClaimSathi — Product Requirements Document.md` | The v0 PRD sits beside v1.1 and contradicts it. A coding agent could read the wrong one. | Medium | Agents implementing superseded requirements | With permission: move it to `docs/archive/` and add a "SUPERSEDED by docs/02-product/PRD.md" banner. Until then, AGENTS.md names the governing files explicitly. | **Yes (permission to move the file)** |
| **CI-19** | PRD OQ-02 to OQ-08, OQ-13 to OQ-15 | CIO form fields, accepted letter languages, Bima Bharosa limits, primary grievance timeline, PED rule, group policies, top-10 products, grievance officer, accuracy-page timing, delay mode | Medium (each blocks one feature, not the start) | Features built on defaults may need rework | Keep the PRD defaults. Each is resolved before its milestone (see the backlog "Decision gate" column). | Yes, by milestone |
| **CI-20** | Evaluation plan §14; PRD NFR-021 | No domain reviewer or native Gujarati and Hindi reviewers have been sourced | High (blocks release, not development) | AI release thresholds cannot be measured; L10N sign-off impossible | Source them before M10 | **Yes, product owner** |
| **CI-21** | Architecture §1.1 | Unverified technical assumptions: Cloud Run deploying the ClamAV image from Docker Hub; Document AI in asia-south1 ("limited support"); trial credits covering Vertex and Document AI; Cloud Run's request size limit | Medium | Rework at M4 and M9 | Spikes S-3 and S-4 at M9. Fallbacks are documented in the architecture. | No |
| **CI-22** | Architecture UD-11 (`*.run.app` URL); PRD FR-002 | A production Google OAuth consent screen normally requires **authorized domains you own**. `run.app` cannot be verified by us. Testing mode limits sign-in to listed test users. (UNVERIFIED; based on knowledge of Google's console, not checked during this session.) | High | Google sign-in, the primary login, may only work for listed test users | For the closed beta: OAuth in Testing mode with listed test users (enough for about 30 beta users if the limit is 100; verify). Before public launch: buy a domain. | **Yes, product owner (₹0 exception)** |
| **CI-23** | Architecture §1.1 Email; PRD FR-001 | SES requires a verified identity. Leaving the sandbox and achieving deliverability (SPF, DKIM, DMARC alignment) realistically needs **your own domain**. Sending as an `@gmail.com` address fails DMARC alignment (ASSUMPTION, standard email practice). | High | Email codes and reminders land in spam or are refused | A domain (about ₹700–1,000 a year) is the **only recommended exception to ₹0**. Alternative: Google-only sign-in for the closed beta, with email codes and reminders deferred (but this conflicts with D-006). | **Yes, product owner** |
| **CI-24** | Testing strategy §5.3; evaluation plan §15.4 | The credit budget (≤ $100 for tests and evaluation) depends on Vertex being payable from the trial (CI-21) | Low | — | Check in spike S-4 | No |

**Checked and found consistent** (no issue raised):

- PRD FR-001 to FR-003 match design AUTH-01/02 and architecture §3.4 and §5 (email code, 60 s resend, 5 attempts, 10-minute expiry).
- Upload caps (15 files / 50 MB / 60 pages) match across PRD FR-008, design CASE-01, architecture §4.2/§5 and testing FR-008.
- The audit statuses, 14-category taxonomy, Rule 14 rules and deadline semantics match across PRD, architecture, testing and the benchmark schema.
- The provenance and "no confidence %" rules match across design DD-07, architecture `confidence_flag` and testing DAC-10.
- Release blockers in the evaluation plan §15.1 map to the testing gates (§6.3) and the PRD release criteria.

---

## 4. Blocking issues and required decisions (batched)

| # | Decision | Recommended answer | Unblocks |
|---|---|---|---|
| D-A | **CI-01:** run the validation sprint first, or waive or scope the PRD §10.1 gate? | Waive for development up to a **closed beta**. Run the teardown and interviews in parallel. The kill criterion still applies before public launch. | All implementation |
| D-B | **CI-02:** amend AI-002 to allow names in the extraction call (India-resident processing only)? | Yes, with legal confirmation before real documents are processed | Real-document AI (M5+); synthetic work can proceed without it |
| D-C | **CI-22/23:** allow one ₹0 exception, a domain at about ₹700–1,000 a year? Or Google-only sign-in for the beta? | Buy a domain before the closed beta | Email deliverability; OAuth beyond test users |
| D-D | **CI-05:** confirm local-first build (M0–M8) and open the GCP trial only at M9; Gemini free tier with **synthetic data only** for AI work before M9 | Yes | AI spike; trial timing |
| D-E | **CI-08/09/10:** restate NFR-014 and NFR-011 as scale-up targets with MVP beta targets; add a global storage guard; lower the open-case cap to 3 for the beta? | Yes, yes, yes | Testable NFRs |
| D-F | **CI-06:** approve UD-01 (Gemini 2.5 Flash, Vertex, Mumbai), UD-03 (stack) and UD-05 (custom auth) | Approve | Consent copy; auth build |
| D-G | **CI-18:** permission to move the v0 PRD to `docs/archive/` with a superseded banner? | Yes | Agent safety |
| D-H | **CI-07/20:** engage a lawyer, a domain reviewer and native gu/hi reviewers before M10 | Yes; start sourcing now | Beta release |

Non-blocking open questions with working defaults:

- PRD OQ-02 to OQ-08, OQ-13 to OQ-15;
- design DQ-01, 04, 06, 07;
- architecture UD-04, 06, 07, 08, 09, 10.

**Approved decisions preserved** (not changed by this audit):

| ID | Decision |
|---|---|
| D-001 | Opportunity A |
| D-002 | en, gu, hi |
| D-003 | Free for users |
| D-004 | Partial disallowances + rejections |
| D-005 | ₹0 |
| D-006 | Google + email code |
| D-007 | India residency |
| D-008 | Paid no-training AI on credits |
| — | Design: 0–9 digits, English admin, no logo |

---

## 5. Gate assessment

| Gate | Status | Evidence | Remaining actions | Owner |
|---|---|---|---|---|
| **A. Product scope and novelty evidence clear** | **BLOCKED** | Scope is clear (PRD v1.1, D-001 to D-008). The novelty evidence explicitly says the core idea is *not* novel, and the differentiation is unvalidated (research §1, §12). The PRD §10.1 gate is unmet (CI-01). | Decision D-A; then the teardown and interviews | Product owner |
| **B. Requirements and design consistent** | **PASS with fixes** | 24 issues logged. The blockers are CI-01 and CI-02 (product). The design-level fixes (CI-11 to CI-15) are low or medium and mechanical. | Apply CI-11 to CI-15 and the CI-08/09/10 restatements after approval | Developer (edits), product owner (CI-08/09/10) |
| **C. Architecture, APIs, data models implementable** | **NOT VERIFIED** | Complete schema, API contract, module map and ADRs (VERIFIED by inspection). Diagrams validated. Two load-bearing assumptions unverified: Supabase Free in Mumbai + pgvector (CI-03), and the direct-upload path (CI-04). | Spikes S-1 and S-2 | Developer |
| **D. Environment and dependencies understood** | **PASS (local) / NOT VERIFIED (cloud)** | Tools inspected: Node 22.17.0, npm 11.2.0, Corepack 0.33.0, Python 3.13.5/3.11 (+ uv 0.10.9 can provision 3.12), Docker 29.2.0 (**daemon not running**), psql 18.1, AWS CLI 2.37.6, git 2.40. Missing: pnpm (via Corepack), gcloud, Terraform, Supabase CLI. Package versions and peers checked on npm/PyPI (repository-audit §4). | Start Docker Desktop; enable pnpm; install cloud CLIs at M9 | Developer |
| **E. Security and privacy defined** | **PASS (spec) / BLOCKED (legal)** | Authorization model, BOLA tests, PII masking, logging allowlist, Supabase hardening (Data API toggle VERIFIED to exist), threat model | Legal review (CI-07); AI-002 amendment (CI-02) | Product owner + lawyer |
| **F. AI behaviour and evaluation specified** | **PASS (spec) / NOT VERIFIED (data, people)** | Schemas, verifier, blockers B1–B10, metrics, baselines, budget. Schema validated against 10 samples. | Annotation guide, gold set, reviewers (CI-17, CI-20); AI spike S-5 | Developer + product owner |
| **G. Testing and acceptance actionable** | **PASS** | Every FR, NFR and AI requirement maps to test IDs, with an expected result and an automation level (testing strategy §2) | Create test harnesses in M0/M1 | Developer |
| **H. First vertical slice ready** | **PASS (definition) / BLOCKED (start)** | VS-1 defined with acceptance criteria (§7; backlog M3) | Needs D-A (gate) and D-D (local-first, synthetic AI) | Product owner |

**Conclusion.** Ready for **M0 (repository setup) and spikes S-1, S-2 and S-5** once the product owner approves this report. Ready for **feature implementation (M1+)** after decisions D-A, D-D and D-F, plus spikes S-1 and S-2 passing or their fallbacks being accepted.

---

## 6. Technical spikes (zero-cost, time-boxed)

| Spike | Question | Method | Pass | Fallback | Cost |
|---|---|---|---|---|---|
| **S-1** | Supabase Free in Mumbai, with pgvector? | Create a Free project; select "South Asia (Mumbai)"; run `create extension vector`; disable the Data API | Region selectable; extension created; REST endpoints return errors | Cloud SQL on trial credit (90 days) | ₹0 |
| **S-2** | Browser-to-storage upload without exposing secret keys? | `createSignedUploadUrl` + TUS with `x-signature`, with and without `apikey`; check what the browser needs | Only a short-lived, path-scoped token is needed, **or** the publishable anon key is acceptable with RLS deny-all | Proxy uploads through the API (≤ 20 MB per request) | ₹0 |
| **S-3** | Cloud Run accepts the Docker Hub ClamAV image; request-size limit | Done at M9 | Deploys; a 20 MB request is accepted | Mirror the image to Artifact Registry (watch the 0.5 GB limit) | ₹0 within the free tier |
| **S-4** | Trial credits pay for Vertex and Document AI in asia-south1; Gujarati OCR accuracy | Done at M9 | A billing report shows credits applied; OCR accuracy measured on 20 synthetic photos | Sarvam (paid) / Cloud Vision | Cents of credit |
| **S-5** | Can Gemini 2.5 Flash return schema-valid extraction and verbatim quotes that pass our verifier? | Gemini Developer API free tier, **synthetic cases SYN-001 to SYN-010 only**; pass rates measured with the deterministic verifier | Structured-output validity ≥ 90% and verifier pass rate ≥ 80% on the samples (PROVISIONAL; this is an indicator, not the release gate) | Revisit prompts or the model in the bake-off | ₹0 (free tier; synthetic data only, per D-008) |

---

## 7. First vertical slice (VS-1): summary

**Journey.** A signed-in user (email code) gives consent, then creates a partly-paid case. They upload **one text-layer PDF** settlement letter (synthetic, `SYN-001`-style). They confirm the extracted facts and line items. They see the **deterministic Para 17(b) audit** (`NO_CLAUSE_CITED` lines), with a **verified citation** to the ingested Master Circular chunk. Finally, they download an **English Stage-1 "basic mode" letter as PDF**.

**Crosses every layer:**

| Layer | What VS-1 exercises |
|---|---|
| Frontend | AUTH, ONB, APP-02, CASE-01/02/03/04 (subset), CASE-06 (download) |
| API and database | Auth, consent, cases, documents, facts, line items, analysis (deterministic), letters, exports |
| AI | Extraction through `ModelGateway`: recorded fake in CI; Gemini free tier with synthetic data in development |
| Verification | Citation verifier |

**Deliberately excluded:**

- OCR of photos, ClamAV, Gujarati and Hindi (the UI shell is translated; letters are English);
- counter-point generation, translation, escalation and reminders;
- Google sign-in (M2 runs in parallel), cloud deployment.

Full acceptance criteria are in `implementation-backlog.md` §3.

---

## 8. Readiness checklist

| Item | Status |
|---|---|
| Research, PRD, design, architecture, evaluation and testing docs exist and are cross-referenced | ✅ VERIFIED |
| Mermaid diagrams parse | ✅ VERIFIED (7/7) |
| Benchmark schema validates the samples | ✅ VERIFIED (earlier in this session) |
| Approved product decisions recorded (D-001 to D-008) | ✅ |
| Consistency audit done; issues logged with owners | ✅ (24 issues) |
| PRD §10.1 validation gate | ❌ Not done (D-A) |
| AI-002 amendment | ❌ (D-B) |
| Domain and email deliverability decision | ❌ (D-C) |
| Trial-timing decision | ❌ (D-D) |
| NFR-011/014 restated; storage guard added | ❌ (D-E) |
| UD-01/03/05 approved | ❌ (D-F) |
| Supabase Free Mumbai + pgvector verified | ❌ (S-1) |
| Upload path verified | ❌ (S-2) |
| Git repository initialised | ❌ (T-001) |
| `.env.example` | ✅ created (placeholders only) |
| `AGENTS.md` | ✅ created |
| Engineering standards, setup guide, backlog | ✅ created |
| Docker daemon running | ❌ (start Docker Desktop) |
| pnpm available | ❌ (`corepack enable pnpm`) |
| Cloud CLIs (gcloud, Terraform, Supabase) | ⏳ Not needed until M9 |
| Legal reviewer, domain reviewer, native reviewers sourced | ❌ (D-H) |
| Annotation guide, wording fixture, seeds | ❌ (CI-17 tasks) |

---

## 9. Decisions applied on 15 October 2026 (product owner: "use the recommended defaults")

The product owner authorised development and approved the recommended answers in §4. They can be changed later.

| Decision | Applied default | Where it shows up |
|---|---|---|
| D-A | Build to a closed beta; the validation sprint runs in parallel; the kill criterion still applies before public launch | Development started (M0–M3) |
| D-B | Pending legal confirmation. Development uses **synthetic data only**, so no real document reaches any model. | `LLM_PROVIDER=fake` by default |
| D-C | A domain is needed before the beta (email deliverability, OAuth). Not needed for local development. | M9 |
| D-D | Local-first through M8; the GCP trial opens at M9; Gemini free tier with synthetic data only | `.env.example`, config guard (D-008) |
| D-E | Beta caps: 3 open cases per user; global storage guard at 95%; NFR-011/014 treated as scale-up targets | `MAX_OPEN_CASES=3`, `STORAGE_GUARD_PCT=95` |
| D-F | Gemini 2.5 Flash (Vertex, Mumbai), the ₹0 stack and custom authentication approved | system-design v1.1 |
| D-G | v0 PRD archived | `docs/archive/PRD-v0-2026-10-12.md` |
| D-H | Lawyer, domain reviewer and native reviewers to be sourced before M10 | Open |

**Implementation choices made during M0–M3** (recorded so the docs stay accurate):

- **Uploads go through the API** (the CI-04 default). No storage keys reach the browser. Direct TUS uploads remain the subject of spike S-2.
- **The frontend uses a small in-house i18n module (about 40 lines) instead of next-intl.** Reason: Next.js 16 enables Cache Components by default, and next-intl's compatibility with it was not confirmed. The routes follow Next's documented `app/[lang]` pattern plus `proxy.ts`.
- **TypeScript 5.x** is pinned, as chosen by `create-next-app@16.4.1`. This resolves CI-16.
- **The initial Alembic migration (0001) was generated from the models with SQLAlchemy's PostgreSQL DDL compiler.** Later migrations use `--autogenerate` against a live database.
- **Local and test knowledge are SYNTHETIC fixtures** (`eval/fixtures/knowledge`). RULE-MC-01 in prod stays `disabled_pending_verification` until the official IRDAI PDF is ingested and its quote verified.
- **In VS-1 a found clause is shown as "Couldn't assess yet", never "appears valid".** No AI counter-point analysis has run yet (it arrives in M5).
- **Local development without Docker** uses a native PostgreSQL (`infra/local/native-postgres-setup.sql`), because the Docker Desktop engine would not start on the developer machine. See development-setup §3a.
- **Google sign-in uses a small in-house OIDC client on `httpx` instead of Authlib.** The flow is the authorization code with PKCE, with state and nonce in a signed 10-minute cookie. `httpx` is already a dependency. Because the ID token comes straight from Google's token endpoint over TLS, the code checks its issuer, audience, expiry, nonce and `email_verified` but not its signature (OIDC Core §3.1.3.7). This keeps the dependency set small. system-design §1.1 and §3.3 still name Authlib; update them if this choice is accepted.
- **Admin console accounts store the email as a keyed hash plus an encrypted copy**, not as plain text (system-design §4.2 lists `admin_users.email text`). This follows the rule that emails are stored only in encrypted columns. Admin sessions share the `sessions` table (`kind='admin'`, `admin_user_id`), and a check constraint allows exactly one owner per session. TOTP (RFC 6238) is a small in-house module tested against the RFC vectors, so `pyotp` is not needed.
- **Database sessions use SQLAlchemy's default `autoflush=True`.** With autoflush off, rows added in the same transaction were invisible to later queries. That caused duplicate `job_steps` rows and an unset `insurer_name`, both found by the integration suite.

### 9.1 Open items found during the build (need a decision or follow-up)

| ID | Item | Proposed resolution | Owner |
|---|---|---|---|
| OI-01 | `pnpm audit --audit-level high` reports GHSA-vfj7-8cjw-p6xm in `braces` (no patched version). It is reached only through `eslint-config-next` → `@next/eslint-plugin-next` → `fast-glob` → `micromatch`, a **development-only** lint dependency that never sees user input. **The CI web audit step will fail** until this is resolved. | Product owner approves a time-boxed **waiver** (testing-strategy SEC-DEP-1): add `auditConfig.ignoreGhsas: [GHSA-vfj7-8cjw-p6xm]` to `pnpm-workspace.yaml` with a review date, and remove it when a patched release exists. Not applied without approval. | Product owner |
| OI-02 | The web CSP has no `script-src` yet. Blocking inline scripts in Next.js needs per-request nonces, which force dynamic rendering and conflict with Cache Components and partial prerendering. The current CSP sets `frame-ancestors`, `base-uri`, `form-action` and `object-src`; the API CSP is strict (`default-src 'none'`). | Decide before M9: nonce-based CSP (dynamic rendering) or hash-based CSP via Next's SRI support. Until then SEC-XSS-1's "CSP blocks inline script" check cannot pass. | Engineering |
| OI-03 | PDF export (WeasyPrint) cannot run on native Windows (no GTK/Pango). It runs in CI and in the API Docker image. | No change. Verify in the first CI run. | Engineering |
| OI-04 | FR-032 says the deleted account's email is kept as a one-way hash for 30 days to limit abuse. System-design defines no table for this, so it is **not implemented**. The existing per-email and per-IP sign-in rate limits still apply. | Add an `email_tombstones(email_hash, deleted_at)` table to system-design §4.2, plus a housekeeping purge after 30 days. | Product owner / architecture |
| OI-05 | FR-042 support access (reviewer can see a case for 7 days) has no admin side yet. The report dialog stores the user's "allow reviewer" choice in the review item only. | **Resolved** (commit 48774da): admins open case content only under the user's 7-day grant, and every attempt is audited. | Engineering |
| OI-06 | On 17 Oct 2026 the local PostgreSQL crashed with "out of memory" while the dev server, browser tests and another local app ran together, and the service stayed stopped. | Locally, stop the dev servers when not in use. CI is unaffected. | Developer |
