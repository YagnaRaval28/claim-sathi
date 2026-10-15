# ClaimSathi: Software Testing Strategy and Release Quality

| Field | Value |
|---|---|
| Version | 1.0 |
| Date | 15 October 2026 |
| Inputs | `competitor-research.md`, `PRD.md` v1.1, `design-system.md` v1.1, `system-design.md` v1.1 (₹0 MVP profile) |
| Companion | `docs/04-ai/evaluation-plan.md` (probabilistic AI quality) |
| Execution status | **No test in this document has been executed. The application has not been built.** Every expected result is a specification, not a measurement. |

## How to read this document

**Scope split.** This document covers **deterministic software correctness**: code that must behave the same way every time. That includes the parts of the AI pipeline that are deliberately non-AI:

- Rule 14 checks
- deadlines
- `NO_CLAUSE_CITED`
- the citation and number verifiers
- PII masking

**Model quality** (extraction accuracy, citation precision, translation adequacy) is measured statistically in the AI evaluation plan, not asserted here.

**Labels used throughout:**

| Label | Meaning |
|---|---|
| **PROVISIONAL** | A proposed target, not yet benchmarked |
| **T0** | Release-blocking test |
| **T1** | High priority |
| **T2** | Normal priority |

---

## 1. Testing scope

### 1.1 Test levels

| Level | What it proves | Tooling (per architecture) | Where it runs | Automated? |
|---|---|---|---|---|
| **Unit** | Pure logic: rules, deadline math, verifiers, masking, money and date utilities, validators, state machines | pytest; Vitest for web utilities | CI on every pull request | Yes |
| **Rule suites** | 100% of the deterministic rules in the rules table, with fixture tables (PRD NFR-017) | pytest, parametrised from YAML fixtures | CI | Yes (T0) |
| **Integration** | Services with a real Postgres (pgvector) database, MinIO (storage), ClamAV, and fake AI/OCR/email/Cloud Tasks adapters | pytest + docker compose services | CI | Yes |
| **API / contract** | Every endpoint in system-design §5: schemas, error codes, idempotency, rate limits, authorization | pytest + httpx against the app; schemathesis property tests from `openapi.json` | CI | Yes |
| **Authorization matrix** | Every case-scoped endpoint × {owner, other user, anonymous, admin, reviewer with grant, reviewer without grant} | Generated pytest matrix | CI | Yes (T0) |
| **End-to-end (E2E)** | Critical user journeys through the real UI and API, with fake AI and OCR adapters returning recorded fixtures | Playwright (Chromium + WebKit, mobile and desktop viewports) | CI (smoke subset), nightly (full) | Yes |
| **E2E with real providers** | The same journeys against staging with real Vertex, Document AI and SES, using **synthetic data only** | Playwright | Pre-release | Yes (manual trigger) |
| **Visual regression** | Layouts at 360, 768 and 1280 px in en, gu and hi, plus large-text mode (design DAC-08) | Playwright screenshots + reviewed baselines | Nightly | Semi (human approves baseline changes) |
| **Accessibility** | WCAG 2.2 AA: automated axe scans plus manual keyboard and screen-reader scripts | axe-core in Playwright; manual NVDA and TalkBack | CI (axe); before each release (manual) | Semi |
| **Security** | OWASP ASVS L2 controls (PRD NFR-006); see Section 4 | pytest security suite; OWASP ZAP; gitleaks; Trivy; pip-audit / osv-scanner; manual penetration test | CI + pre-release | Semi |
| **Performance** | NFR-001 to NFR-003, NFR-014, NFR-015 | k6 (HTTP), worker load harness, Lighthouse CI | Staging, pre-release | Yes (staging) |
| **Reliability / chaos** | Recovery from worker crash, provider outage and DB failover (NFR-010, NFR-011) | Fault-injection flags in the adapters; scripted kill of worker revisions | Staging | Semi |
| **Migration** | Alembic upgrade on an empty DB and on the previous release's schema; old app revision compatible with the new schema | pytest + Cloud Run Job dry run | CI + pre-deploy | Yes |
| **Localisation** | Translation key completeness; Indic rendering in UI, PDF and DOCX | CI script; visual fixtures; native reviewer | CI + pre-release | Semi |
| **User acceptance (UAT)** | Real target users complete the journeys | Moderated sessions | Closed beta | Manual |

### 1.2 Manual versus automated

| Must be automated (reproducible, deterministic) | Requires human review |
|---|---|
| Authorization matrix, rule suites, deadline math, verifiers, masking, API contracts, idempotency, rate limits, deletion and retention jobs, migrations, axe scans, translation-key completeness, dependency and secret scans | Screen-reader usability (NVDA, TalkBack), native-speaker review of Gujarati and Hindi copy and rendering, visual baseline approval, legal and disclaimer copy review, penetration test findings triage, UAT, human AI-quality rubrics (evaluation plan) |

### 1.3 Out of scope

This document does not test:

- PRD deferred items: the case-strength score, phone OTP, WhatsApp and SMS reminders, chat, the clinic workspace, payments, consumer-court drafting.
- Native apps.
- Insurer or Ombudsman portal behaviour. The app never files on the user's behalf.

P1 features (FR-002, FR-025, FR-041) have tests that are marked T2 and gated by feature flags.

### 1.4 Test environments and data

| Environment | Data | AI / OCR | Purpose |
|---|---|---|---|
| CI (ephemeral) | Synthetic fixtures only | `fake` adapters replaying recorded JSON; Tesseract for OCR adapter tests | Unit, integration, API, E2E smoke |
| Staging (Supabase Free project #2 + `staging`-tagged Cloud Run revisions) | Synthetic users and cases; consented research cases only in a restricted bucket | Real Vertex, Document AI and SES, **paid from trial credits, so runs are budgeted (§5.3)** | E2E-real, small-scale performance, security scans, evaluation |
| Prod | Real | Real | Post-deployment smoke tests only, using a dedicated synthetic **test account** flagged `is_test=true` and excluded from metrics |

**Test data rules:**

- **No real user data in CI, tickets, screenshots or logs.**
- Synthetic letters use the fictional insurer **"Sample Health Insurance Co. Ltd."** and the fictional product wording `SAMPLE-WORDING-001`, written by the team, so no real organisation is impersonated.
- The real public regulation texts (Master Circular, Ombudsman Rules) may be ingested as fixtures.

**Test doubles** (one per external dependency, selectable by environment variable):

| Double | Simulates |
|---|---|
| `FakeModelGateway` | Recorded responses, plus injectable faults: timeout, 429, 5xx, invalid JSON, wrong citation |
| `FakeOcrEngine` | Recorded OCR output |
| `FakeMailer` / Mailpit | Captures sign-in codes and reminder emails |
| `FakeTaskQueue` | Runs Cloud Tasks handlers in-process; can drop, duplicate or delay deliveries |
| `FakeMailer` | Mailpit in local and CI |
| `FakeMalwareScanner` | Real clamd in CI, plus a forced-error mode |
| `FakeObjectStore` | fake-gcs-server |

**Clock:** a fixed or injectable clock (`core.clock`) in IST for deadline tests.

---

## 2. Requirements traceability matrix

### 2.1 Conventions

**Test ID format:** `<TYPE>-<REQ>-<n>`.

| Type | Meaning |
|---|---|
| UT | unit |
| RS | rule suite |
| IT | integration |
| API | API / contract |
| AZ | authorization |
| E2E | end-to-end |
| VIS | visual regression |
| A11Y | accessibility |
| SEC | security |
| PERF | performance |
| REL | reliability |
| MIG | migration |
| L10N | localisation |
| MAN | manual |
| EVAL | AI evaluation (see the evaluation plan) |

**Automation values:**

| Value | Meaning |
|---|---|
| **A-CI** | Runs on every pull request |
| **A-NI** | Runs nightly |
| **A-STG** | Runs on staging before release |
| **SEMI** | Scripted, with human judgement |
| **MAN** | Manual |

**Priority** is the test priority (T0 to T2), not the requirement priority.

### 2.2 Functional requirements

| Req | Test IDs | Type | Preconditions | Steps (condensed) | Expected result | Pri | Auto |
|---|---|---|---|---|---|---|---|
| FR-001 Email-code sign-in | API-FR001-1..7, E2E-FR001-1 | API, E2E | FakeMailer | (1) Valid email → code → verify. (2) 6th request in an hour. (3) 5 wrong codes. (4) Expired code at 10:01. (5) Malformed email. (6) Existing email. (7) Unknown versus known email on request. | (1) Exactly one user and a session cookie (HttpOnly, Secure, SameSite=Lax). (2) 429 with Retry-After. (3) Code invalidated; correct code now fails. (4) 410 `email_code_expired`. (5) 422. (6) Signs in, no duplicate user. (7) Identical 204 response and timing within tolerance (no enumeration). | T0 | A-CI |
| FR-002 Google sign-in (P0) | API-FR002-1..4, E2E-FR002-1 | API, E2E | Mock OIDC provider | (1) New Google user. (2) Returning user. (3) Cancelled consent / bad `state`. (4) Google user whose email already signed in by code. (5) `email_verified=false`. | (1) User created with verified email. (2) Same user. (3) Redirect to sign-in, no session, no error page. (4) Same account (linking). (5) Rejected. | T0 | A-CI |
| FR-003 Sessions | API-FR003-1..4, E2E-FR003-1 | API, E2E | Two sessions for one user | (1) Logout, then reuse cookie. (2) Logout-all, then other session calls `/me`. (3) Idle expiry (24 h / 30 d trusted) with clock. (4) Absolute expiry. (E2E) Back button after logout. | (1, 2) 401 immediately (≤60 s requirement exceeded: immediate). (3, 4) 401 after expiry. (E2E) No case data rendered. | T0 | A-CI |
| FR-004 Language | E2E-FR004-1..3, L10N-FR004-1 | E2E, L10N | — | (1) Browser locale gu → first screen preselects gu. (2) Switch language mid-form. (3) Preference persists across sign-in. (L10N) Release build key check. | (1) gu selected. (2) Route prefix changes; entered data kept. (3) Redirect to stored language. (L10N) 0 missing gu/hi keys. | T1 | A-CI |
| FR-005 Consent | API-FR005-1..5, E2E-FR005-1 | API, E2E | Consent v1 published | (1) Create case without consent. (2) Consent stores the exact version. (3) Publish v2 (`requires_reconsent`) → next request. (4) Withdraw processing → enqueue analysis via API **and** run a pending job. (5) Reminders consent off → reminder due. | (1) 403 `consent_required`. (2) Row has version v1, purposes and language. (3) 403 until re-consent; UI shows the re-consent variant. (4) API 403, **and** the job aborts before any model call (no `ai_calls` row). (5) No email sent; in-app only. | T0 | A-CI |
| FR-006 Eligibility | API-FR006-1..5, E2E-FR006-1 | API, E2E | Consented user | Each branch: (1) health = no. (2) delayed. (3) group. (4) in litigation = yes. (5) Edit eligibility after first export. | (1) 422 `out_of_scope`; UI shows APP-03. (2) mode = `delay`. (3) Case created; caveat flag. (4) RULE-ESC-04 later blocks S3. (5) 409 (not editable). | T1 | A-CI |
| FR-007 Cases | API-FR007-1..3, AZ-FR007-1, IT-FR007-1 | API, AZ, IT | — | (1) List shows only the user's own cases. (2) 11th open case. (3) Two parallel creates when 9 cases are open. | (1) Only own cases. (2) 409 `open_case_limit`. (3) Exactly 10 succeed; 1 gets 409 (row lock). | T0 | A-CI |
| FR-008 Upload | API-FR008-1..9, E2E-FR008-1..2, SEC-FR008-* | API, E2E, SEC | Case exists | (1) PDF, JPG, PNG each. (2) 21 MB declared size. (3) 21 MB actual size with an understated declaration. (4) HEIC. (5) Same file twice. (6) 16th file, or a total above 50 MB, or above 60 pages. (7) Locked PDF + correct password. (8) Wrong password. (9) Analysis with no `decision_letter`. | (1) Accepted with type. (2) 413 before URL issue. (3) Rejected at upload (token size limit) or at `complete` (size check) with 422. (4) 415 with message. (5) 409 `duplicate_file`. (6) 409 `case_upload_limit`. (7) Processed; **password absent from DB rows, job args, logs and Sentry** (grep test). (8) 422 `pdf_password_incorrect`. (9) 409. | T0 | A-CI |
| FR-009 Resilient upload | E2E-FR009-1..2, IT-FR009-1 | E2E, IT | Playwright network throttling | (1) Drop the network mid-upload, then restore. (2) Close the tab after `queued`, then reopen. (IT) Worker restart during `reading`. | (1) Upload completes without user action (up to 3 retries). (2) Processed result shown. (IT) Job resumes; the document reaches `ready`. | T0 | A-NI |
| FR-010 OCR + extraction | IT-FR010-1..3, EVAL-A2 | IT, EVAL | Fake OCR/LLM fixtures | (1) Every extracted verbatim field maps to page and line IDs. (2) Amount absent from OCR text but present in fake model output. (3) Low OCR quality → status. | (1) `source_ref` present. (2) Field rejected (`not_found`) by the number scanner. (3) `needs_attention` with the retake reason. Accuracy is measured in EVAL-A2. | T0 | A-CI |
| FR-011 Confirm gate | API-FR011-1..4, E2E-FR011-1 | API, E2E | Extracted case | (1) POST analysis before confirmation. (2) Confirm with a required field missing. (3) Edit the decision date after analysis. (4) Original and edited values. | (1) 409 `fields_not_confirmed`. (2) 422 listing the fields. (3) Case stale; exports 409; deadlines recomputed. (4) Both retrievable. | T0 | A-CI |
| FR-012 Line items | API-FR012-1..4, UT-FR012-1 | API, UT | Partial case | (1) Mismatch above max(₹1, 1%). (2) Mismatch at exactly the threshold. (3) Deducted > billed. (4) Unitemised single line. | (1) Warning flag true. (2) false. (3) 422. (4) `unitemised=true`; audit `NO_CLAUSE_CITED`. | T1 | A-CI |
| FR-013 Classify | UT-FR013-1, API-FR013-1, EVAL-A4 | UT, API, EVAL | — | (1) Confidence below threshold. (2) User override. | (1) `other_unknown` + ask. (2) `category_source='user'` and override wins on re-run. Macro-F1 in EVAL-A4. | T1 | A-CI |
| FR-014 Wording | IT-FR014-1..4, AZ-FR014-1 | IT, AZ | Library wording + uploaded | (1) Uploaded wording preferred. (2) UIN match picks the version effective on the admission date. (3) No wording → limited mode. (4) Switch source → stale. (AZ) User B's uploaded wording never retrieved for user A. | (1) Source = uploaded. (2) Correct version row. (3) mode = `limited`; 0 policy citations. (4) Stale. (AZ) 0 rows. | T0 | A-CI |
| FR-015 Deduction audit | RS-FR015-1..6, UT-FR015-1 | RS, UT | Fixture case | (1) Empty, `none` or no-identifier clause text. (2) Cited clause not in wording. (3) Limited mode with a cited clause. (4) QUESTIONABLE without a verified citation. (5) Totals. | (1) `NO_CLAUSE_CITED` with 100% precision. (2) `CLAUSE_NOT_FOUND`. (3) `CANNOT_ASSESS` (never NOT_FOUND). (4) Impossible: falls back to APPEARS_VALID or CANNOT_ASSESS. (5) Sum per status equals the line sum. | T0 | A-CI |
| FR-016 Rejection analysis | RS-FR016-1..6, IT-FR016-1 | RS, IT | Fake model | Moratorium at 59, 60, 61 months and unknown inception; CRC on repudiation; Para 17(c) docs; RULE-MC-04 disabled. (IT) Fake model returns an invalid citation. | Fires at ≥60 months only; not at 59 or unknown. CRC request present for repudiation only. MC-04 never fires while disabled. (IT) Point dropped, `review_items` row created, not shown. | T0 | A-CI |
| FR-017 Explanation | UT-FR017-1..2, L10N-FR017-1, EVAL-A6 | UT, L10N, EVAL | — | (1) Number scanner on a fake output with a wrong amount. (2) Banned phrases. | (1) Sentence removed. (2) Removed and logged. Native review in L10N. | T0 | A-CI |
| FR-018 Checklist | UT-FR018-1, API-FR018-1 | UT, API | Evidence-map rules | (1) Category → items. (2) Mark obtained / upload. | (1) Every item traces to a map row. (2) Status persisted; enclosure list updated. | T2 | A-CI |
| FR-019 Abstention | IT-FR019-1..3, E2E-FR019-1 | IT, E2E | — | (1) No reasons extracted. (2) Empty retrieval. (3) Model `abstain=true`. | Each gives a distinct state with a recovery action, never an empty screen. Empty retrieval skips the LLM call (no `ai_calls` row). | T1 | A-CI |
| FR-020 Stage + Rule 14 | RS-FR020-1..12, API-FR020-1..3 | RS, API | Fixture rules | Pass and fail for each RULE-ESC-01..06. (API) Pack with a Block failing; Warn unacknowledged; skip S2. | Per the PRD table. 409 `rule_blocked` / `warnings_not_acknowledged`. S3 eligibility does not depend on S2. | T0 | A-CI |
| FR-021 Deadlines | RS-FR021-1..10 | RS | Injectable clock | 31 Jan + 1 month; 29 Feb + 1 year; 31 Mar + 1 month; IST midnight boundary; recompute on date edit; reminders rescheduled. | 28/29 Feb (last day rule); 28 Feb; 30 Apr; correct IST date; all dependants recomputed; old reminders cancelled. | T0 | A-CI |
| FR-022 Reminders | IT-FR022-1..5 | IT | FakeMailer | (1) Due reminder. (2) Two scheduler runs concurrently. (3) Email failure ×3. (4) Case closed. (5) Inspect body. | (1) Sent once. (2) Exactly one send (unique key + SKIP LOCKED). (3) In-app "Email failed". (4) Cancelled. (5) No diagnosis, hospital or amount fields. | T0 | A-CI |
| FR-023 Events | API-FR023-1..4 | API | — | (1) Future date. (2) Date before the decision. (3) `s1_sent` → deadline. (4) Insurer reply unsatisfied → new current decision. | (1, 2) 422. (3) RULE-ESC-02 clock starts. (4) Stale + prompt. | T1 | A-CI |
| FR-024 S1 letter | IT-FR024-1..4, EVAL-A7 | IT, EVAL | Analysis done | (1) Inspect the prompt payload sent to the fake gateway. (2) Every grounds paragraph. (3) Non-English letter. (4) APPEARS_VALID item default. | (1) **No confirmed identity value present** (masking). (2) ≥1 verified citation or a rule source. (3) English copy present; quotes in source language. (4) Unselected. | T0 | A-CI |
| FR-025 Bima Bharosa (P1) | API-FR025-1 | API | Flag on | Content reuses only verified grounds; char counts. | No unverified text; counts correct. | T2 | A-CI |
| FR-026 Ombudsman pack | API-FR026-1..3, E2E-FR026-1 | API, E2E | — | (1) Pack with a Block. (2) Grievance history dates. (3) Helper case. | (1) 409. (2) Equal to logged events. (3) Signatory = complainant. | T0 | A-CI |
| FR-027 Editor | E2E-FR027-1..3, API-FR027-1 | E2E, API | Letter ready | (1) Edit inside a protected quote. (2) Undo. (3) Autosave at 10 s / blur. (API) Tampered `doc` with an altered quote but the citation mark kept. | (1) Badge removed; warning. (2) Restored. (3) Saved. (API) Server marks the citation unverified (`broken_citation_ids`). | T0 | A-CI |
| FR-028 Export | IT-FR028-1..3, VIS-FR028-1, MAN-FR028-1 | IT, VIS, MAN | — | (1) Export while stale or unreviewed. (2) PDF and DOCX produced. (3) Footnotes. (VIS/MAN) Gujarati and Devanagari glyphs. | (1) 409. (2) Both files open (DOCX also opened in LibreOffice in CI). (3) Footnotes present. (VIS/MAN) No missing glyphs; native sign-off. | T0 | A-CI / MAN |
| FR-029 Source viewer | E2E-FR029-1 | E2E | — | Open every citation on the fixture case. | The highlighted span equals the quote. | T1 | A-CI |
| FR-030 Export data | IT-FR030-1 | IT | 15-file, 50 MB case | Request a ZIP. | Within 5 min; contains originals, JSON, letters, timeline, consents; link expires at 24 h. | T1 | A-NI |
| FR-031 Delete case | IT-FR031-1..3, E2E-FR031-1 | IT, E2E | Case with files | (1) Delete → purge job. (2) Delete during processing. (3) Audit row. | (1) No DB rows; no storage objects under the prefix. (2) Jobs cancelled; no orphans. (3) Content-free audit row. | T0 | A-CI |
| FR-032 Delete account | IT-FR032-1..2 | IT | — | (1) Delete, then sign in with the same number. (2) Phone hash retained for 30 days. | (1) Fresh empty account. (2) Hash removed after 30 days (clock). | T0 | A-CI |
| FR-033 Retention | IT-FR033-1..3 | IT | Clock | (1) Closed case at +90 d. (2) Extended once. (3) Inactive open case at 18 months, then +30 d. | (1) Files deleted. (2) Second extension rejected. (3) Notified, then deleted. | T0 | A-CI |
| FR-034 Outcome | API-FR034-1 | API | — | All optional; skip. | Stored or skipped. | T2 | A-CI |
| FR-035 Report | API-FR035-1..2 | API | — | (1) Report. (2) With grant. | (1) `review_items` row within 1 min, payload only. (2) Support grant created. | T1 | A-CI |
| FR-036 Settings | E2E-FR036-1 | E2E | — | Toggle each setting. | Persists and takes effect immediately. | T2 | A-CI |
| FR-037 Admin auth | API-FR037-1..4 | API | — | (1) Consumer cookie on admin route. (2) Non-allowlisted Google account. (3) No TOTP. (4) 6 wrong TOTPs. | (1) 401 (no route disclosure). (2) 403. (3) No session. (4) Locked. | T0 | A-CI |
| FR-038 Knowledge base | IT-FR038-1..4 | IT | Admin | (1) Publish without attestation. (2) Retire a version used by a letter. (3) Chunk without `clause_ref`. (4) Retired source in retrieval. | (1) 422. (2) Letter citations unchanged. (3) Flagged. (4) Excluded. | T0 | A-CI |
| FR-039 Rules admin | API-FR039-1..3 | API | Admin | (1) Enable without source or verifier. (2) New version. (3) Invalid `params`. | (1) 422 (and DB CHECK). (2) Old cases keep the old version. (3) 422 schema error. | T0 | A-CI |
| FR-040 Review queue | IT-FR040-1 | IT | — | Monthly sampler. | 100 random citations across languages. | T1 | A-CI |
| FR-041 Metrics (P1) | API-FR041-1 | API | Flag | Metrics endpoint. | Aggregates only; no case content fields. | T2 | A-CI |
| FR-042 Support access | AZ-FR042-1..3 | AZ | — | (1) Reviewer without grant. (2) With grant. (3) After 7 days or revoked. | (1) 403 + audit. (2) 200 + audit. (3) 403. | T0 | A-CI |
| FR-043 Public pages | A11Y-FR043-1, UT-FR043-1, E2E-FR043-1 | A11Y, UT, E2E | — | (1) Lighthouse a11y. (2) Accuracy page with no audit. (3) Content lint for statistics without a link. | (1) ≥95 (PROVISIONAL). (2) Empty state, no number. (3) 0 violations. | T1 | A-CI |
| FR-044 Free channels | E2E-FR044-1 | E2E | — | From each case screen, reach the notice. | ≤1 tap. | T2 | A-CI |

### 2.3 AI requirements (deterministic parts here; statistical parts in the evaluation plan)

| Req | Test IDs | Type | Steps (condensed) | Expected | Pri | Auto |
|---|---|---|---|---|---|---|
| AI-001 Where AI is used | UT-AI001-1 | UT | Static check: the modules for deadlines, rules, `NO_CLAUSE_CITED` and verifiers import no `ai` gateway | 0 imports | T1 | A-CI |
| AI-002 Masking | UT-AI002-1..4, IT-AI002-1 | UT, IT | Masker over fixtures with names, phone numbers, emails and Aadhaar/PAN-like numbers; all post-confirmation calls captured | No confirmed identity value appears in any captured payload. Extraction-call exception per UD-02 is asserted explicitly. | T0 | A-CI |
| AI-003 Structured output | IT-AI003-1..2 | IT | Fake returns invalid JSON once, then valid; invalid twice | Repair retry succeeds; second failure → step failed → FR-019 state | T0 | A-CI |
| AI-004 Citation verifier | UT-AI004-1..10 | UT | Exact match; whitespace and quote variants; case (Latin vs Indic); ID not in the retrieved set; quote of 7 words; paraphrase; Unicode NFC/NFD | Pass and fail exactly per spec; 100% on the table | T0 | A-CI |
| AI-005 Number scanner | UT-AI005-1..8 | UT | Latin, Gujarati (૧૨,૦૦૦) and Devanagari digits; dates; percentages; clause IDs; numbers present in a cited chunk | Ungrounded token → sentence removed; grounded kept | T0 | A-CI |
| AI-006 Thresholds | UT-AI006-1 | UT | Values just below and above each threshold | Correct flag or state; no numeric confidence in any API response (schema test) | T1 | A-CI |
| AI-007 Human approval | API-AI007-1..3 | API | Export unreviewed version; review v1, edit to v2, export | 409 `letter_not_reviewed` until v2 reviewed | T0 | A-CI |
| AI-008 Fallbacks | REL-AI008-1..5 | REL | Fake timeout, 5xx, circuit open, all citations fail, translation fails | Retry schedule; `retrying` state; deterministic grounds letter; English + warning; never partial translation | T0 | A-CI |
| AI-009 Translation | UT-AI009-1, EVAL-A8 | UT, EVAL | Quote placeholders altered by fake translation | Fail closed → English shown | T0 | A-CI |
| AI-010 Injection | IT-AI010-1, EVAL-ADV | IT, EVAL | Fixture document containing instructions | Instructions not followed (evaluation); detector count logged; no content logged | T0 | A-CI / A-STG |
| AI-011 Versioning | IT-AI011-1 | IT | Run analysis | Model, prompt, source and rule versions stored | T1 | A-CI |
| AI-012 / AI-013 Evaluation | EVAL-* | EVAL | See the evaluation plan | Thresholds met | T0 | A-STG |
| AI-014 No training | MAN-AI014-1 | MAN | Contract and console settings review | Evidence filed | T0 | MAN |
| AI-015 Provider terms | MAN-AI015-1 | MAN | DPA signed; abuse-logging exception; caching disabled | Evidence filed | T0 | MAN |

### 2.4 Non-functional requirements

| Req | Test IDs | Type | Method | Expected (PROVISIONAL unless noted) | Pri | Auto |
|---|---|---|---|---|---|---|
| NFR-001 OCR + extraction | PERF-NFR001-1 | PERF | 30 runs of a 20-page synthetic case on staging (real Document AI and Vertex); timing from `job_steps` | p90 ≤ 90 s | T1 | A-STG |
| NFR-002 Analysis / letter | PERF-NFR002-1..2 | PERF | 30 runs each | Analysis p90 ≤ 60 s; letter p90 ≤ 45 s | T1 | A-STG |
| NFR-003 Front-end speed | PERF-NFR003-1..2 | PERF | Lighthouse CI (mobile, Slow 4G) on PUB-01, APP-01, CASE-04; INP from Playwright traces | LCP ≤ 3.0 s; non-AI interaction ≤ 200 ms | T1 | A-NI |
| NFR-004 TLS | SEC-NFR004-1 | SEC | testssl.sh against staging and prod; header check | TLS ≥1.2; HSTS; no mixed content | T0 | A-STG |
| NFR-005 Encryption | IT-NFR005-1..3 | IT | Raw DB read of encrypted columns; signed URL expiry; key rotation job | Ciphertext only; URL dead after 15 min; re-encrypted rows decrypt | T0 | A-CI |
| NFR-006 ASVS L2 | SEC-* (Section 4), MAN-NFR006-1 | SEC | Suite plus external penetration test | 0 open high or critical findings | T0 | SEMI |
| NFR-007 Backups | REL-NFR007-1..2 | REL | (1) Restore the latest encrypted nightly dump into a fresh Supabase project (or local Postgres) and run the app smoke test. (2) Verify the dump job ran, the rolling 7 copies exist, and the weekly offline copy is decryptable. | (1) Restore within RTO 8 h; data at the dump point. (2) Pass. | T0 | MAN (pre-beta, then quarterly) |
| NFR-008 DPDP | MAN-NFR008-1, IT-FR030/031/032 | MAN, IT | Legal checklist; rights flows tested | Lawyer sign-off; flows pass | T0 | MAN |
| NFR-009 Residency | MAN-NFR009-1, UT-NFR009-1 | MAN, UT | Terraform plan review (all regions asia-south1 / ap-south-1); config test asserting region values | All data stores in India | T0 | A-CI + MAN |
| NFR-010 No lost uploads | REL-NFR010-1..2 | REL | Kill worker mid-job; simulate a 1 h provider outage | All jobs complete or show a recoverable state; 0 lost | T0 | A-STG |
| NFR-011 Availability | REL-NFR011-1 | REL | Uptime checks (prod) | 99.5% monthly (measured after launch) | T1 | Monitoring |
| NFR-012 WCAG 2.2 AA | A11Y-* (Section 3.10) | A11Y | axe + manual scripts | 0 serious or critical; manual scripts pass | T0 | SEMI |
| NFR-013 Readability | MAN-NFR013-1 | MAN | Grade-level tool on English; native-reviewer register check | English ≈ Grade 8 or below | T2 | SEMI |
| NFR-014 Scale | PERF-NFR014-1 | PERF | Section 5 scenario L2 | No degradation of NFR-001/002 | T1 | A-STG |
| NFR-015 Fairness | PERF-NFR015-1 | PERF | One user floods 20 analyses while others submit | Others' p90 within NFR-002 | T1 | A-STG |
| NFR-016 Versioned prompts | UT-NFR016-1 | UT | CI asserts every prompt and schema file has a version and a changelog entry | Pass | T2 | A-CI |
| NFR-017 Coverage | CI gate | — | Coverage report | Rule suites 100%; back end ≥ 70% lines | T0 | A-CI |
| NFR-018 No hard-coded copy | UT-NFR018-1 | UT | ESLint rule for JSX string literals | 0 violations | T1 | A-CI |
| NFR-019 Log hygiene | UT-NFR019-1, IT-NFR019-1 | UT, IT | Logging allowlist test; run E2E and grep the captured logs and Sentry payloads for fixture PII and OCR text | 0 hits | T0 | A-CI |
| NFR-020 Alerts | REL-NFR020-1 | REL | Trigger each alert condition on staging | Alert delivered | T1 | A-STG |
| NFR-021 L10N quality | L10N-NFR021-1, MAN-NFR021-1 | L10N, MAN | Key completeness in CI; native sign-off | 0 missing; sign-off recorded | T0 | A-CI + MAN |
| NFR-022 Cost per case | PERF-NFR022-1, IT-NFR022-1 | PERF, IT | (PERF) 30 real-provider runs within the §5.3 credit budget; sum `ai_calls` cost + paid OCR. (IT) Hosting stays within free tiers: quota-snapshot job reports DB MB, storage MB, Document AI pages and registry MB. | Report the per-case distribution (ESTIMATE about ₹10 on Gemini 2.5 Flash; ≤ ₹40 PROVISIONAL). Every free-tier quota below 80%. | T1 | A-STG |
| NFR-023 Budget cap | IT-NFR023-1 | IT | Set the cap low; reach 80% | New analyses queue; admin alerted | T1 | A-CI |
| NFR-024 Disclaimer | E2E-NFR024-1 | E2E | Check CASE-04, CASE-06, CASE-10 and exports | Present on all | T0 | A-CI |
| NFR-025 Browsers | E2E-NFR025-1 | E2E | Playwright Chromium, WebKit and Firefox; Android Chrome via BrowserStack (or a real device) | Critical journeys pass | T1 | A-NI |
| NFR-026 Stack | — | — | Architecture conformance review | Matches ADRs | T2 | MAN |

### 2.5 Design acceptance criteria (design-system §10)

| DAC | Test IDs | Auto |
|---|---|---|
| DAC-01 Tokens | Stylelint/ESLint token rule (CI) | A-CI |
| DAC-02 / DAC-03 Contrast and axe | A11Y-DAC02-1 (token-pair contrast script), A11Y-DAC03-1 (axe on every route × 3 languages × default and error states) | A-CI |
| DAC-04 / DAC-05 Keyboard and screen readers | MAN-A11Y-KB-1, MAN-A11Y-SR-1..2 (Section 3.10) | MAN |
| DAC-06 / DAC-07 Reflow and targets | A11Y-DAC06-1 (320 px and 200% zoom screenshots), A11Y-DAC07-1 (target-size script) | A-NI |
| DAC-08 Responsive | VIS-DAC08-* (pages × 3 viewports × 3 languages) | SEMI |
| DAC-09 State completeness | VIS-DAC09-1: Storybook fixture per listed state; CI counts against the state inventory | A-CI |
| DAC-10 / DAC-11 AI honesty and provenance | UT-DAC10-1 (no `%` adjacent to confidence in UI strings; no numeric confidence in API schemas); E2E-DAC11-1 (DOM check: every counter-point, quote and fact has a ProvenanceTag or CitationTab) | A-CI |
| DAC-12 Reduced motion | E2E-DAC12-1 (emulate `prefers-reduced-motion`; computed styles) | A-CI |
| DAC-13 Performance | PERF-NFR003-1 | A-NI |
| DAC-14 Indic rendering | VIS-FR028-1 + MAN native sign-off | SEMI |
| DAC-15 Destructive safety | E2E-DAC15-1 (typed-code dialogs; Escape disabled while busy) | A-CI |
| DAC-16 / DAC-17 Traceability and consistency | MAN review at design QA | MAN |

---

## 3. Core test scenarios

These complement the per-requirement tests and are the source of most E2E and integration cases.

### 3.1 Successful journeys (E2E, recorded fixtures; repeated with real providers on staging)

| ID | Journey (PRD / design) | Key assertions |
|---|---|---|
| SCN-J1 | J1/F1: partial disallowance in Gujarati, through to S1 export and logged send | Facts confirmed; audit statuses as in the fixture; Gujarati letter with English copy; deadlines shown; `s1_sent` recorded |
| SCN-J2 | J2/F2: repudiation for non-disclosure; moratorium fires; S1 → one month → S3 pack | Moratorium point (rule provenance); Block before one month; pack after; signatory |
| SCN-J3 | J3/F3: no wording → limited mode → upload wording → stale → update | Limited callout; stale banner; full findings after the update |
| SCN-J11 | J11: helper for a parent | Signatory notice on S3; letters name the complainant |
| SCN-J12 | J12: insurer partial reversal | New current decision; reduced disputed amount carried into S3 |

### 3.2 Invalid inputs and validation

- **Schema-driven testing:** schemathesis generates invalid bodies for every endpoint. The expected result is 422, **never 500**.
- **Boundary tables:**
  - email (missing @, 255 characters, Unicode domain, leading or trailing spaces, uppercase);
  - sign-in code (5 and 7 digits, letters);
  - dates (31/02, year 1900, future, before the decision);
  - amounts (negative, above ₹50 lakh, non-numeric, paise rounding);
  - verbatim fields (4,000 and 4,001 characters);
  - comment (1,000 and 1,001 characters);
  - nickname containing emoji and Gujarati;
  - file names containing path traversal (`../`) and Unicode.

### 3.3 Authentication and authorization

- **AZ matrix (T0):** generated from the OpenAPI document. For every path with `{id}`, `{doc_id}`, `{letter_id}` or `{chunk_id}`:

  | Caller | Expected |
  |---|---|
  | Owner | 2xx |
  | Other user | **404** (body identical to a truly missing resource) |
  | Anonymous | 401 |
  | Admin session on a consumer route | 401 |
  | Reviewer without grant on `case-content` | 403 |
  | Reviewer with grant | 200 + audit row |

- **Mass assignment:** PATCH with `user_id`, `status` or `stage` in the body is rejected by `extra=forbid` (422).
- **Signed-URL reuse:** another user using an owner's signed URL or upload token after expiry → rejected by storage; an upload token used for a different object path → rejected.

### 3.4 Data persistence and ownership

- **Round-trips:** facts, line items, letters and events survive a restart. Encrypted columns decrypt correctly.
- **Optimistic concurrency:** two tabs editing facts or a letter → the second save gets 409 `version_conflict`. The UI offers a reload, and no edits are silently lost (E2E).
- **Reproducibility:** retiring a knowledge source or rule version does not change existing analyses or letters.

### 3.5 File uploads and processing

See FR-008, FR-009 and SEC-UP-* (Section 4). Also:

- a photo group of 5 pages;
- auto-rotation of a sideways photo;
- the 15-file, 50 MB and 60-page caps across files;
- a corrupt PDF;
- a zero-byte file;
- an image of 20,000 × 20,000 px (decompression bomb, blocked by the Pillow pixel limit);
- a scanned PDF without a text layer;
- a mixed-language page.

### 3.6 External API failures, timeouts and retries (fault injection in the fakes)

| Dependency | Faults injected | Expected |
|---|---|---|
| Vertex | Timeout, 429, 500, invalid JSON, slow (90 s) | Retry schedule; circuit breaker after 5 failures; `retrying` step; final failed state + basic letter offer |
| Document AI | 5xx, timeout, low-quality result | Retries; `needs_attention` |
| Supabase Storage | 5xx on write | Task retry; no partial DB state |
| Google OAuth | Error or timeout on callback | Back to sign-in with a message; email-code option offered |
| Cloud Tasks | Dispatch failure; duplicate delivery; delivery after a long delay | Outbox re-dispatches within the 5-minute tick; duplicates are skipped by `job_steps`; delayed steps still complete |
| SES | Throttle, 5xx, sandbox recipient refused | Code email: error with "Continue with Google". Reminder: retried 3 times over 6 h, then in-app fallback. |
| ClamAV | Connection refused | Document **failed** (fail closed), never `ready` |
| Supabase Postgres (pooler) | Connection drop mid-transaction; project paused | Transaction rolled back; task retried; no half-written analysis. Paused project: DB-unreachable alert fires (R-18). |

### 3.7 Duplicate requests

- Same `Idempotency-Key` + same body on POST analyses, letters, exports, events, cases, reports → identical response; **one** resource and **one** job.
- Same key + different body → 409.
- Double-click on the Create letter button (E2E) → one letter.
- Duplicate scheduler ticks → one reminder (FR-022).
- Duplicate Cloud Tasks deliveries of the same step → the step runs once (`job_steps` skip).

### 3.8 Concurrent actions

| Situation | Expected |
|---|---|
| Two simultaneous case creations at the limit | One 409 (FR-007) |
| Facts edited while an analysis is running | Analysis completes but is marked stale; the new run supersedes it |
| Case deleted while a job is mid-step | Job aborts at the next consent/case check; no orphan objects (housekeeping sweep test) |
| Letter autosave racing an export | Export uses the reviewed version, or 409 |
| Support grant revoked during a reviewer session | Next request 403 |

### 3.9 Empty and loading states, mobile and responsive

- **Storybook state fixtures** for every state listed in design §4 (DAC-09).
- **E2E with delayed fakes** verifies:
  - skeletons;
  - ProcessingSteps showing **real** step names and attempt counts;
  - the "you can leave this page" note after 20 s;
  - no percentage bar without a ratio.
- **Responsive:** Playwright projects Pixel 5 (393 px), iPhone SE (375 px), 320 px reflow, tablet (768 px) and desktop (1280 px).
  - Mobile uses bottom sheets, the sticky action bar and LineItemCards.
  - Desktop uses the rail, SourcePanel column and LedgerTable (design §9.5).

### 3.10 Accessibility (manual scripts, before each release)

| Script | Steps | Pass |
|---|---|---|
| MAN-A11Y-KB-1 | Complete SCN-J1 keyboard-only on desktop Chrome | Done without a mouse; focus always visible and never obscured by sticky bars |
| MAN-A11Y-SR-1 | NVDA + Chrome: SCN-J1 in English and Hindi | All controls named; processing announced at most once per 10 s; errors announced; language switching pronounced |
| MAN-A11Y-SR-2 | TalkBack + Android Chrome: read CASE-04 and CASE-06 in Gujarati | Provenance tags read; citations operable |
| MAN-A11Y-ZOOM-1 | 200% text, large-text mode, 320 px | No loss of content or function |

### 3.11 Account deletion and data retention

- FR-031, FR-032 and FR-033 tests.
- After deletion, a scan for the user's identifiers across all tables, storage and logs (synthetic fixture identifiers) returns 0, except the 30-day email hash.
- Backup expiry (35 days) is verified by configuration review, not by test.

### 3.12 Recovery after partial failure

| Failure point | Expected |
|---|---|
| Worker killed after the OCR step | Resume at extraction |
| API crash after upload but before `complete` | Upload re-completable; orphan `uploads` objects deleted by the 24-hour housekeeping |
| API crash after commit but before the Cloud Task is created | The outbox row is dispatched by the next 5-minute tick |
| DB restore from backup | Housekeeping sweeps orphaned storage prefixes |
| Export job crash | Re-run produces the same key; no duplicate files |

---

## 4. Security testing

| ID | Area | Test | Expected | Auto |
|---|---|---|---|---|
| SEC-AZ-1 | Unauthorized access | Every protected route without a session | 401 | A-CI |
| SEC-AZ-2 | Broken object-level authorization (BOLA) | AZ matrix (Section 3.3), including IDs in query and body fields (`document_id`, `case_id` in reports, `chunk_id` in sources) | 404; no data | A-CI (T0) |
| SEC-AZ-3 | Cross-user leakage | Seed users A and B with similar data. Run every list and search endpoint as A, and retrieval for A's case. | No B identifiers appear anywhere (string search on responses) | A-CI (T0) |
| SEC-AZ-4 | Admin separation | Consumer → admin APIs; reviewer → admin-only APIs | 401 / 403 | A-CI |
| SEC-INJ-1 | SQL injection | SQL metacharacters in all string fields and query parameters (schemathesis + payload list); ZAP active scan on staging | No 500; no behaviour change; parameterised SQL only (ruff/bandit rule against f-string SQL) | A-CI + A-STG |
| SEC-INJ-2 | Template / format injection | `{{7*7}}`, `${…}` in nickname, reasons and letter text → export | Rendered literally | A-CI |
| SEC-XSS-1 | Stored XSS | `<script>`, `<img onerror>`, `javascript:` URLs in every user text field and in TipTap JSON (forbidden nodes, `href`) | Escaped in UI; TipTap sanitiser strips them; CSP blocks inline script (report-only violations = 0) | A-CI |
| SEC-XSS-2 | Model-output XSS | Fake model returns HTML/JS in statements | Rendered as text | A-CI |
| SEC-CSRF-1 | CSRF | Unsafe method without or with a wrong `X-CSRF-Token`; cross-origin `Origin` | 403 | A-CI |
| SEC-SESS-1 | Cookie flags and fixation | Inspect Set-Cookie; reuse a pre-login cookie | HttpOnly, Secure, SameSite=Lax; new token on login | A-CI |
| SEC-RL-1..6 | Rate limits | Each limit in system-design §5.5, at the limit and one over | 429 + Retry-After exactly at the limit + 1 | A-CI |
| SEC-RL-7 | Email-code abuse | Many distinct emails from one IP; the global daily cap | Limited per IP; cap enforced; responses do not enumerate accounts | A-CI |
| SEC-SUPA-1 | Supabase exposure | Call the project's REST (PostgREST) and Storage endpoints with the anon key; search the client bundle for Supabase keys | Data API disabled or RLS deny-all returns nothing; buckets private; 0 keys in the bundle | A-STG (T0) |
| SEC-TASK-1 | Forged worker calls | Call `/tasks/*` and `/ticks/*` without an OIDC token, or with a token for the wrong audience or service account | 401/403; no side effects | A-STG (T0) |
| SEC-UP-1 | Malicious upload | EICAR test file (as PDF, JPG and inside a PDF attachment) | `rejected`; object deleted; never parsed | A-CI |
| SEC-UP-2 | Type spoofing | PNG bytes declared as PDF; HTML or SVG renamed to .jpg | Rejected with 415 by the magic-byte check at upload `complete` (added to system-design §5.2 during test design) | A-CI |
| SEC-UP-3 | Parser abuse | Decompression-bomb image; PDF with JavaScript or launch actions; deeply nested PDF; encrypted PDF with an empty password | Rejected or processed safely within the timeout; no JavaScript executed (pypdfium2 does not execute JS) | A-CI |
| SEC-UP-4 | Size bypass | Upload beyond the token's size limit; reuse a token for a second object | Rejected by storage; `complete` 422 | A-STG |
| SEC-SECRET-1 | Secret exposure | gitleaks on the repository; Trivy secret scan on images; grep the Next.js client bundle for env names and keys | 0 findings | A-CI |
| SEC-DEP-1 | Dependencies | pip-audit / osv-scanner (Python, npm); Trivy OS packages | No known high or critical vulnerabilities without a waiver | A-CI |
| SEC-ERR-1 | Unsafe error messages | Force 500s and validation errors | Problem+json without stack traces, SQL or file paths; same body for missing and not-owned resources | A-CI |
| SEC-HDR-1 | Security headers | Check CSP, HSTS, X-Content-Type-Options, Referrer-Policy, frame-ancestors | Present and correct | A-CI |
| SEC-PII-1 | PII to the model | Capture all gateway payloads in E2E | No confirmed identity values (except the extraction call, per UD-02) | A-CI (T0) |
| SEC-PII-2 | PII in logs and telemetry | NFR-019 test | 0 hits | A-CI (T0) |
| SEC-OTP-1 | Sign-in code brute force | 5 attempts per challenge; timing-safe compare (code review) | Locked after 5 | A-CI |
| SEC-ADM-1 | Admin MFA brute force | 6 wrong TOTPs | Lockout | A-CI |
| SEC-PEN-1 | External penetration test | Third-party test against staging (scope: web, API, upload, auth, admin) | 0 open high or critical findings at release | MAN |

---

## 5. Performance and reliability

All targets are **PROVISIONAL**, from PRD NFR-001 to NFR-003, NFR-014 and NFR-015.

**Measurement locations:**

- `job_steps` timestamps for pipeline latency;
- k6 summaries for HTTP;
- Cloud Monitoring for CPU, memory and DB metrics;
- Lighthouse for front-end metrics.

Load tests run on staging, which shares the production Cloud Run free tier and uses the second Supabase Free project. **Under the ₹0 constraint, load tests use fake AI and OCR adapters by default, and real-provider runs are capped by the credit budget in §5.3.**

### 5.1 Load model

The PRD capacity of 2,000 cases a month gives about 70 a day. Assume 20% of daily traffic falls in the peak hour and a burst factor of 5. That gives **about 15 new cases per peak hour** and about 50 concurrent processing jobs (NFR-014).

### 5.2 Scenarios

| ID | Scenario | Provider mode | Target |
|---|---|---|---|
| PERF-L1 | **API baseline:** 50 virtual users browsing (case list, facts, findings, progress polling every 3 s) for 15 min | Fakes | p95 API latency ≤ 300 ms for non-AI GETs; error rate < 0.5% |
| PERF-L2 | **Pipeline throughput:** 50 cases submitted in 10 min (10-page synthetic each) | Fake model and fake OCR with realistic latency distributions recorded from staging; real Document AI on 3 cases only | All complete; p90 per step within NFR-001/002; Cloud Tasks concurrency respected; DB connections < 80% of the Free pooler limit |
| PERF-L3 | **Real-provider latency:** 30 sequential cases | Real Vertex + Document AI | Measure p50 and p90 for NFR-001/002; cost per case (NFR-022) |
| PERF-L4 | **Noisy neighbour:** one user submits 20 analyses while 10 users submit 1 each | Fakes | Others' p90 ≤ NFR-002 (per-user queue limits) |
| PERF-L5 | **Soak:** PERF-L1 at 30% for 4 h | Fakes | No memory growth > 10%; no connection leaks |
| PERF-L6 | **Front end:** Lighthouse mobile, Slow 4G, mid-tier device; warm and cold runs | — | Warm LCP ≤ 3.0 s; JavaScript budget per design §9.7. **Cold-start LCP is measured and reported, with no target in the MVP** (NFR-003). |
| PERF-L7 | **Upload:** 10 concurrent 5 MB uploads, deleted afterwards | Real Supabase Storage (staging) | All complete; API CPU unaffected (direct-to-storage); storage returns below 80% after cleanup |

**Resource targets:**

- API memory < 512 MiB per instance;
- worker memory < 2 GiB per instance;
- Supabase Free DB: no connection exhaustion during L2;
- Cloud Run usage for the whole test run stays inside the monthly free tier (check the billing report).

These are PROVISIONAL and will be revised after the first run.

### 5.3 Credit budget for real-provider tests (₹0 constraint)

Real-provider runs spend the trial credit (system-design §1.4). The PROVISIONAL allocation for all testing and evaluation is **≤ US$100**:

| Activity | Budget | Notes |
|---|---|---|
| PERF-L3 real-provider latency (30 cases) | ≤ US$15 | Gemini 2.5 Flash ESTIMATE ≈ $0.12 per case |
| E2E-real pre-release runs | ≤ US$10 | Synthetic cases only |
| AI evaluation and bake-off | ≤ US$75 | Evaluation plan §15.4 |

Spend is read from `ai_calls` after each run. **A run stops when its budget is reached**, and its partial result is reported as partial.

### 5.4 Reliability tests

| ID | Fault | Expected |
|---|---|---|
| REL-1 | Kill a worker revision mid-L2 | All jobs complete after restart (NFR-010) |
| REL-2 | Fake Vertex outage for 30 min, then recovery | Jobs show `retrying`, then complete; no lost work; degraded banner appears after 15 min |
| REL-3 | Supabase project restart, or a paused project restored | API returns 503 briefly; no corruption; tasks retry and resume |
| REL-6 | Credit guard | Set `CREDIT_BUDGET_USD` low on staging and run analyses past 90% | New analyses return 503 `ai_paused_budget`; rules, deadlines and the basic letter still work; admin alerted |
| REL-7 | Free-tier quota alert | Fill staging storage past 80% | Quota alert fires within one daily run |
| REL-4 | Restore drill (NFR-007) | RTO ≤ 8 h, timed |
| REL-5 | Alert drills (NFR-020) | Each alert fires within 5 min of its condition |

---

## 6. CI/CD quality gates

### 6.1 Merge gate (pull request)

**All checks are required:**

1. Lint and format: ruff, black, eslint, prettier, stylelint + the design token rule (DAC-01).
2. Type checks: mypy (strict for `rules`, `verify`, `ai`, `security`), `tsc --noEmit`.
3. Unit tests + **rule suites at 100%** (NFR-017).
4. Integration and API tests (Postgres + fakes).
5. **Authorization matrix** (T0).
6. Coverage: back end ≥ 70% lines; `rules`, `verify`, `ai/masking` and `security` ≥ 95% branches (PROVISIONAL).
7. OpenAPI diff, which must be acknowledged in the pull request if changed. Generated TypeScript types must be up to date.
8. **Migration validation:**
   - `alembic upgrade head` on an empty DB;
   - upgrade from the previous release's schema with synthetic data;
   - `alembic check` (models equal migrations);
   - the destructive-change linter (DROP/ALTER TYPE requires an `expand-contract` label).
9. Translation-key completeness (NFR-021).
10. Security: gitleaks, bandit, pip-audit / osv-scanner, npm audit (high and critical block), Trivy image scan.
11. E2E smoke (Playwright, fakes): SCN-J1 and SCN-J2 on mobile and desktop.
12. axe scan on fixture pages (DAC-03).
13. Prompt and schema version check (NFR-016). **Any change under `ai/prompts/`, retrieval or knowledge-base code requires the `eval-required` label**, which blocks deployment to production until the evaluation gate passes.

### 6.2 Deploy gate to staging (automatic on `main`)

- Image build.
- Migration Cloud Run Job (must succeed).
- Deploy.
- Post-deploy smoke tests (Section 7.5).
- Nightly suites (full E2E, visual, Lighthouse).

### 6.3 Deploy gate to production (tag + manual approval)

1. All staging gates green on the same commit.
2. **AI evaluation gate:** if `eval-required` changes are included since the last production release, the benchmark run on staging meets the release thresholds and does not regress beyond tolerance (evaluation plan §13 and §15).
3. **Backward compatibility:** the *previous* API revision's smoke suite runs against the *new* schema, so a rollback is safe.
4. No open S1 or S2 defects (Section 7.2).
5. The release checklist (Section 7.1) is signed off for major releases.

---

## 7. Release readiness

### 7.1 Go / no-go checklist (MVP closed beta)

Derived from PRD §10.2, design §10 and architecture §C.9. **Every item needs evidence linked in the release ticket.**

**Product and validation**

- [ ] PRD §10.1 pre-build gate passed (teardown, interviews, legal, spikes). Evidence: discovery notes.
- [ ] Product-owner decisions UD-01 to UD-05 recorded.

**Functional**

- [ ] All T0 tests in Section 2 automated and passing on the release commit.
- [ ] All P0 functional requirements have passing acceptance tests.
- [ ] SCN-J1, J2, J3, J11 and J12 pass E2E with fakes **and** with real providers on staging.

**AI** (evaluation plan)

- [ ] Benchmark vX run on the held-out test split with real providers. Report attached.
- [ ] All **release blockers** = 0 (evaluation plan §15.1).
- [ ] All PROVISIONAL thresholds met, or the product owner has approved a documented exception.
- [ ] Baseline comparison documented (evaluation plan §13.4).

**Security and privacy**

- [ ] Penetration test complete; 0 open high or critical findings.
- [ ] AZ matrix, BOLA and PII tests passing.
- [ ] DPA with the AI provider signed; Vertex abuse-logging exception granted; caching disabled.
- [ ] Lawyer review of the privacy notice, consent, disclaimers, retention and breach runbook.
- [ ] Secrets in Secret Manager; no long-lived CI keys.

**Accessibility and localisation**

- [ ] axe: 0 serious or critical; manual keyboard and screen-reader scripts passed.
- [ ] Native-speaker sign-off (gu, hi) on templates, UI copy, and PDF/DOCX rendering.

**Operations**

- [ ] Restore drill done (RTO measured).
- [ ] Alerts firing in drills; on-call contact defined (the solo developer, plus a backup contact).
- [ ] Budget alerts and cap configured.
- [ ] SES out of sandbox; code-email delivery tested to Gmail, Outlook and Yahoo; Sentry EU region with a scrubbing test.
- [ ] **₹0 checks:** Supabase projects confirmed in Mumbai (UD-12); Data API disabled; free-tier quota snapshot under 80%; credit guard tested (REL-6); trial start date, day-75 decision date and day-90 close date recorded in the release ticket; SES 6-month free-plan end date recorded.
- [ ] Performance PERF-L1 to L3 and L6 run; results recorded against the PROVISIONAL targets.

**Go-live decision:** product owner + developer.

**No-go if:** any T0 failure, any AI release blocker > 0, any open S1/S2 defect, or any missing legal sign-off.

### 7.2 Severity definitions

| Severity | Definition | Examples | Release impact | Fix target |
|---|---|---|---|---|
| **S1 Critical** | Harm to the user's case, privacy breach, security hole, or data loss | Unverified quote shown as verified; wrong deadline; cross-user data visible; PII in logs or Sentry; deletion fails; letter amount differs from confirmed facts | **Blocks release; production hotfix or rollback immediately** | Same day |
| **S2 Major** | A core journey is broken or misleading, with no workaround | Cannot export; reminders not sent; OCR stuck; Gujarati PDF glyphs broken | Blocks release | ≤ 3 days |
| **S3 Minor** | Degraded experience with a workaround | Layout glitch at one breakpoint; slow but working step | Allowed with a known-issue entry | Next release |
| **S4 Trivial** | Cosmetic | Copy typo (non-legal) | Allowed | Backlog |

**AI-quality defects** are classified the same way. Any instance of a release-blocker category is **S1**.

### 7.3 Rollback criteria (production)

Roll back to the previous Cloud Run revision (traffic shift) if, within 60 minutes of deploy:

- 5xx rate > 2% for 10 min, **or**
- job failure rate > 5% for 15 min, **or**
- p90 analysis latency > 2× the pre-deploy baseline, **or**
- any S1 detected, **or**
- the smoke test fails.

**Schema rollback:** migrations are forward-only and backward-compatible (expand/contract, gate 6.3 item 3), so app rollback needs no DB rollback. If a migration itself is faulty, restore the latest nightly dump as a last resort (REL-NFR007 runbook). The free tier has no point-in-time recovery, so up to 24 hours of data can be lost.

### 7.4 Known-issue policy

- **S3 and S4** may ship if they are listed in `docs/05-quality/known-issues.md` with an ID, impact, workaround and target release.
- **S1 and S2 may never ship.**
- **AI known limitations** (for example "Gujarati handwriting not supported") are documented for users in the help content where they affect use. They must never contradict the disclaimers.

### 7.5 Post-deployment smoke tests (automated; staging and production)

Production uses the `is_test` synthetic account.

1. `GET /` (en, gu, hi) returns 200; `GET /api/v1/public/accuracy` returns 200.
2. Email-code sign-in for the test account (Mailpit or a test inbox in staging; a real code email to the test inbox in production, weekly rather than on every deploy). Google sign-in is checked manually weekly.
3. Create a case, upload a synthetic letter, wait for `ready` (≤ 120 s), confirm facts, run analysis (≤ 90 s), generate a letter, export a PDF.
4. Check the PDF downloads and contains the disclaimer.
5. Delete the test case; verify the purge within 10 min.
6. Health checks: DB, Supabase Storage, Vertex (a tiny call), Document AI (a 1-page fixture), clamd (EICAR rejected), Cloud Tasks (a no-op task round trip).
7. Check log scrubbing: the smoke-run identifiers do not appear in logs.

---

## 8. Prioritised test-case inventory

The ordering reflects build sequence (architecture §C.10) and risk.

| Rank | Test group | IDs | Pri | Build stage |
|---|---|---|---|---|
| 1 | Authorization and BOLA matrix; cross-user leakage | AZ-*, SEC-AZ-1..4 | T0 | 1 onward |
| 2 | Deterministic rule suites (Rule 14, deadlines, moratorium, CRC, 17(c), `NO_CLAUSE_CITED`) | RS-FR015/016/020/021 | T0 | 2 |
| 3 | Citation verifier, number scanner, masking | UT-AI004, UT-AI005, UT-AI002, SEC-PII-1 | T0 | 2 / 4 |
| 4 | Auth (Google + email code), sessions, CSRF, code limits; Supabase exposure; worker endpoint auth | API-FR001/002/003, SEC-CSRF/SESS/OTP, SEC-SUPA-1, SEC-TASK-1 | T0 | 1 |
| 5 | Consent enforcement (API + job) | API-FR005 | T0 | 1 / 5 |
| 6 | Upload validation and malicious files; password never stored | API-FR008, SEC-UP-* | T0 | 3 |
| 7 | Deletion, retention, account deletion; log hygiene | IT-FR031/032/033, SEC-PII-2 | T0 | 8 |
| 8 | Confirmation gate, staleness, review-before-export | API-FR011, API-AI007, IT-FR028-1 | T0 | 4 / 6 |
| 9 | Fallbacks and fault injection | REL-AI008, Section 3.6 | T0 | 5 |
| 10 | Reminders exactly once | IT-FR022 | T0 | 7 |
| 11 | Idempotency and concurrency | Sections 3.7, 3.8 | T1 | all |
| 12 | E2E journeys SCN-J1..J12 | E2E | T0 / T1 | 6 / 7 |
| 13 | Export rendering (Indic) | VIS-FR028, MAN | T0 | 6 |
| 14 | Accessibility (axe + manual) | A11Y-*, MAN-A11Y | T0 | 6 onward |
| 15 | Migration and backward compatibility | MIG | T0 | 0 onward |
| 16 | Performance L1 to L7, reliability REL-1 to 5 | PERF, REL | T1 | 9 |
| 17 | Visual regression | VIS-DAC08 | T1 | 9 |
| 18 | P1 features | FR-002, FR-025, FR-041 | T2 | 10 |

---

## 9. Defect process: reporting, reproducing and fixing

### 9.1 Reporting

**Where:** the issue tracker. A private label is used for security issues. **No real user data in tickets.**

| Field | Content |
|---|---|
| Title | `[S#][area] symptom` |
| Environment | local / staging / prod; release tag; commit |
| Identifiers | `request_id`, `job_ref`, `analysis_id`. **No names, emails, phone numbers, documents or OCR text.** |
| Steps to reproduce | Numbered, using a **synthetic fixture** or a minimal recreated case |
| Expected and actual | Including the error `code` |
| Evidence | Screenshot of the synthetic reproduction; log query link (content-free logs) |
| Severity | Per Section 7.2 |
| Related requirement | FR, NFR, AI or DAC ID |

**Production user reports (FR-035)** become `review_items`. A reviewer reproduces them under a **support grant** (FR-042) only, then files the ticket with de-identified details.

### 9.2 Reproducing

1. Reproduce on local or staging with a synthetic fixture. If real data is the only trigger, the reviewer writes a **synthetic replica** that preserves the structure (layout, reason wording pattern) without personal data.
2. AI defects: rerun the stored inputs (`analysis_id` → model, prompt, source and rule versions, AI-011) on staging against the fake recorded response *and* the live model. This separates a deterministic bug from model variance.
3. Record the minimal failing fixture under `tests/fixtures/defects/DEF-####/`.

### 9.3 Fixing

1. **Write a failing test first:** unit, integration or E2E for deterministic bugs; a new benchmark case for AI bugs (evaluation plan §14.5).
2. Fix, then pass CI including the new test.
3. For S1 and S2: a root-cause note in the ticket (what, why, why not caught, prevention).
4. AI defects: the fix must pass the regression benchmark (no blocker increase, no metric regression beyond tolerance) before release.
5. Close the ticket only after verification on staging. Production verification is required for S1.

### 9.4 Triage service levels (solo developer)

| Severity | Acknowledge | Response |
|---|---|---|
| S1 | Within 4 h of detection | Rollback first, then fix |
| S2 | 1 working day | — |
| S3 / S4 | Weekly triage | — |
