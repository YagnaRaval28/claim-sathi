# ClaimSathi: Product Requirements Document

| Field | Value |
|---|---|
| Version | 1.1 (₹0 MVP constraints, 15 October 2026) |
| Date | 15 October 2026 |
| Status | **Opportunity approved by product owner; build gated on validation sprint (Section 10.1)** |
| Supersedes | *ClaimSathi — Product Requirements Document* (v0, 12 October 2026) |
| Inputs | `docs/01-discovery/competitor-research.md` (13 October 2026). No interview notes, validation results or opportunity brief exist yet. |

### Decisions recorded from the product owner (15 October 2026)

| ID | Decision |
|---|---|
| D-001 | Build **Opportunity A**: a vernacular-first health-claim disallowance auditor and procedure-correct escalation companion. |
| D-002 | The MVP ships in **English, Gujarati and Hindi**. |
| D-003 | **Free for consumers.** No success fee, no paid tier in the MVP. |
| D-004 | MVP covers **both partial disallowances and full rejections** (repudiations). |
| D-005 | **₹0 to run the MVP.** Use free tiers and new-account trial credits, and accept their limits. AI cost is ₹0 only while trial credits last (see system-design §0.2). |
| D-006 | **Sign-in with Google, plus an emailed code.** Phone OTP is deferred, because SMS and TRAI DLT registration cost money. |
| D-007 | **Keep personal and health data in India**, including under the ₹0 constraint. |
| D-008 | **AI runs on a paid, no-training API funded by trial credits.** Free AI tiers that may use inputs for training are never used with real documents. |

### How to read this document

- **Evidence references.** `[S31]`-style references point to the source register in `competitor-research.md`.
- **Provisional targets.** A value marked **PROVISIONAL** is a proposed target that has not been benchmarked. It must be confirmed or revised after the validation sprint or the first evaluation run.
- **Hypotheses and assumptions.** A statement marked **HYPOTHESIS** or **ASSUMPTION** is not a confirmed fact. Section 15 lists all of them.
- **Verify before enabling.** A rule or fact marked **VERIFY-PRIMARY** came from a secondary source. It must be checked against the primary legal text before the feature that depends on it is enabled.

---

## Executive summary

**What ClaimSathi does.** Indian families whose health-insurance claim was rejected or only partly paid upload their insurer's letter, policy and hospital papers. ClaimSathi then:

- explains the decision in English, Gujarati or Hindi;
- checks every deduction to see whether the insurer cited a specific policy clause, as the IRDAI Master Circular (Para 17(b)) requires;
- checks rejection grounds against the policy wording and IRDAI rules;
- drafts complaint letters in which every quoted citation is checked by code;
- guides the user through the insurer grievance, Bima Bharosa and Insurance Ombudsman stages, with deadline tracking and filing-condition checks.

**Why it is needed.** The problem is large and documented:

- Health complaints make up 61.5% of Ombudsman complaints (32,655 in FY25) [S31].
- Partial disallowances were worth more than outright repudiations in FY24 (₹15,100 cr against ₹10,937 cr) [S33].
- 5,047 health complaints in FY25 were dismissed as non-entertainable, mostly on procedure [S31].

**Where it sits among competitors.** At least four Indian AI tools already draft appeals [S1–S5]. ClaimSathi is therefore **not** novel as a category. Its intended differentiation is:

- Gujarati support;
- Rule 14 filing-condition checks before an Ombudsman complaint;
- the Para 17(b) deduction audit;
- deadline tracking across all stages;
- code-verified citations;
- no success fee.

None of these has been validated against real competitor output.

**MVP gating.** The MVP is gated by a six-week validation plan. The week-1 competitor teardown is a kill test. If competitors already produce accurate, procedurally correct output, this PRD should not be built.

**Requirement counts.** The MVP has 44 functional requirements (42 P0, 2 P1), 15 AI requirements and 26 non-functional requirements. Model performance targets are PROVISIONAL until benchmarked on a gold test set.

---

## 1. Product vision

### 1.1 Name and working description

**ClaimSathi** ("claim companion") is a free, mobile-first web app. It helps Indian health-insurance policyholders challenge rejected or partly paid claims through the official grievance route, in their own language, with every argument traceable to a real clause or rule.

### 1.2 Problem statement

When an Indian health insurer rejects a claim or deducts part of it, the policyholder usually receives a short letter. The letter often uses terms such as "non-payable items", "reasonable and customary" or "pre-existing disease", sometimes without naming the specific policy clause relied on.

The official route to challenge it is free but procedural:

1. Write to the insurer.
2. Optionally complain on Bima Bharosa.
3. Go to the Insurance Ombudsman within one year, but only after the insurer has had its chance to respond [S47].

**Evidence that this fails people:**

- **Scale is rising.** Health-claim complaints on Bima Bharosa grew from 47,658 (FY24) to 73,729 (FY26, to February) [S29].
- **Partial deductions matter most by value.** They exceed outright repudiations in rupee terms [S33].
- **Procedure trips people up.** 17% of health complaints the Ombudsman disposed of in FY25 (5,047 of 29,156) were non-entertainable [S31].
- **Complainants often win when heard.** About 53% of health disposals in FY25 ended in a recommendation or an award for the complainant (INFERRED) [S31].
- **The regulator lacks reason data.** IRDAI does not collect reasons for repudiation [S34].

### 1.3 Target users and unmet needs (HYPOTHESIS until interviews)

| Segment | Unmet need |
|---|---|
| Policyholders and family members with a rejected or partly paid health claim | Know whether the decision is challengeable, and file a complaint the insurer and Ombudsman must take seriously |
| Gujarati- and Hindi-preferring users | Explanation and letters in their language. No competitor was found serving Gujarati [S1–S5]. |
| Family "helpers" (for example an adult child acting for a parent) | Prepare the case for the policyholder to sign and file |

### 1.4 Core value proposition

> "Understand why your health claim was cut, and file a complaint that cannot be dismissed on procedure, in your language, for free, with every claim backed by a clause you can check."

### 1.5 Differentiation

Compared with fairClaims, ClaimAssist Pro, ClaimBhai AI and UnDeny [S1–S5], based on public pages only:

| Capability | Competitors (public evidence) | ClaimSathi MVP | Validation status |
|---|---|---|---|
| Gujarati UI and letters | None found | Yes | UNVALIDATED demand (AS-02) |
| Hindi | Schema metadata only (support contact) | Yes | UNVALIDATED |
| Para 17(b) clause-reference audit per deduction | fairClaims checks deductions against wording; Para 17(b) not mentioned | Yes, a per-line status | UNVALIDATED (AS-04) |
| Rule 14 Ombudsman filing-condition checks | Not described | Yes, deterministic | UNVALIDATED (AS-03) |
| Deadline tracking across all stages | Not described | Yes | — |
| Code-verified citations; published accuracy | Not described | Yes | Competitor accuracy unknown (AS-01) |
| Pricing | 0–15% success fee | Free, no success fee | D-003 |

### 1.6 Product goals

| ID | Goal |
|---|---|
| G-1 | Explain any in-scope rejection or deduction in plain English, Gujarati or Hindi. |
| G-2 | Produce complaint packs that meet the stage's procedural preconditions, so no user is dismissed for a reason the app could have caught. |
| G-3 | Make every regulatory or policy citation verifiable by the user, and never show an unverified quote as fact. |
| G-4 | Keep the user on time through every escalation stage. |
| G-5 | Handle medical data with consent, data minimisation and full user control. |

### 1.7 Success metrics (all targets PROVISIONAL)

| ID | Metric | Definition | Provisional target (6 months after public launch) | Goal |
|---|---|---|---|---|
| M-01 | Activation | Signed-up users who confirm extracted fields for at least one case | ≥ 50% | G-1 |
| M-02 | Diagnosis delivered | Confirmed cases that receive an analysis without a system failure | ≥ 95% | G-1 |
| M-03 | Pack completion | Diagnosed cases that export a Stage 1 letter | ≥ 40% | G-2 |
| M-04 | Citation precision | Displayed citations judged correct (exists *and* supports the sentence) in a monthly human audit | ≥ 98% | G-3 |
| M-05 | Unverified quotes shown | Quoted spans shown to users that failed the deterministic verifier | **0** (hard requirement, not provisional) | G-3 |
| M-06 | Missed deadlines | Active cases where a tracked deadline passed with no reminder sent | 0 | G-4 |
| M-07 | Ombudsman non-entertainable rate (self-reported) | Users reaching Stage 3 who report dismissal as non-entertainable | < 5%, against a CIO baseline of about 17% [S31] | G-2 |
| M-08 | Reported favourable outcome | Closed cases reporting full or partial payment after using ClaimSathi | Baseline only; no target until 50 closed cases | Impact |
| M-09 | Trust | Post-case rating of 4 or 5 out of 5 | ≥ 80% | G-3 |
| M-10 | Vernacular usage | Cases with Gujarati or Hindi as display language | Tracked to test AS-02; no target | — |
| M-11 | Median time to first letter | From first upload to Stage 1 export, including the user's review time | ≤ 15 minutes | G-1 |

---

## 2. User and market definition

### 2.1 Personas (ALL ARE HYPOTHESES; validate with 15–20 interviews)

**P1, Rahul, 34: salaried, Ahmedabad, English and Hindi (primary)**

- **Situation:** his father's cashless claim was partly paid, with about ₹1.2 lakh deducted under "non-payable items" and "proportionate deduction".
- **Motivation:** recover the money, and find out whether the deduction was lawful.
- **Pain points:**
  - The settlement letter lists deductions without clause references.
  - The TPA helpline gives scripted answers.
  - He doesn't know the Ombudsman exists.
- **Constraints:**
  - Limited time; uses his phone during commutes.
  - Is not the policyholder, since his father signs.

**P2, Meena, 52: homemaker, Rajkot, Gujarati-preferring (primary)**

- **Situation:** her reimbursement claim was rejected for "non-disclosure of pre-existing disease". The family has held the policy continuously for six years.
- **Motivation:** fairness; she distrusts paid agents.
- **Pain points:**
  - English legal language.
  - Fear of making a mistake.
  - Doesn't know that the 60-month moratorium may apply [S45].
- **Constraints:**
  - Low-end Android phone, intermittent 4G.
  - Comfortable reading Gujarati, less so typing it.

**P3, family helper (secondary)**

An adult child or relative who manages the case on a parent's behalf. They need to prepare everything, while the policyholder signs. Rule 14 requires the complainant, or their legal heirs, nominee or assignee, to make the complaint [S47].

**Deferred personas (not served in the MVP):** hospital billing desks, claim consultants and NGO volunteers handling several clients.

### 2.2 Current alternatives and workflows

| Alternative | What users do today | Limitation (from research) |
|---|---|---|
| Do nothing | Accept the deduction | Money lost. LocalCircles reports 29% partly approved "for invalid reasons" (self-reported, directional) [S38]. |
| Call the TPA or insurer | Phone helpline | No written record; no clause reference |
| Human claim-recovery firms | Hand over the case | 12–22% success fee plus upfront fee; highly selective (about 3–4 of 100 cases in 2020) [S9–S11] |
| AI appeal tools | Upload, get a draft | No Gujarati found; 10–15% success fee on some; accuracy unknown [S1–S5] |
| Broker claims desks | Ask the broker | Mainly for the broker's own customers [S13, S14] |
| ChatGPT or Claude used directly | Paste the letter, get a draft | No verification; no procedure checks [S15] |
| File directly on Bima Bharosa or with the Ombudsman | Fill in the forms | Free, but no explanation or drafting help; procedural pitfalls [S31] |

### 2.3 Jobs to be done

| ID | Job |
|---|---|
| JTBD-1 | When my claim is cut, help me understand exactly what was deducted and why, so I can decide whether to fight it. |
| JTBD-2 | When I decide to fight, help me write a complaint that cites the right rules, so the insurer has to respond properly. |
| JTBD-3 | When the insurer doesn't fix it, tell me exactly what to do next and when, so I don't lose my right to go to the Ombudsman. |
| JTBD-4 | When I'm doing this for a parent, let me prepare everything so they only need to sign. |

### 2.4 Accessibility, device, language and regional requirements

**Devices and connectivity**

- Mobile-first, responsive web app. Primary target is a low-end Android phone (2 GB RAM, Chrome).
- Desktop is supported.
- No native app in the MVP.

**Network**

- Usable on a "Slow 4G" network profile.
- Uploads resume or retry automatically after a network drop (FR-009).

**Languages**

- UI, explanations and letters in English (`en`), Gujarati (`gu`) and Hindi (`hi`).
- The user can switch language at any time.
- The English original of every quoted clause is always available.

**Accessibility**

- WCAG 2.2 AA (NFR-012).
- Large-text mode.
- Screen-reader labels in all three languages.

**Region and scope**

- India only.
- Indian-registered health and general insurers offering health products.
- Amounts in INR, displayed in Indian digit grouping (₹1,20,000).
- Dates displayed as DD/MM/YYYY.

---

## 3. Product scope

### 3.1 MVP features

| Feature | Requirements | Why it is in the MVP |
|---|---|---|
| Account and onboarding | FR-001 to FR-006 | Consent and eligibility are legal prerequisites |
| Case and documents | FR-007 to FR-012 | Every downstream feature depends on confirmed facts |
| Analysis | FR-013 to FR-019 | Core value: explanation, Para 17(b) audit, grounded counter-points |
| Escalation engine | FR-020 to FR-023 | Main differentiator: procedure-correct, deadline-tracked |
| Complaint packs | FR-024 to FR-029 | The output users act on |
| Data controls | FR-030 to FR-033 | DPDP obligations for health data [S51] |
| Feedback and outcomes | FR-034, FR-035 | Measures impact and catches AI errors |
| Settings | FR-036 | Language and notification control |
| Administration | FR-037 to FR-042 | Knowledge base and rules versioning; error review |
| Public site | FR-043, FR-044 | Trust, disclaimers, links to official free channels |

### 3.2 Deferred features

| Feature | Target | Reason for deferral |
|---|---|---|
| Case-strength score from similar Ombudsman awards | Not planned | **Blocked.** CIO terms forbid reproduction or derivative works, and current awards are OTP-gated [S49, S32]. Revisit only with a licence. |
| Rule-based case-strength indicator | v2 | Needs outcome data (M-08) to calibrate; risk of false confidence |
| WhatsApp and SMS reminders; phone OTP sign-in | v2 / scale-up | Need DLT registration and paid SMS (D-005, D-006). Email, in-app and .ics calendar reminders cover the MVP. |
| "Ask your policy" chat | v2 | Not needed for the core job; adds hallucination surface |
| Consumer-commission complaint drafting | v2+ | Legal-practice risk; government Jagriti assistant exists [S57] |
| Clinic and consultant multi-client workspace | v3 | Different buyer (Opportunity B) |
| Payments | Not in MVP | D-003 |
| Additional languages (Marathi, Tamil and others) | v2+ | Validate Gujarati and Hindi first |

### 3.3 Explicit exclusions

1. Legal advice, legal representation, or appearing at hearings.
2. Filing on any portal, or emailing the insurer, on the user's behalf. **The user always sends.**
3. Success fees or any fee based on the amount recovered.
4. Motor, life, travel and non-insurance disputes.
5. Selling, recommending or comparing insurance products.
6. Using user documents to train or fine-tune models.
7. Scraping or reusing Ombudsman awards.
8. Predicting win probability.

### 3.4 Feature dependencies and prioritisation rationale

```
FR-001..006 (account, consent)
   └─> FR-007..012 (case, upload, OCR, confirmation)  ── gate: fields confirmed
          ├─> FR-013 classify ─> FR-014 policy wording ─> FR-015 deduction audit
          │                                           └─> FR-016 rejection analysis
          │                                                  └─> FR-017 explanation, FR-018 checklist
          ├─> FR-020..022 escalation engine (needs confirmed dates, rules table FR-039)
          └─> FR-024..029 letters (need FR-015/016 output + AI-004 verifier + FR-020 stage)
FR-038 knowledge base and FR-039 rules table must be populated before any analysis runs.
```

**Prioritisation principle:** anything required for a correct, verified Stage 1 letter and for correct deadlines is P0. Convenience features are P1. Everything else is deferred.

---

## 4. Detailed functional requirements

### 4.0 Conventions

**Priority**

- **P0** = required for the MVP release.
- **P1** = planned for the MVP; may slip to a fast follow without blocking release.

**Roles**

| Role | Who |
|---|---|
| `user` | A signed-in consumer |
| `admin` | The operator: knowledge base, rules, metrics |
| `reviewer` | Reviews flagged outputs and translations |
| `system` | Background jobs |

**Case ownership.** A case belongs to exactly one user. No other user can access it. Admins **cannot** read case documents or content unless the user has granted support access for that case (FR-042).

**Languages.** All user-facing strings exist in `en`, `gu` and `hi`. Missing translations block release (NFR-021).

---

### A. Account, authentication and onboarding

#### FR-001: Sign up and sign in with an email code
- **Story:** As a new user without a Google account handy, I want to sign in with a code sent to my email, so I don't need a password.
- **Behaviour:**
  - The user enters an email address.
  - The system emails a 6-digit code, valid for 10 minutes.
  - When the code is verified, an account is created if none exists, and the user is signed in.
- **Inputs:** email, code.
- **Outputs:** a session (see FR-003) and a user record.
- **Business rules:**
  - Maximum 5 code requests per email per hour.
  - Maximum 5 wrong attempts per code, then the code is invalidated.
  - Resend is allowed after 60 seconds.
  - A global daily cap on code emails (PROVISIONAL 500) protects cost and sender reputation.
  - The response to a code request never reveals whether an account exists.
  - The code email contains only the code and its expiry.
- **Preconditions:** none.
- **Success:** the user lands on onboarding (FR-004) on first sign-up, or on the case list if already onboarded.
- **Failure:**
  - Invalid email format: inline error.
  - Email provider failure: "Couldn't send the code. Try again, or continue with Google."
  - Rate limit reached: show the time remaining.
- **Edge cases:**
  - An email already used with Google signs in to the same account. Both methods prove control of the same verified email.
  - Code emails may land in spam: the screen says "Check your spam folder".
- **Acceptance criteria:**
  - AC1: a valid email receives a code, and a correct code creates exactly one user.
  - AC2: the 6th code request within an hour is rejected with a wait message.
  - AC3: after 5 wrong attempts, the code no longer works.
  - AC4: an expired code (over 10 minutes) is rejected.
  - AC5: the request endpoint responds identically for known and unknown emails.
- **Depends on:** a transactional email sender in India (Amazon SES, Mumbai; system-design §1.1). **Priority:** P0.

#### FR-002: Sign in with Google (primary)
- **Story:** As Meena on an Android phone already signed in to Google, I want to sign in with one tap.
- **Behaviour:** standard OAuth/OIDC sign-in. It is the first option on the sign-in screen.
- **Business rules:**
  - The email is taken from Google and must be verified.
  - A Google sign-in and an email-code sign-in with the same verified email resolve to one account.
  - No phone number is collected in the MVP.
- **Acceptance criteria:**
  - AC1: Google sign-in creates, or signs in, a user with a verified email.
  - AC2: cancelling the OAuth flow returns the user to sign-in with no error state.
  - AC3: Google and email-code sign-ins with the same email reach the same account.
- **Priority:** P0 (raised from P1 by D-006).

#### FR-003: Session management and sign-out
- **Behaviour:**
  - Sessions use secure, HTTP-only cookies.
  - Idle timeout is 30 days on a device the user marks "trusted", otherwise 24 hours.
  - "Sign out" ends the current session. "Sign out everywhere" (in Settings) revokes all sessions.
- **Acceptance criteria:**
  - AC1: after sign-out, the back button cannot display case data.
  - AC2: "Sign out everywhere" invalidates the sessions on other devices within 60 seconds.
- **Priority:** P0.

#### FR-004: Choose language
- **Story:** As Meena, I want to use the app in Gujarati.
- **Behaviour:**
  - The first screen offers ગુજરાતી / हिन्दी / English. The initial selection follows the browser locale if it is supported, otherwise English.
  - The choice is stored on the user and can be changed from any screen header.
- **Business rules:**
  - The display language controls the UI and explanations.
  - Letter language is chosen separately per letter (FR-024).
- **Acceptance criteria:**
  - AC1: switching language re-renders the current screen with no loss of entered data.
  - AC2: no English fallback strings appear in `gu` or `hi` in the release build (checked by NFR-021).
- **Priority:** P0.

#### FR-005: Consent and disclaimer
- **Story:** As a user, I want to know exactly what happens to my medical documents before I upload them.
- **Behaviour:** before the first case is created, the user sees a plain-language notice in their language. It covers:
  1. what is collected;
  2. the purposes, which are analysing their claim, generating letters and sending reminders;
  3. that de-identified text is processed by a third-party AI provider (named);
  4. retention periods;
  5. their rights to access, correct, delete and withdraw consent;
  6. a grievance contact;
  7. that ClaimSathi is a **self-help drafting tool, not legal advice**, and that the official channels are free.

  The user ticks separate checkboxes for (a) processing their documents and (b) email reminders. Item (a) is required to proceed; item (b) is optional.
- **Outputs:** a consent record containing user, consent version, purposes, timestamp, language and IP hash.
- **Business rules:**
  - Consent text is versioned.
  - A new version that changes purposes requires re-consent at next sign-in, before any new processing.
  - Withdrawing consent (a) stops all processing and offers deletion (FR-032).
- **Acceptance criteria:**
  - AC1: case creation is impossible without consent (a) at the current version.
  - AC2: the consent record stores the exact version shown.
  - AC3: withdrawing consent prevents new analysis jobs for that user. This is checked by job-level authorisation, not just the UI.
- **Depends on:** legal review (R-03). **Priority:** P0.

#### FR-006: Eligibility screening
- **Story:** As a user, I want to know quickly whether ClaimSathi can help with my situation.
- **Behaviour:** a short questionnaire runs at case creation.
  1. Is this a **health insurance** claim with an insurer in India? (yes / no / not sure)
  2. What happened? (claim **rejected** / claim **partly paid** / claim **delayed or pending** / other)
  3. Is the policy individual, family floater, or through an employer or group? (group is accepted with the caveat in OQ-07)
  4. Who is the policyholder or insured person, and what is your relationship to them?
  5. Is this matter **already in any court, consumer commission, or arbitration**? (yes / no / not sure)
  6. Roughly when was the insurer's decision letter dated?
- **Business rules:**
  - Q1 = no: show an out-of-scope message with links to official channels, and do not create a case.
  - Q2 = delayed or pending: create the case in **"delay" mode**. Analysis is limited to timeline rules and the letter becomes a delay-grievance template. If OQ-15 resolves against including this mode, it falls back to an out-of-scope message.
  - Q5 = yes: create the case, but mark Stage 3 as **not maintainable** (RULE-ESC-04) and explain why.
  - Q6 is used only as a provisional date until the letter date is extracted and confirmed (FR-011).
- **Acceptance criteria:**
  - AC1: each branch produces the specified state.
  - AC2: answers are stored on the case and can be edited until the first letter is exported.
- **Priority:** P0.

---

### B. Case and documents

#### FR-007: Create and list cases
- **Behaviour:**
  - The user can hold several cases.
  - The case list shows insurer, patient initials, amount in dispute, current stage, next deadline and status.
- **Business rules:**
  - Maximum 10 open cases per user (PROVISIONAL; prevents abuse).
  - Each case records the complainant (policyholder), the patient and the preparing user's relationship to them.
- **Acceptance criteria:**
  - AC1: a user sees only their own cases (verified by an authorisation test).
  - AC2: the 11th open case is blocked with a message.
- **Priority:** P0.

#### FR-008: Upload case documents
- **Story:** As Rahul, I want to photograph or upload my letters and bills from my phone.
- **Behaviour:**
  - Upload by file picker or camera capture.
  - The user tags each file with a type, or accepts an auto-suggested type:

    | Type key | Document |
    |---|---|
    | `decision_letter` | Repudiation or settlement letter |
    | `settlement_breakup` | Deduction or settlement breakup |
    | `policy_schedule` | Policy schedule |
    | `policy_wording` | Policy wording |
    | `discharge_summary` | Discharge summary |
    | `final_bill` | Final hospital bill |
    | `reports` | Investigation reports |
    | `insurer_correspondence` | Insurer correspondence |
    | `other` | Other |

  - Multi-page photos can be grouped into one document.
- **Inputs:**
  - Formats: PDF, JPG, JPEG, PNG.
  - Size: ≤ 20 MB per file.
  - Count: ≤ 15 files per case.
  - Total size: ≤ 50 MB per case.
  - Pages: ≤ 60 per case.
  - These caps fit the ₹0 storage tier (D-005). The previous limits were 25 files and 200 pages. Raise them at scale-up.
- **Outputs:** document records, with files stored encrypted (NFR-005).
- **Business rules:**
  - At least one `decision_letter` is required to run analysis.
  - Password-protected PDFs: prompt for the password, use it once to decrypt, and **never store the password**.
  - Files are scanned for malware before processing.
  - Duplicate files (same hash in the same case) are rejected with a notice.
- **Failure:**
  - Unsupported format or over size: specific inline message.
  - Corrupt file: "Couldn't open this file".
  - Malware detected: file rejected and the event logged.
- **Edge cases:**
  - Indian insurer letters are often password-protected, commonly with a date of birth.
  - A HEIC photo is rejected with "take the photo with the in-app camera instead".
  - Sideways photos are auto-rotated.
- **Acceptance criteria:**
  - AC1: each listed format uploads and is assigned the chosen type.
  - AC2: a 21 MB file is rejected before upload starts (client-side check) and again server-side.
  - AC3: a password-protected PDF is processed after the correct password is given. The password does not appear in any database row or log.
  - AC4: analysis cannot start without a `decision_letter`.
- **Priority:** P0.

#### FR-009: Resilient upload and processing status
- **Behaviour:**
  - Uploads retry automatically up to 3 times on network failure.
  - Each document shows a status: `uploading` → `queued` → `reading` → `ready` | `needs_attention` | `failed`.
  - Progress updates without a page reload.
- **Business rules:** a closed browser does not lose an upload that reached `queued`. Processing continues server-side.
- **Acceptance criteria:**
  - AC1: simulated network loss mid-upload, followed by recovery, completes without user action.
  - AC2: closing the tab after `queued` and reopening shows the processed result.
- **Priority:** P0.

#### FR-010: Text recognition (OCR) and field extraction
- **Behaviour:**
  - Text is extracted from each document, using OCR for images and scanned PDFs. Page and bounding-box positions are kept so the source can be highlighted.
  - The fields below are extracted into a structured schema (AI-003), each with a confidence value and a source location.

  | Field | Notes |
  |---|---|
  | Insurer | Matched to the controlled list of IRDAI-registered insurers |
  | TPA | |
  | Policy number | |
  | Product name and UIN | |
  | Policy type | |
  | **First inception date** (start of continuous coverage) | |
  | Current policy period | |
  | Sum insured | |
  | Patient name | Masked downstream |
  | Hospital | |
  | Admission and discharge dates | |
  | Claim number | |
  | Claim type | Cashless or reimbursement |
  | Amount claimed | |
  | Amount approved or paid | |
  | Amount disallowed | |
  | **Decision letter date** | |
  | Decision type | `repudiation` / `partial` |
  | **Stated reasons (verbatim)** | |
  | **Clauses cited by the insurer (verbatim)** | |
  | Grievance contact, if printed | |

- **Business rules:**
  - Amounts and dates are never inferred by the model. A field that is not found stays empty and is marked `not_found`.
  - Verbatim fields must string-match the OCR text (AI-005).
- **Failure:** OCR quality below the threshold (AI-006) sets the document to `needs_attention` with "Photo unclear: retake in good light, flat, all edges visible".
- **Acceptance criteria:**
  - AC1: on the gold test set, field-level accuracy meets AI-012.
  - AC2: every extracted verbatim field maps to a source page and region.
  - AC3: no amount or date appears that is absent from the OCR text.
- **Depends on:** AI-001 to AI-006. **Priority:** P0.

#### FR-011: Review and confirm extracted facts (gate)
- **Story:** As a user, I want to check what the app read before it analyses anything.
- **Behaviour:**
  - A review screen lists all fields grouped as Policy, Claim and Decision.
  - Low-confidence and empty required fields appear first and are highlighted.
  - Tapping a field shows the source snippet image.
  - The user can edit any field, then presses "These details are correct".
- **Required fields to confirm:**
  - insurer;
  - decision letter date;
  - decision type;
  - at least one stated reason;
  - amount claimed;
  - amount paid, if the decision type is partial;
  - first inception date, which may be marked "I don't know".
- **Business rules:**
  - Analysis (FR-013 onward) cannot start until confirmation.
  - Editing a confirmed field after analysis marks the analysis and letters **stale**. They must be regenerated before export.
  - User-edited values are stored with `confirmed_by_user = true` and the original extracted value kept for evaluation.
- **Edge cases:**
  - Several decision letters, such as a first decision and a reply to a grievance: the user picks which one is the "current decision". Both remain in the timeline.
  - Patient and policyholder differ: both are captured.
- **Acceptance criteria:**
  - AC1: analysis API calls fail with `409 fields_not_confirmed` before confirmation.
  - AC2: changing the decision date after analysis marks letters stale and recomputes deadlines (FR-021).
  - AC3: the original and edited values are both retrievable.
- **Priority:** P0.

#### FR-012: Deduction line-item extraction (partial cases)
- **Story:** As Rahul, I want each deducted amount listed separately so I can see which cuts are questionable.
- **Behaviour:** for `partial` decisions, a line-item table is extracted from `settlement_breakup`, `decision_letter` and `final_bill`. Each line has:
  - description;
  - billed amount;
  - deducted amount;
  - the insurer's reason (verbatim);
  - the cited clause reference (verbatim or `none`).

  The user can edit, add or delete lines.
- **Business rules:**
  - The sum of deducted line amounts is compared with the confirmed disallowed amount.
  - If they differ by more than ₹1 or 1% (whichever is larger), show "Line items don't add up to the deducted amount: please check".
  - The user may proceed with this warning visible.
- **Edge cases:**
  - Deductions given only as a lump sum: a single line `unitemised` is created, and the audit flags it under Para 17(b).
  - A breakup document that is missing triggers an evidence-checklist item (FR-018).
- **Acceptance criteria:**
  - AC1: line items carry source locations.
  - AC2: the mismatch warning appears exactly when the threshold is exceeded.
  - AC3: user edits persist and are flagged as user-entered.
- **Priority:** P0.

---

### C. Analysis

#### FR-013: Classify the decision and its reasons
- **Behaviour:** each stated reason or deduction line is mapped to the taxonomy below, with a confidence value (AI-006).

  | Category key | Meaning |
  |---|---|
  | `ped_waiting` | Pre-existing disease waiting period |
  | `non_disclosure` | Non-disclosure or misrepresentation |
  | `specific_waiting` | Specific-illness waiting period |
  | `initial_waiting` | Initial 30-day or similar waiting period |
  | `exclusion` | Policy exclusion |
  | `not_medically_necessary` | Including "no active line of treatment" and "OPD-type" |
  | `documents_or_intimation` | Missing documents, late intimation or late submission |
  | `policy_not_in_force` | |
  | `non_payable_items` | |
  | `room_rent_proportionate` | Room-rent capping or proportionate deduction |
  | `reasonable_customary` | |
  | `sub_limit` | |
  | `copay_deductible` | |
  | `other_unknown` | |

- **Business rules:**
  - Below the confidence threshold, the category is `other_unknown` and the user is asked to pick from a plain-language list. A selection by the user overrides the model.
- **Acceptance criteria:**
  - AC1: every reason and line gets exactly one category.
  - AC2: classification metrics on the gold set meet AI-012.
- **Priority:** P0.

#### FR-014: Resolve the applicable policy wording
- **Behaviour:** the system determines which policy wording to analyse against, in this order:
  1. A `policy_wording` the user uploaded for this case.
  2. A library wording matched by insurer, product UIN and the version effective on the admission date.
  3. No wording.

  The source used is shown to the user, for example "Using: Star Health Comprehensive, UIN …, version effective 01/04/2024 (from our library)". The user can switch to "use my uploaded copy".
- **Business rules:**
  - A library match needs an exact UIN match, or an insurer + product name match confirmed by the user.
  - With no wording, the case runs in **limited mode**:
    - only regulation-based points and the Para 17(b) audit are produced;
    - the letter requests the clause-level reasons;
    - the evidence checklist asks for the wording.
  - A user-uploaded wording is chunked and indexed **for that case only**. It never enters the shared library unless a separate opt-in exists (none in the MVP).
- **Acceptance criteria:**
  - AC1: the wording source is always displayed on the analysis screen.
  - AC2: limited mode produces no policy-clause citations.
  - AC3: user wording is retrievable only within its case (authorisation test on retrieval).
- **Depends on:** FR-038. **Priority:** P0.

#### FR-015: Deduction audit (Para 17(b) check)
- **Story:** As Rahul, I want to see for each deduction whether the insurer justified it with a specific clause, and whether that clause says what they claim.
- **Behaviour:** for every line item (FR-012) and every repudiation reason, assign an **audit status**:

  | Status | Condition | User-facing meaning |
  |---|---|---|
  | `NO_CLAUSE_CITED` | Insurer gave no specific policy term reference | IRDAI requires disallowances to reference specific policy terms (Master Circular Para 17(b)) [S45]. You can ask for it. |
  | `CLAUSE_NOT_FOUND` | Cited clause reference not found in the resolved wording | The clause they cited could not be found in the policy wording used. Check that the right wording was used. |
  | `CLAUSE_FOUND_QUESTIONABLE` | Clause found; analysis finds a grounded counter-point | The clause exists, but there are reasons it may not apply (listed with sources). |
  | `CLAUSE_FOUND_APPEARS_VALID` | Clause found and no grounded counter-point | This deduction appears consistent with your policy. Challenging it may not succeed. |
  | `CANNOT_ASSESS` | Insufficient data, or model abstained | We could not assess this item. |

- **Business rules:**
  - `NO_CLAUSE_CITED` is determined **deterministically**: the verbatim clause field is empty or `none`, or contains no clause or section identifier pattern. Patterns are configurable in the rules table.
  - `CLAUSE_NOT_FOUND` is determined by searching the resolved wording for the cited identifier and title. It is never set in limited mode; `CANNOT_ASSESS` is used instead.
  - `QUESTIONABLE` requires at least one counter-point that passes the citation verifier (AI-004). Otherwise the status falls back to `APPEARS_VALID` or `CANNOT_ASSESS`.
  - The app **must** display `APPEARS_VALID` honestly. It never inflates a case.
- **Outputs:**
  - A per-line status.
  - Amounts by status.
  - Totals: "₹X across N items with no clause cited".
- **Acceptance criteria:**
  - AC1: on the gold set, `NO_CLAUSE_CITED` precision is 100% (deterministic).
  - AC2: no `QUESTIONABLE` status exists without a verified citation.
  - AC3: status totals equal the sum of line amounts.
- **Depends on:** FR-012, FR-014, AI-004. **Priority:** P0.

#### FR-016: Grounded analysis of rejection grounds
- **Behaviour:** for each reason, the system produces 0–5 **counter-points**. Each counter-point contains:
  - a plain-language statement;
  - its **basis type**: `regulation` / `policy_wording` / `case_fact` / `deterministic_rule`;
  - citations (chunk ID + verbatim quote);
  - an "applies if" condition when it depends on a fact the user must confirm.

  Deterministic rule checks run first:

  | Rule | Fires when | Status |
  |---|---|---|
  | RULE-MC-03, moratorium | Reason is `non_disclosure` or `ped_waiting`, and the confirmed first inception date is at least 60 months before admission (continuous coverage). Produces a counter-point citing Para 13 [S45] with caveat "except established fraud". | Enabled |
  | RULE-MC-02, repudiation | Decision is `repudiation`. Produces a request for confirmation that the Claims Review Committee approved it (Para 17(a)). | Enabled |
  | RULE-MC-05, documents | Reason is `documents_or_intimation` and concerns hospital documents. Cites Para 17(c). | Enabled |
  | RULE-MC-04, PED waiting cap | 36-month cap | **Disabled until VERIFY-PRIMARY is complete** (OQ-06) |

- **Business rules:**
  - The model may reason **only** over retrieved chunks and confirmed fields (AI-005).
  - A counter-point whose citations fail verification is dropped, never shown.
  - If no counter-points survive, show "We found no grounded argument against this reason" and set `CANNOT_ASSESS` or `APPEARS_VALID` as appropriate.
- **Acceptance criteria:**
  - AC1: the moratorium rule fires on the test fixture with inception at 61 months, and not at 59 months or with the date unknown.
  - AC2: 100% of displayed counter-points have at least one verified citation, or are `deterministic_rule` with a stored rule source.
  - AC3: unverified counter-points are logged for review (FR-040).
- **Priority:** P0.

#### FR-017: Plain-language explanation
- **Behaviour:** a summary of 150 words or fewer in the display language, covering:
  - what was decided;
  - the amount at stake;
  - the main reasons in plain words;
  - how many items lack clause references;
  - recommended next step.

  Insurance terms link to a glossary.
- **Business rules:**
  - Numbers come from confirmed fields only.
  - No predictive language: "you will win" and similar phrases are banned and covered by the evaluation checklist.
  - A one-line disclaimer appears.
- **Acceptance criteria:**
  - AC1: all numbers match confirmed fields (automated check).
  - AC2: banned-phrase list check passes.
  - AC3: Gujarati and Hindi versions pass native-reviewer spot checks (NFR-021).
- **Priority:** P0.

#### FR-018: Evidence checklist
- **Behaviour:** a list of documents that would strengthen the case, generated from category-to-evidence mappings in the rules table (admin-maintained, **not** model-invented). Examples:
  - `ped_waiting` / `non_disclosure`: a treating doctor's certificate stating the date of first diagnosis, plus earlier policy schedules proving continuity.
  - `room_rent_proportionate`: the hospital tariff sheet and room category record.

  Users can tick items as obtained, or upload them (which links to FR-008).
- **Acceptance criteria:**
  - AC1: every checklist item traces to a mapping row.
  - AC2: ticking or uploading updates the case and the enclosure list in letters.
- **Priority:** P0.

#### FR-019: Abstention and limited-analysis states
- **Behaviour:** when inputs are insufficient (unreadable decision letter, no reasons extracted, out-of-scope product) or the model abstains (AI-006), show a specific state. Each state has a recovery action: retake photo, type the reason manually, upload wording, or contact support.
- **Business rules:** a typed reason entered by the user is treated as a confirmed field and stored verbatim.
- **Acceptance criteria:**
  - AC1: each abstention trigger in the AI-006 table maps to a distinct UI state and recovery action.
  - AC2: there is never an empty analysis screen without an explanation.
- **Priority:** P0.

---

### D. Escalation engine

#### FR-020: Stage model and filing-condition (maintainability) checks
- **Behaviour.** Each case has a stage:

  | Stage | Meaning |
  |---|---|
  | `S0_PREPARE` | Preparing the case |
  | `S1_INSURER_GRIEVANCE` | Written representation to the insurer's grievance officer |
  | `S2_BIMA_BHAROSA` | Bima Bharosa complaint. **Optional; may run in parallel; not a precondition for S3.** |
  | `S3_OMBUDSMAN` | Insurance Ombudsman complaint |
  | `CLOSED` | Case closed |

- **Stage 3 checks** run before the Ombudsman pack is generated. Each is deterministic, from the rules table:

  | Rule | Source | Check | On failure |
  |---|---|---|---|
  | RULE-ESC-01 | Rule 14(3)(a) | A written, email or online representation to the insurer has been logged (FR-023) | **Block.** Explain that the insurer must be written to first. |
  | RULE-ESC-02 | Rule 14(3)(a) | The insurer rejected it, did not reply within one month of the representation, or the user is unsatisfied with the reply | **Block** until one month has passed or a reply is logged. |
  | RULE-ESC-03 | Rule 14(3)(b) | Filing is within one year of the insurer's rejection or reply, or of the one-month expiry | **Warn, do not block** (Rule 14(4) allows condonation). State that it is late and the Ombudsman may refuse. |
  | RULE-ESC-04 | Rule 14(5) | Not pending or decided in a court, consumer forum or arbitration (FR-006 Q5) | **Block.** Explain why. |
  | RULE-ESC-05 | Rule 17(3) | Amount in dispute ≤ ₹50 lakh | **Warn.** Compensation is capped at ₹50 lakh. |
  | RULE-ESC-06 | Rule 14(1)–(2) | The complainant is the policyholder or insured, or their legal heir, nominee or assignee | **Inform.** The complaint must be signed and filed by the complainant, not the helper. |

- **Business rules:**
  - Rules are versioned with effective dates and source references (FR-039).
  - The rule version applied is stored on the case.
  - The model is never consulted for these checks.
- **Acceptance criteria:**
  - AC1: a unit test covers each rule's pass and fail paths, using rule-table fixtures.
  - AC2: an Ombudsman pack cannot be generated while any **Block** rule fails (API-enforced).
  - AC3: S2 can be skipped without affecting S3 eligibility.
- **Depends on:** FR-039. **Priority:** P0.

#### FR-021: Deadline computation
- **Behaviour:** deadlines are computed from confirmed dates and logged events using the rules table:

  | Deadline | Basis | Status |
  |---|---|---|
  | Ombudsman eligibility opens | Date the S1 representation was sent + 1 month (RULE-ESC-02) | — |
  | Ombudsman limitation date | 1 year from the insurer's rejection or reply, or from the one-month expiry, whichever applies (RULE-ESC-03) | — |
  | Expected insurer grievance response | Configurable; default 14 days | **VERIFY-PRIMARY**, OQ-05 |
  | Ombudsman award expected | 3 months from complete complaint (Rule 17(4)), shown as informational only | — |

  Dates are shown as calendar dates and as "N days left".
- **Business rules:**
  - Dates are calculated in IST.
  - "One month" means the same day number in the next calendar month. If that day does not exist, the last day of that month is used.
  - "One year" is calculated the same way.
  - This interpretation is recorded in the rules table and confirmed by legal review (OQ-10).
- **Acceptance criteria:**
  - AC1: fixture tests for month-end and leap-year dates pass.
  - AC2: changing a source date recomputes all dependent deadlines and reschedules reminders.
- **Priority:** P0.

#### FR-022: Reminders
- **Behaviour:** email and in-app reminders are sent:
  - at Ombudsman eligibility opening;
  - at 60, 30, 14 and 3 days before the Ombudsman limitation date;
  - at the expected insurer response date ("Did the insurer reply? Log it").

  Each reminder deep-links to the next action.
- **Business rules:**
  - Email reminders are sent only with consent (b) (FR-005) and a verified email.
  - Each reminder is sent at most once.
  - Reminders stop when the case is closed.
  - Sending is idempotent across job retries.
  - Reminder content includes no medical details. It contains the case nickname and the action only.
- **Failure:** a failed email send is retried up to 3 times over 6 hours. After that the reminder shows in-app as "Email failed".
- **Calendar export (P1):** an "Add to calendar" action downloads an `.ics` file of the case's active deadlines. Events contain only the case nickname and the action. This is a ₹0 reminder channel that keeps working after the email credits end (D-005).
- **Acceptance criteria:**
  - AC1: the scheduler sends each due reminder exactly once (duplicate-run test).
  - AC2: no reminder body contains diagnosis, hospital or amount fields.
  - AC3: M-06 is measurable from logs.
- **Priority:** P0 (email and in-app).

#### FR-023: Log case events
- **Behaviour.** The user logs:

  | Event key | Meaning |
  |---|---|
  | `s1_sent` | Stage 1 letter sent (date, method: email / post / insurer portal) |
  | `insurer_reply` | Insurer replied (date, upload, satisfied: yes / no) |
  | `s2_filed` | Filed on Bima Bharosa (date, token number) |
  | `s3_filed` | Filed with the Ombudsman (date, reference) |
  | `ombudsman_outcome` | Ombudsman outcome |
  | `payment_received` | Payment received (amount) |
  | `closed` | Case closed |

  Events drive stage transitions and deadlines.
- **Business rules:**
  - Event dates cannot be in the future, or before the decision letter date.
  - Logging an insurer reply prompts the user to upload it and re-run analysis, with the reply treated as the new current decision.
- **Acceptance criteria:**
  - AC1: invalid dates are rejected with a message.
  - AC2: `s1_sent` starts the RULE-ESC-02 clock.
  - AC3: the timeline view shows all events in order.
- **Priority:** P0.

---

### E. Complaint packs and letters

#### FR-024: Stage 1 grievance letter
- **Story:** As Meena, I want a complete letter to the insurer's grievance officer that I can send today.
- **Behaviour:** the letter is generated from a **fixed skeleton**. The model fills only the grounds paragraphs, and every ground carries its citation IDs.

  1. Complainant details. Filled **server-side** from confirmed fields; the model sees placeholders only.
  2. Policy, claim and decision references.
  3. Subject line.
  4. Facts, built deterministically from confirmed fields.
  5. **Grounds.** One numbered paragraph per surviving counter-point (FR-016) and per `NO_CLAUSE_CITED` group (FR-015).
  6. **Specific requests:**
     - (a) reconsider and pay ₹X, taken from the disputed lines the user selected;
     - (b) provide the specific policy terms relied on for each disallowance (Para 17(b));
     - (c) for repudiations, confirm Claims Review Committee approval (Para 17(a));
     - (d) respond in writing.
  7. Enclosures, taken from uploaded documents and the checklist.
  8. Sign-off for the complainant.

  The user selects which disputed items to include. `APPEARS_VALID` items are unselected by default, with an explanation.
- **Letter language:** English, Gujarati or Hindi, chosen per letter. An **English parallel copy is always generated**, and the export includes both when the language is not English (OQ-03).
- **Business rules:**
  - Quoted policy or regulation text is kept in its original language, inside quotation marks, followed by a labelled translation.
  - Tone is fixed as firm and polite. No tone picker in the MVP.
  - Every output carries the self-help disclaimer in the footer.
- **Acceptance criteria:**
  - AC1: the letter contains no amount, date or clause number absent from confirmed fields or cited chunks (verifier AI-005).
  - AC2: each grounds paragraph has at least one verified citation, or a deterministic rule source.
  - AC3: placeholders are filled server-side, and the model request log contains no complainant name, phone or address.
- **Priority:** P0.

#### FR-025: Stage 2 Bima Bharosa complaint content
- **Behaviour:** generates copy-ready content for the Bima Bharosa complaint:
  - complaint summary;
  - reference numbers;
  - amounts;
  - a short grounds summary, reusing verified grounds.

  Each item has a "Copy" button. The app shows a link to the official portal and its toll-free number, and states that filing is free.
- **Business rules:**
  - Field length limits come from the rules table. They are initially **unknown** (OQ-04). Until they are set, the app shows the character count without truncating.
- **Acceptance criteria:**
  - AC1: content reuses only verified grounds.
  - AC2: copy actions work on mobile browsers.
- **Priority:** P1.

#### FR-026: Stage 3 Ombudsman complaint pack
- **Behaviour:** after FR-020 checks pass, generates:
  1. the complaint letter, using the same skeleton as FR-024 plus a history of the insurer grievance with dates;
  2. copy-ready fields matching the CIO complaint form (field list in OQ-02);
  3. an enclosure checklist that includes the S1 letter, the insurer reply or a statement of no reply, and the decision letter;
  4. instructions for filing online, by email or by post, and a note that filing is free [S50].
- **Business rules:** the pack identifies the complainant as the signatory, and helpers are told this explicitly (RULE-ESC-06).
- **Acceptance criteria:**
  - AC1: generation is impossible while any Block rule fails.
  - AC2: the grievance history dates match logged events exactly.
- **Priority:** P0.

#### FR-027: Edit letters while preserving citations
- **Behaviour:** a rich-text editor.
  - Cited quotes appear as protected spans with a citation badge.
  - Editing inside a protected span converts it to plain text and removes the badge, with the warning "This is no longer a verified quote".
  - Free text can be added anywhere.
- **Business rules:**
  - The exported letter preserves badges as footnotes.
  - User-added text is not verified and is not labelled as a citation.
- **Acceptance criteria:**
  - AC1: an edited quote loses verified status in both the UI and the export.
  - AC2: undo restores the verified span.
  - AC3: autosave runs every 10 seconds and on blur.
- **Priority:** P0.

#### FR-028: Export
- **Behaviour:**
  - Export as PDF and as DOCX.
  - A4 page size.
  - Fonts that render Gujarati and Devanagari correctly.
  - Footnotes list each citation with its source title, version, clause or paragraph, and quote.
  - A "Copy as email text" option.
- **Business rules:** export is blocked while the letter is **stale** (FR-011).
- **Acceptance criteria:**
  - AC1: Gujarati and Hindi PDFs render without missing glyphs (visual regression on fixtures).
  - AC2: DOCX opens in Word and LibreOffice with footnotes intact.
  - AC3: the export event is logged.
- **Priority:** P0.

#### FR-029: Source viewer
- **Behaviour:** tapping any citation opens a panel showing:
  - the source title;
  - the version or effective date;
  - the clause or paragraph identifier;
  - the full chunk text with the quoted span highlighted;
  - for user documents, the page image region.
- **Acceptance criteria:**
  - AC1: every citation opens a viewer whose highlighted span equals the quote.
  - AC2: the viewer works offline for already-loaded content (PROVISIONAL; drop if costly).
- **Priority:** P0.

---

### F. Data controls

#### FR-030: Export my data
- **Behaviour:** the user downloads a ZIP for a case or the whole account. It contains original files, extracted fields (JSON), the analysis, letters, the event timeline and consent records.
- **Acceptance criteria:** AC1: the ZIP is generated within 5 minutes for a 25-file case, and a link is emailed or shown, valid for 24 hours.
- **Priority:** P0.

#### FR-031: Delete a case
- **Behaviour:** typed confirmation, then hard deletion of:
  - files in storage;
  - database rows, including extracted fields, analyses, letters and embeddings of user wording;
  - queued jobs.

  Audit logs keep only `case deleted, id, timestamp`, with no content.
- **Acceptance criteria:**
  - AC1: storage objects and rows are gone within 24 hours (verified by an integration test).
  - AC2: backups are purged on their rotation, ≤ 35 days (NFR-007).
- **Priority:** P0.

#### FR-032: Delete account
- **Behaviour:** deletes all cases (as FR-031), consents, sessions and the user record. The email is kept as a one-way hash for 30 days to rate-limit abuse, then removed.
- **Acceptance criteria:**
  - AC1: after deletion, signing in with the same number creates a fresh, empty account.
  - AC2: the deletion confirmation is emailed or shown.
- **Priority:** P0.

#### FR-033: Automatic retention
- **Behaviour:**

  | Situation | Action |
  |---|---|
  | Source files of a **closed** case | Deleted 90 days after closure. The user can extend once by 90 days. |
  | **Open** case with no activity for 18 months | Notify the user; delete after 30 more days unless they act |

  These periods are PROVISIONAL and subject to legal review.
- **Acceptance criteria:** AC1: the retention job deletes the eligible fixtures and leaves the others.
- **Priority:** P0.

---

### G. Feedback and outcomes

#### FR-034: Outcome and rating capture
- **Behaviour:**
  - On `closed` or `payment_received`, ask for the outcome (paid in full / partly / not paid / withdrawn), the amount received (optional), and a 1–5 trust rating with optional comment.
  - At Stage 3, also ask whether the complaint was accepted or dismissed as non-entertainable (for M-07).
- **Acceptance criteria:** AC1: all answers are optional and skippable, and are stored for metrics M-07 to M-09.
- **Priority:** P0.

#### FR-035: Report a problem with an output
- **Behaviour:** a "Something's wrong" control on each counter-point, citation and letter paragraph. The user chooses a reason (wrong fact / wrong rule / bad translation / other) and may add a comment.
- **Business rules:**
  - The report creates a review item (FR-040) containing **only** the flagged output and its citations.
  - Reviewers see document content only if the user ticks "allow reviewer to see this case" (FR-042).
- **Acceptance criteria:** AC1: the report appears in the review queue within 1 minute.
- **Priority:** P0.

---

### H. Settings

#### FR-036: Settings
- **Behaviour:** the user can manage:
  - display language;
  - email address, with verification by a link;
  - reminder consent on or off;
  - large-text mode;
  - sign out everywhere;
  - export data;
  - delete account;
  - view consent history.
- **Acceptance criteria:** AC1: each setting persists and takes effect immediately.
- **Priority:** P0.

---

### I. Administration

#### FR-037: Admin authentication and roles
- **Behaviour:**
  - A separate admin sign-in with mandatory TOTP-based MFA.
  - Roles are `admin` and `reviewer`.
  - Every admin action is written to the audit log.
- **Acceptance criteria:**
  - AC1: admin routes reject consumer sessions.
  - AC2: sign-in fails without MFA.
- **Priority:** P0.

#### FR-038: Knowledge base management
- **Behaviour.** The admin uploads sources and records their metadata:
  - type: `regulation` / `policy_wording` / `glossary`;
  - issuer;
  - title;
  - identifier (for example the circular number, or the product UIN);
  - version;
  - effective from and to;
  - source URL;
  - date retrieved.

  The system chunks by clause or paragraph, keeping clause identifiers, and indexes for retrieval. Sources can be retired without being deleted, so past cases stay reproducible.
- **Launch corpus** (minimum):

  | Source | Status |
  |---|---|
  | IRDAI Master Circular on Health Insurance Business, 29 May 2024 [S45] | Confirmed |
  | Insurance Ombudsman Rules 2017, as amended to 9 November 2023 [S47] | Confirmed |
  | IRDAI policyholder-protection regulations and circulars currently in force | VERIFY-PRIMARY, OQ-05 |
  | Wordings for the top N retail health products, N = 10 (PROVISIONAL) | Selection in OQ-08 |

  **Excluded:** Ombudsman awards [S49].
- **Business rules:**
  - Publishing a source requires the admin to confirm "text checked against the official PDF".
  - Each chunk stores the source version, so analyses keep pointing to the exact version used.
- **Acceptance criteria:**
  - AC1: retiring a version does not alter citations in existing letters.
  - AC2: each chunk has a non-empty clause or paragraph identifier, or is flagged.
- **Priority:** P0.

#### FR-039: Rules table management
- **Behaviour:** the admin can create, edit and version:
  - the RULE-ESC and RULE-MC rules;
  - deadline parameters;
  - clause-identifier patterns;
  - category-to-evidence mappings;
  - field limits;
  - banned phrases.

  Each rule has an ID, parameters, effective dates, source citation, status (`enabled` / `disabled_pending_verification`) and the name of the person who verified it.
- **Business rules:**
  - A rule cannot be enabled without a source citation and a verifier name.
  - Changes create a new version. Existing cases keep their rule version until the user re-runs the checks.
- **Acceptance criteria:**
  - AC1: enabling without a source fails.
  - AC2: case records show the rule versions applied.
- **Priority:** P0.

#### FR-040: Review queue
- **Behaviour:** a queue of:
  - user reports (FR-035);
  - verifier rejections (AI-004);
  - abstentions above a rate threshold;
  - random audit samples for M-04.

  Reviewers mark each item correct, incorrect (with category) or needs knowledge-base fix.
- **Acceptance criteria:** AC1: monthly audit sampling selects 100 citations at random (PROVISIONAL size) across languages.
- **Priority:** P0.

#### FR-041: Metrics dashboard
- **Behaviour:** aggregate charts for the funnel (Section 7), AI quality metrics, cost per case and reminder delivery. No individual case content is shown.
- **Acceptance criteria:** AC1: every metric M-01 to M-11 is visible.
- **Priority:** P1.

#### FR-042: Support access by user grant
- **Behaviour:** the user can grant reviewer access to one case for 7 days, and revoke it at any time. Without a grant, admins and reviewers cannot open documents or case content.
- **Acceptance criteria:**
  - AC1: an access attempt without a grant returns 403 and is logged.
  - AC2: access expires automatically.
- **Priority:** P0.

---

### J. Public site

#### FR-043: Landing, information and trust pages
- **Behaviour:** pages in all three languages:
  - home (value proposition and scope);
  - how it works;
  - what we don't do;
  - privacy notice;
  - terms;
  - **accuracy page**, publishing the latest M-04 audit result and its date once at least one audit exists;
  - contact or grievance officer.
- **Business rules:**
  - No claims of success rates until M-08 has enough data.
  - No testimonials invented or seeded.
- **Acceptance criteria:**
  - AC1: Lighthouse accessibility score ≥ 95 on each page (PROVISIONAL).
  - AC2: no statistic appears without a source link.
- **Priority:** P0.

#### FR-044: Official free channels notice
- **Behaviour:** a persistent help link listing the insurer's grievance officer step, the Bima Bharosa portal and toll-free number, and the CIO complaint portal, with the statement that these are free.
  - It also warns users never to pay anyone claiming to be the Ombudsman [S50].
- **Acceptance criteria:** AC1: the notice is reachable from every case screen in at most 1 tap.
- **Priority:** P0.

---

### 4.K Logical data model (minimum fields)

| Entity | Key fields |
|---|---|
| User | id, email (verified), google_subject?, display_language, large_text, created_at, deleted_at |
| Consent | id, user_id, version, purposes[], granted_at, withdrawn_at, language |
| Case | id, user_id, nickname, complainant_name*, complainant_relation, patient_name*, insurer_id, policy_type, mode (`full`/`limited`/`delay`), stage, status, wording_source_id, rule_versions{}, eligibility_answers{}, stale (bool), closed_at |
| Document | id, case_id, type, storage_key, sha256, pages, ocr_status, ocr_quality |
| ExtractedField | id, case_id, name, extracted_value, value, confidence, source_ref, confirmed_by_user |
| LineItem | id, case_id, description, billed, deducted, reason_verbatim, clause_cited_verbatim, category, audit_status, user_entered |
| KnowledgeSource | id, type, issuer, title, identifier, version, effective_from, effective_to, url, retrieved_at, status |
| KnowledgeChunk | id, source_id, clause_ref, text, language, embedding, case_id (null unless user wording) |
| Rule | id, rule_key, version, params{}, effective_from, source_ref, status, verified_by |
| Analysis | id, case_id, model_versions{}, prompt_versions{}, summary_i18n{}, counter_points[] (statement, basis_type, citations[{chunk_id, quote}], verified), created_at |
| Letter | id, case_id, stage, language, body, english_body, citations[], verified_at, stale, exported_at |
| Deadline | id, case_id, kind, due_date, rule_id/version, reminders_sent[] |
| CaseEvent | id, case_id, kind, event_date, metadata{} |
| ReviewItem | id, source (`user_report`/`verifier`/`audit`), case_id, payload, status, reviewer_id |
| AuditLog | id, actor, action, entity, entity_id, created_at (no content) |

Fields marked * are encrypted at the application level (NFR-005).

---

## 5. AI-specific requirements

#### AI-001: Where AI is and is not used

| Function | AI? | Why |
|---|---|---|
| OCR on images and scans | Yes (OCR engine) | Unstructured photos and scans |
| Field and line-item extraction | Yes (LLM, structured output) | Insurer letter formats vary widely |
| Reason classification | Yes | Free-text reasons |
| Counter-point drafting over retrieved chunks | Yes | Needs reasoning over clauses |
| Explanation, letter grounds, translation | Yes | Language generation |
| `NO_CLAUSE_CITED`, deadlines, Rule 14 checks, moratorium rule, amounts and dates in letters, citation verification | **No, deterministic code** | Must be exact and auditable |

#### AI-002: Input handling and data minimisation
- All document text is passed to models as **data** inside delimited blocks, with instructions that it is untrusted (prompt-injection defence).
- Before any model call, the following are replaced with typed placeholders such as `{{PATIENT_NAME}}`:
  - names, phone numbers, emails and addresses;
  - Aadhaar-pattern and PAN-pattern numbers;
  - policy, claim and member IDs.
- Medical content needed for reasoning (diagnosis, procedure) is sent under consent (a).
- Placeholders are re-filled server-side only in final rendered output.

#### AI-003: Structured outputs
- Every model call returns JSON validated against a versioned schema. Invalid JSON is retried once with a validation error message, then treated as a failure (AI-008).
- Minimum schemas:
  - `ExtractionResult{fields[{name, value|null, confidence 0–1, source:{doc_id,page,bbox}}]}`
  - `LineItems{items[{description, billed|null, deducted, reason_verbatim, clause_cited_verbatim|null, source}]}`
  - `Classification{target_id, category, confidence}`
  - `CounterPoints{reason_id, points[{statement, basis_type, citations[{chunk_id, quote}], applies_if|null}], abstain:boolean, abstain_reason|null}`
  - `LetterGrounds{paragraphs[{text, citation_refs[]}]}`
  - `Translation{text, glossary_terms_used[]}`

#### AI-004: Citation requirements and verifier
- Every `policy_wording` or `regulation` statement must carry at least one `{chunk_id, quote}`.
- The verifier (deterministic code) checks:
  1. The chunk ID exists **and** was among the chunks retrieved for this call.
  2. The quote appears in the chunk text after normalisation: Unicode NFC, collapsed whitespace, unified quotes and dashes, case-insensitive for Latin script only.
  3. Quote length is at least 8 words or 40 characters (PROVISIONAL), to stop trivial matches.
- Any failure removes the point or paragraph and logs it to the review queue.
- Quotes always stay in the source language. A translation is shown separately and labelled as a translation.

#### AI-005: No ungrounded facts
- Every amount, date, percentage, clause identifier and regulation identifier in generated text must equal a confirmed field value or appear in a cited chunk.
- A post-generation scanner extracts numeric and identifier tokens in all three scripts (including Gujarati and Devanagari numerals) and checks them.
- Sentences that fail are removed and logged.

#### AI-006: Confidence, uncertainty and abstention
- **Extraction fields** with confidence below 0.80 (PROVISIONAL) are highlighted for user review. Required fields are never auto-accepted.
- **OCR page quality** (mean character confidence) below 0.70 (PROVISIONAL) gives `needs_attention`.
- **Classification** confidence below 0.70 (PROVISIONAL) gives `other_unknown` and asks the user.
- **Counter-points:** the model must set `abstain=true` when retrieved chunks do not address the reason. Abstentions show FR-019 states.
- **No numeric "case strength" or win probability** is shown anywhere in the MVP.
- All thresholds are tuned on the gold set before release and recorded in the rules table.

#### AI-007: Human approval of consequential actions
- The user must confirm the extracted facts (FR-011) before analysis.
- The user must review the letter and press "I've read this letter" before the first export of each version.
- The system **never** sends letters or files complaints.
- Knowledge-base and rule changes require admin confirmation (FR-038, FR-039).

#### AI-008: Failure and fallback
| Failure | Behaviour |
|---|---|
| Provider timeout or 5xx error | Retry with exponential backoff, up to 3 attempts. Then switch to the secondary provider if configured (OQ-01). Otherwise the job is `failed_retryable`, the user sees "Taking longer than usual, we'll notify you", and an auto-retry runs in 15 minutes. |
| Schema-invalid output twice | Fail the step. Show FR-019 with "type the reason yourself" or retry. |
| All counter-points fail verification | Show no counter-points (FR-016 empty state). The letter still includes the deterministic grounds: Para 17(b) request, Claims Review Committee confirmation request, and the moratorium rule if it fired. |
| Translation failure | Show English with the message "Gujarati/Hindi version unavailable right now, retry". Never show a partial translation. |
| Provider outage longer than 1 hour | Uploads and confirmation continue. Analysis jobs queue and no work is lost (NFR-010). |

#### AI-009: Translation
- Translations use a maintained glossary of insurance and legal terms in `en`, `gu` and `hi`.
- Regulator, scheme and form names stay in their official form, with a translation in parentheses.
- Native-speaker review is required for all fixed templates and a sample of generated outputs before release (NFR-021).

#### AI-010: Prompt-injection and misuse defences
- Instructions found inside documents are ignored and logged.
- Requests outside the scope (health insurance claims in India) return an out-of-scope message.
- There is no free-form chat in the MVP.

#### AI-011: Versioning and reproducibility
- Model IDs, prompt versions, retrieval parameters, knowledge-base source versions and rule versions are stored with every analysis and letter.
- Re-running an analysis creates a new record. The old one is kept until the case is deleted.

#### AI-012: Evaluation metrics and acceptable error levels (ALL PROVISIONAL until the first benchmark)

| Metric | Definition | Provisional release threshold |
|---|---|---|
| Field extraction accuracy | Exact match after normalisation, per required field | ≥ 95% on printed PDFs; ≥ 85% on phone photos |
| Line-item recall | Deduction lines found / lines in ground truth | ≥ 90% |
| Classification macro-F1 | Across the FR-013 taxonomy | ≥ 0.80 |
| Citation verifier pass rate | Generated citations that pass AI-004 (a quality signal; failures are hidden from users) | ≥ 90% |
| Citation precision (human) | Shown citations that exist and support the sentence | ≥ 98% |
| Unsupported-sentence rate | Shown sentences judged unsupported by a reviewer | ≤ 1% |
| Deterministic rules | Rule 14, deadlines, `NO_CLAUSE_CITED` | **100%** on the test suite (not provisional) |
| Translation adequacy | Native reviewer score of 4 or more out of 5 on a sample | ≥ 90% of samples |
| Abstention appropriateness | Abstained when no grounded point exists | Measured; target set after baseline |

#### AI-013: Evaluation process
- **Gold set:** at least 100 anonymised real cases, gathered with explicit research consent, including at least 20 Gujarati-context and at least 20 Hindi-context cases (PROVISIONAL composition). Until enough real cases exist, synthetic fixtures may supplement them but are reported separately.
- **When it runs:** on every prompt, model, retrieval or knowledge-base change, in CI or as a pre-release job.
- **Release gate:** a release that misses an AI-012 threshold is blocked.

#### AI-014: No training on user data
- User documents and outputs are never used for model training or fine-tuning.
- Provider contracts must guarantee no training and minimal retention (OQ-01).

#### AI-015: Provider requirements
- The provider must offer a data-processing agreement, a no-training commitment, and documented retention (zero, or 30 days or less, PROVISIONAL).
- An India region is preferred where available (OQ-01).
- A provider-abstraction layer must allow switching without product changes.

---

## 6. Non-functional requirements

All numeric targets are PROVISIONAL unless stated otherwise.

### Performance

| ID | Requirement |
|---|---|
| NFR-001 | OCR and extraction of a 20-page case complete in ≤ 90 seconds at p90. |
| NFR-002 | Analysis after confirmation completes in ≤ 60 seconds at p90. Letter generation completes in ≤ 45 seconds at p90, including translation. |
| NFR-003 | On a mid-range Android phone on Slow 4G, Largest Contentful Paint is ≤ 3.0 s on landing and case pages for a **warm** service. Interaction responses are ≤ 200 ms for non-AI actions. Under ₹0 hosting (scale to zero), the first request after idle has a cold start; it is measured and reported separately, with no target in the MVP. |

### Security and privacy

| ID | Requirement |
|---|---|
| NFR-004 | TLS 1.2 or higher everywhere. HSTS. No mixed content. |
| NFR-005 | Encryption at rest: AES-256 for storage and the database, plus application-level encryption of identity fields (marked * in 4.K). File access only through signed URLs that expire in 15 minutes or less. |
| NFR-006 | OWASP ASVS Level 2 controls verified before launch. Rate limiting on auth and upload endpoints. Malware scanning of uploads. CSRF protection. Strict Content Security Policy. |
| NFR-007 | Backups: a daily encrypted database dump, kept 7 days online, plus a weekly offline copy kept 35 days. The free database tier has no managed backups. Deleted data leaves all backups within 35 days. RPO 24 hours, RTO 8 hours. Uploaded case documents are not backed up (users can re-upload). This is stated in the privacy notice. |
| NFR-008 | DPDP Act 2023 and DPDP Rules 2025 compliance. This covers notice, purpose-limited consent, withdrawal, access, correction, erasure, and the grievance contact. It also requires a breach-response runbook that meets the Rules' notification timelines (to be confirmed by legal, OQ-10). Compliance must be ready by **public launch**, regardless of the phased effective dates [S51, S52]. |
| NFR-009 | Data residency: the database, file storage and backups are hosted in an India region. Data sent to an AI provider is de-identified per AI-002. Cross-border processing is disclosed in the notice. |

### Reliability and availability

| ID | Requirement |
|---|---|
| NFR-010 | No accepted upload is lost. Jobs are durable and idempotent and survive worker restarts and AI-provider outages. |
| NFR-011 | 99.5% monthly availability for the web app and API, excluding announced maintenance. |

### Accessibility

| ID | Requirement |
|---|---|
| NFR-012 | WCAG 2.2 AA. Full keyboard operability. Screen-reader labels in all three languages. Touch targets of at least 44×44 px. Large-text mode at 1.25× or more. |
| NFR-013 | Readability: English explanations at roughly Grade 8 reading level or below. Gujarati and Hindi reviewed for plain register by native reviewers. |

### Scalability

| ID | Requirement |
|---|---|
| NFR-014 | Handles 2,000 new cases per month and 50 concurrent processing jobs without degrading NFR-001 or NFR-002. Workers scale horizontally. |
| NFR-015 | Per-user and global queue limits stop one user from starving others. |

### Maintainability

| ID | Requirement |
|---|---|
| NFR-016 | Prompts, schemas, rules-table seeds and glossary are kept in version control, with change history. |
| NFR-017 | Automated tests: 100% of deterministic rules (Rule 14, deadlines, `NO_CLAUSE_CITED`, verifier, number scanner); API authorisation tests for every case-scoped endpoint; at least 70% line coverage on the back end. |
| NFR-018 | All user-facing strings sit in translation catalogues. No hard-coded copy. |

### Observability

| ID | Requirement |
|---|---|
| NFR-019 | Structured logs with **no document content or identity fields**. Errors are tracked. LLM traces record prompt and model version, latency, tokens and cost, with payloads redacted or stored only in de-identified form. |
| NFR-020 | Alerts fire on: job failure rate above 5% over 15 minutes; reminder-send failures; a verifier rejection rate above twice the baseline; and a cost per case above the budget threshold. |

### Localisation quality

| ID | Requirement |
|---|---|
| NFR-021 | Release build fails CI if any `gu` or `hi` key is missing. A native reviewer signs off on all templates and fixed copy. |

### Cost

| ID | Requirement |
|---|---|
| NFR-022 | **Hosting costs ₹0 within free tiers (D-005).** AI and OCR cost per completed case is drawn from trial credits: ESTIMATE about ₹10 with Gemini 2.5 Flash, and at most ₹40 (PROVISIONAL). After the credits, it becomes a real cost (OQ-09). |
| NFR-023 | **Free-tier and credit guardrails.** Alert at 80% of any free-tier quota. At 90% of the trial-credit budget, AI features pause with a clear message; deterministic features (rules, deadlines, the basic letter) keep working. The admin is alerted. |

### Compliance copy

| ID | Requirement |
|---|---|
| NFR-024 | The self-help disclaimer appears on every analysis screen and in every exported document, and is reviewed by a lawyer. |

### Browser support

| ID | Requirement |
|---|---|
| NFR-025 | The last two versions of Chrome (Android and desktop), Safari (iOS), Edge and Firefox. |

### Implementation constraints

| ID | Requirement |
|---|---|
| NFR-026 | Stack per `docs/03-architecture/system-design.md` v1.1 (₹0 profile): Next.js + FastAPI on Cloud Run (Mumbai), Supabase Free Postgres with pgvector and Storage (Mumbai), Cloud Tasks, Vertex AI and Document AI (Mumbai), Amazon SES (Mumbai). Changing the stack must not change any requirement in this PRD. |

---

## 7. Product analytics

**Principles:**

- First-party analytics only.
- Events carry **no** document content, names, phone numbers, amounts to the rupee, diagnoses or insurer correspondence.
- Amounts are bucketed (< ₹25k, ₹25k–1L, 1L–5L, 5L–50L, > 50L).
- Analytics is covered by the privacy notice.
- A user can opt out of non-essential analytics in Settings.

### 7.1 Events

| Event | Key properties | Purpose |
|---|---|---|
| `signup_completed` | method (otp / google), language | Acquisition |
| `consent_given` / `consent_withdrawn` | version, purposes | Compliance |
| `case_created` | eligibility branch, policy_type, decision_type | Funnel |
| `document_uploaded` | type, format, pages, is_photo | Funnel, OCR quality |
| `document_needs_attention` | reason | OCR quality |
| `fields_confirmed` | n_fields_edited, n_low_confidence | Activation, extraction quality |
| `analysis_completed` / `analysis_failed` | mode, n_points, n_abstain, duration_ms, failure_type | Quality, reliability |
| `audit_status_counts` | counts per status, amount bucket per status | Validates AS-04 |
| `citation_opened` | basis_type | Trust behaviour |
| `letter_generated` | stage, language | Funnel, AS-02 |
| `letter_edited` | n_verified_spans_broken | Quality |
| `letter_exported` | stage, format, language | Pack completion |
| `stage_block_shown` | rule_id | Validates AS-03 |
| `event_logged` | kind | Escalation progress |
| `reminder_sent` / `reminder_failed` / `reminder_clicked` | kind, channel | G-4 |
| `output_reported` | reason | Quality |
| `outcome_recorded` | outcome, amount_bucket, stage_reached, non_entertainable | Impact |
| `rating_submitted` | score | Trust |
| `case_deleted` / `account_deleted` | — | Retention, compliance |

### 7.2 Funnels

1. Sign-up → consent → case created → first upload → fields confirmed → analysis completed → letter exported (S1).
2. S1 exported → `s1_sent` logged → insurer reply logged → S3 pack generated → `s3_filed` → outcome recorded.

### 7.3 Retention indicators

- **Case return rate:** users who return within 45 days of `s1_sent` to log a reply. This is the key engagement signal, because the product is used episodically.
- **Reminder click-through rate.**
- Daily or monthly active users are **not** a target metric. Repeat use is not expected.

### 7.4 Impact measures

- Self-reported outcome distribution (M-08).
- Self-reported amount recovered, bucketed.
- Ombudsman non-entertainable rate (M-07).
- Share of disputed amount that had `NO_CLAUSE_CITED`.

All of these are self-reported and will be presented as such.

---

## 8. User journeys and edge cases

**J1: First use, partial disallowance, Gujarati (happy path; P2-like user)**

1. Opens the link and picks ગુજરાતી.
2. Signs in with Google (one tap).
3. Reads the consent notice in Gujarati and accepts processing and reminders.
4. Eligibility: health / partly paid / family floater / self / not in court.
5. Photographs the settlement letter (3 pages) and the final bill. Uploads the policy wording PDF; the password prompt appears and is satisfied.
6. Reviews the extracted fields. The first inception date is highlighted as low-confidence, so she corrects it from the policy schedule, then confirms.
7. Sees the line items: 9 deductions, 6 marked `NO_CLAUSE_CITED` (₹38,400) and 1 `CLAUSE_FOUND_QUESTIONABLE`. She taps a citation and sees the highlighted Para 17(b) text in English with a Gujarati translation.
8. Reads the 150-word Gujarati explanation and the evidence checklist.
9. Generates the Stage 1 letter in Gujarati (an English copy is included), reads it, confirms, and exports a PDF.
10. Logs "sent by email today". Ombudsman eligibility (+1 month) and the limitation date appear on the timeline.

**J2: Rejection escalated to the Ombudsman**

Starts like J1 with a repudiation for `non_disclosure`.

- The moratorium rule fires (first inception 74 months before admission).
- She logs S1 sent. After 1 month without a reply, she receives a reminder email.
- Runs the S3 checks: all pass. Generates the Ombudsman pack and files it on the CIO portal herself.
- Logs `s3_filed`. Three months later she logs the outcome and rates the case.

**J3: Missing information (no policy wording)**

- The user has only the decision letter, and no library match exists, so the case enters **limited mode**.
- An explanation says what is missing.
- The checklist asks for the policy wording (usually in the welcome kit or on the insurer's website).
- The letter includes Para 17(b) and Claims Review Committee requests.
- Uploading the wording later marks the analysis stale and offers a re-run.

**J4: Validation errors**

| Problem | What happens |
|---|---|
| File over 20 MB | Client-side message with tips to compress or use the camera |
| HEIC photo | Rejected with a message to use the in-app camera |
| Unreadable photo | `needs_attention` with retake guidance |
| Line items don't add up | Warning shown; the user may proceed |
| Event date in the future | Rejected inline |

**J5: Cancellation and resume**

- The user closes the browser mid-review. On return, the case shows "Continue checking details". Nothing is lost (autosave).
- The user deletes the case mid-process: queued jobs are cancelled and FR-031 runs.

**J6: Failed AI call**

- The analysis provider is down: the user sees "Taking longer than usual, we'll email you when ready", and the job retries.
- If all retries fail within 2 hours (PROVISIONAL), the in-app status becomes "Couldn't complete: tap to retry" and the user is notified.
- Deterministic grounds are still available, so a basic Stage 1 letter can be generated (AI-008).

**J7: Recovery and new device**

- The user signs in on a new phone with Google or an email code and sees all their cases.
- If the user lost the number: there is no recovery in the MVP. Support guidance is to sign in with the linked Google account if one exists (risk R-14).

**J8: Account deletion**

Settings → Delete account → typed confirmation → everything is deleted as in FR-032 → confirmation is shown. Signing in again creates an empty account.

**J9: Out of time**

- The decision letter date is more than 1 year ago and no representation was made.
- S1 is still allowed: write to the insurer now.
- At S3, RULE-ESC-03 warns that the complaint is late and the Ombudsman may decline, which may be condoned under Rule 14(4).
- No block, but it is clearly flagged.

**J10: Parallel litigation**

- The user answered "yes, consumer case filed".
- S3 is blocked under RULE-ESC-04 with an explanation. S1 remains available.

**J11: Helper preparing for a parent (P3)**

- Relationship is set to "son".
- Letters name the father as the complainant and the signatory.
- The S3 pack instructs: "Your father must sign and file this complaint" (RULE-ESC-06).

**J12: Insurer reply arrives**

- The user logs a reply and uploads it. It becomes the new current decision.
- If it is a partial reversal, amounts are re-confirmed and a fresh analysis runs. Remaining disputed items carry into the S3 pack.

---

## 9. Risks and assumptions

### 9.1 Risk register

| ID | Risk | Likelihood | Impact | Mitigation | Owner (role) | Validation method |
|---|---|---|---|---|---|---|
| R-01 | Competitors already deliver accurate, procedurally correct output, so there is no differentiation | Medium | **Fatal** | Kill gate at week 1 (Section 10.1) | Product owner | Competitor teardown benchmark |
| R-02 | Wrong citation or rule shown to a user, harming their case | Medium | High | AI-004 and AI-005 verifiers; deterministic rules; human audit (M-04); report button | Tech lead | Gold-set evaluation; monthly audit |
| R-03 | Treated as unauthorised legal practice | Low–Medium (U) | High | Self-help positioning; user always files; no representation; disclaimers; legal opinion before launch | Product owner + legal counsel | Written legal opinion |
| R-04 | Medical data breach | Low | High | NFR-004 to NFR-009; de-identification; minimal retention; pre-launch security review | Tech lead | Security review / penetration test |
| R-05 | DPDP obligations apply earlier than planned (Nov 2026) | Medium | Medium | Comply fully at launch (NFR-008) | Product owner | Legal check of notified timeline (OQ-10) |
| R-06 | Gujarati and Hindi demand is weak | Medium | High (differentiator) | Smoke test; M-10 tracking | Product owner | Interviews; landing-page split test |
| R-07 | Policy wordings hard to collect or version | High | Medium | Limited mode; prefer the user's upload; start with N = 10 | Admin | Data-collection spike |
| R-08 | Poor OCR on phone photos of Indic text | Medium | Medium | Retake guidance; mandatory field confirmation; possible cloud OCR | Tech lead | OCR spike on 20 real images |
| R-09 | Deadline rules misinterpreted ("one month", start date) | Low–Medium | High | Rules table with legal sign-off; fixture tests | Product owner + legal | Legal review of RULE-ESC set |
| R-10 | No sustainable funding for a free product | High | High | Cost caps (NFR-022, NFR-023); explore grants, CSR, later B2B | Product owner | Willingness-to-pay and funder conversations |
| R-11 | Users mistrust an unknown site with medical documents | Medium | High | Accuracy page, clear privacy notice, no success fee, official-channel links | Product owner | Concierge pilot upload rates |
| R-12 | Prompt injection through uploaded documents | Low | Medium | AI-002 and AI-010; structured outputs; verifiers | Tech lead | Red-team fixtures in gold set |
| R-13 | Regulatory change (draft Ombudsman amendment 2025, new circulars) | Medium | Medium | Versioned rules and knowledge base; quarterly review | Admin | Quarterly regulatory check |
| R-14 | Lost access to the email or Google account locks the user out | Low | Medium | Both sign-in methods map to the same email; session revocation; support guidance | Tech lead | Support log review |
| R-15 | Code emails land in spam or are undelivered | Medium | Medium | Google sign-in as primary; SES production access; SPF/DKIM once a domain exists | Tech lead | Delivery test to Gmail, Outlook and Yahoo before beta |
| R-17 | Free-tier limits or trial expiry interrupt the beta (storage 1 GB, DB 500 MB, credits for 90 days; GCP project deleted 30 days after the trial closes unless billing is upgraded) | Medium | High | Quota alerts, credit guard, upload caps, retention; upgrade decision by trial day 75 | Product owner | Weekly quota report |
| R-18 | Free database pauses after a week of low activity | Low | Medium | A scheduled job queries the DB every 5 minutes; alert if unreachable | Tech lead | Pause drill in staging |
| R-16 | Bad actors use the brand to charge users (lookalike scams) | Low–Medium | Medium | Clear "we never charge" messaging; official-channel notice | Product owner | Brand monitoring |

### 9.2 Assumptions

See Section 15. None of them is to be treated as fact.

---

## 10. Release criteria

### 10.1 Pre-build gate (validation sprint, from research Section 11)

Implementation may start only when all of these hold:

- [ ] **Competitor teardown** on 10 real cases is complete, and **does not** show the best competitor at ≥ 90% citation correctness with correct procedure in ≥ 8 of 10 cases.
- [ ] **15–20 interviews** are complete, and their pass criteria are met.
- [ ] **Legal opinion** has been received, with no blocking issue.
- [ ] **OCR and data spikes** are done.

If the gate fails, this PRD is archived, as the research recommended.

### 10.2 MVP release to external users (closed beta)

- [ ] All P0 requirements are implemented, and their acceptance criteria pass in automated or documented manual tests.
- [ ] AI-012 thresholds are met on the gold set, with actual thresholds recorded (replacing PROVISIONAL values).
- [ ] Deterministic rule suites pass at 100%. All enabled rules have a source and a verifier name. No VERIFY-PRIMARY rule is enabled.
- [ ] The citation verifier blocks 100% of seeded fake citations in a red-team fixture set.
- [ ] Security review done to OWASP ASVS L2. No open high or critical findings.
- [ ] DPDP notice, consent, deletion and breach runbook reviewed by a lawyer. Disclaimers reviewed by a lawyer.
- [ ] Gujarati and Hindi: CI shows no missing keys; native-reviewer sign-off on templates; Gujarati and Devanagari PDF rendering verified.
- [ ] Accessibility audit: WCAG 2.2 AA, with no blocking issues.
- [ ] India-region hosting confirmed. AI-provider data-processing agreement signed (OQ-01).
- [ ] Monitoring, alerts and budget cap are active.
- [ ] Backup restore tested once.

### 10.3 Public launch

- [ ] Closed beta has run for at least 4 weeks with at least 30 real cases (PROVISIONAL).
- [ ] M-04 ≥ 98% in at least one full monthly audit.
- [ ] M-05 = 0.
- [ ] No open severity-1 issues.
- [ ] The accuracy page publishes the latest audit result.

---

## 11. Requirements traceability

| Requirement(s) | Goal | Evidence or decision | Verified by |
|---|---|---|---|
| FR-001 to FR-003 | G-5 | D-005/D-006: ₹0 sign-in (Google + email code) for Android-first users | FR-001 to FR-003 acceptance criteria; auth tests |
| FR-004, AI-009, NFR-021 | G-1 | D-002; no Gujarati competitor [S1–S5] | NFR-021 CI; native review |
| FR-005, FR-030 to FR-033, NFR-008 | G-5 | DPDP Rules [S51, S52] | Legal review; deletion integration tests |
| FR-006, FR-020 (RULE-ESC-04) | G-2 | Ombudsman Rule 14(5) [S47] | Rule unit tests |
| FR-007 to FR-011 | G-1, G-3 | Grounding requires confirmed facts | FR-011 AC1 to AC3 |
| FR-012, FR-015 | G-1, G-2 | D-004; disallowances ₹15,100 cr [S33]; Para 17(b) [S45] | Gold-set `NO_CLAUSE_CITED` precision 100% |
| FR-013 | G-1 | IRDAI does not collect reasons [S34] | AI-012 macro-F1 |
| FR-014, FR-038 | G-3 | Wording collection risk (R-07) | FR-014 AC1 to AC3 |
| FR-016 | G-1, G-3 | Para 13, 17(a), 17(c) [S45] | FR-016 AC1 to AC3 |
| FR-017, FR-018, FR-019 | G-1 | JTBD-1 | Acceptance criteria; banned-phrase check |
| FR-020 to FR-023, FR-039 | G-2, G-4 | Rule 14 [S47]; 5,047 non-entertainable [S31] | 100% rule suite; M-06, M-07 |
| FR-024 to FR-029, AI-004, AI-005 | G-2, G-3 | Hallucination rates of 17–33% in legal RAG [S21] | Verifier red-team; M-04, M-05 |
| FR-034, FR-035, FR-040 | G-3, impact | Need for outcome baseline | M-04, M-08, M-09 |
| FR-037, FR-042 | G-5 | Health-data sensitivity | 403 tests; audit log |
| FR-043, FR-044 | G-5, trust | CIO "free" advisory [S50]; lookalike scam risk | Content review |
| AI-001 to AI-015 | G-3 | Research Section 6.1 (technical feasibility) | AI-012 and AI-013 |
| NFR-001 to NFR-026 | All | — | Load, security, accessibility and cost checks in Section 10 |

---

## 12. Prioritised MVP backlog

The order reflects dependencies and risk. Epic E0 is not development work.

| Order | Epic | Contents | Size | Notes |
|---|---|---|---|---|
| 0 | **E0 Validation sprint** | Competitor teardown, interviews, legal opinion, OCR and data spikes | — | **Kill gate (10.1)** |
| 1 | E1 Foundations | India hosting on free tiers, auth (FR-001, FR-002, FR-003), i18n framework (NFR-018, NFR-021), audit log, CI | M | Local-first; activate the trial credit only at the AI stage |
| 2 | E2 Rules and knowledge base | FR-038, FR-039; seed the Master Circular, Ombudsman Rules and 10 wordings; rule fixtures | M | Before any analysis |
| 3 | E3 Consent and onboarding | FR-004, FR-005, FR-006, FR-044 | S | Legal copy dependency |
| 4 | E4 Case and documents | FR-007, FR-008, FR-009 | M | |
| 5 | E5 Extraction and confirmation | FR-010, FR-011, FR-012, AI-002, AI-003, AI-006 | L | Gold set started here |
| 6 | E6 Deterministic engine | FR-020, FR-021, FR-015 (deterministic part), AI-005 scanner, AI-004 verifier | M | 100% test suites |
| 7 | E7 AI analysis | FR-013, FR-014, FR-015 (AI part), FR-016, FR-017, FR-018, FR-019, AI-008 | L | |
| 8 | E8 Letters | FR-024, FR-026, FR-027, FR-028, FR-029, AI-009 | L | Gujarati and Devanagari PDF fonts |
| 9 | E9 Tracking and reminders | FR-022, FR-023 | M | |
| 10 | E10 Data controls and settings | FR-030 to FR-033, FR-036 | M | |
| 11 | E11 Admin and quality | FR-037, FR-040, FR-042, FR-034, FR-035; AI-013 evaluation pipeline | M | |
| 12 | E12 Public site | FR-043 | S | |
| 13 | E13 P1 items | FR-025, FR-041, FR-022 calendar export | S | May follow beta start |
| 14 | E14 Hardening | NFR security review, accessibility audit, load test, backup restore, cost alerts | M | Release gate 10.2 |

---

## 13. Open questions requiring product-owner decisions

| ID | Question | Default until decided |
|---|---|---|
| OQ-01 | Which LLM, OCR and embedding providers? Requirements: data-processing agreement, no training, retention, India region, secondary fallback. | Block E5 until decided |
| OQ-02 | What exact fields and format does the CIO Ombudsman complaint form require? | Generic pack (FR-026 items 1, 3, 4) |
| OQ-03 | Do insurers and Ombudsman offices accept complaints written in Gujarati or Hindi? | Always include the English copy |
| OQ-04 | What are the Bima Bharosa field limits? Does a Bima Bharosa complaint count as the Rule 14(3)(a) representation to the insurer? | Show counts; require direct S1 representation |
| OQ-05 | What is the insurer grievance response deadline, and the exact current regulation (policyholder-protection framework, 2024)? | 14 days, labelled VERIFY-PRIMARY |
| OQ-06 | Enable the 36-month PED waiting cap rule? Needs the primary IRDAI instrument and its applicability by policy issue or renewal date. | Disabled |
| OQ-07 | Are employer and group health policies within Ombudsman jurisdiction for the insured employee? | Accept, with a caveat |
| OQ-08 | Which 10 products form the launch wording library? | Top retail products by market share (source to be chosen) |
| OQ-09 | After the trial credit ends (90 days or US$300), upgrade billing and pay about ₹7–10 per case, or pause AI features? | Decide by trial day 75 |
| OQ-10 | Legal: unauthorised-practice risk, DPDP timeline and breach rules, "one month" and "one year" computation, retention periods, disclaimer wording. | Launch-blocking |
| OQ-11 | ~~SMS provider and DLT timeline~~ Resolved by D-006: no SMS in the MVP. | — |
| OQ-12 | Confirm that Supabase Free can create projects in Mumbai (system-design UD-12). | Check first; fallback Cloud SQL on credits |
| OQ-13 | Who is the grievance officer or contact named in the privacy notice? | Product owner |
| OQ-14 | Publish the accuracy page at beta, or only at public launch? | Public launch |
| OQ-15 | Should "delay or pending claim" mode (FR-006) be in the MVP? | In the MVP as a template only |

---

## 14. Not in this PRD

The following are deliberately left to later documents:

- the UI design system and visual design;
- the API endpoint catalogue;
- the infrastructure diagram;
- prompt texts;
- the gold-set annotation guide.

---

## 15. Assumptions that must not be treated as confirmed facts

| ID | Assumption | Validated by |
|---|---|---|
| AS-01 | Existing AI tools (fairClaims, ClaimAssist Pro, ClaimBhai AI, UnDeny) make citation or procedural errors often enough that ClaimSathi's verification and checks matter. | Teardown |
| AS-02 | A meaningful share of affected users prefer Gujarati or Hindi, and would not use an English-only tool. | Interviews, smoke test, M-10 |
| AS-03 | Users don't know the Rule 14 preconditions, and procedural errors cause a meaningful share of non-entertainable dismissals. | Interviews; CIO data if available |
| AS-04 | Partial-settlement letters commonly lack the clause references required by Para 17(b). | Audit of 20–30 real letters |
| AS-05 | Users will upload medical documents to a new, free web tool. | Concierge pilot |
| AS-06 | A free consumer product can be funded sustainably. | Funding conversations |
| AS-07 | A self-help drafting tool with no fee and no representation is legally low-risk in India. | Legal opinion |
| AS-08 | Wordings for 10 top products can be collected and kept current. | Data spike |
| AS-09 | OCR plus user confirmation achieves usable accuracy on phone photos of Gujarati and Hindi letters. | OCR spike; AI-012 |
| AS-10 | Personas P1–P3 represent real users. | Interviews |
| AS-11 | The insurer grievance response period is 14 days (secondary source only). | OQ-05 |
| AS-12 | A Bima Bharosa complaint is optional and is not a precondition for the Ombudsman. This is consistent with Rule 14, which names only the insurer representation. | Legal confirmation (OQ-04, OQ-10) |
| AS-13 | Ombudsman outcomes favour complainants in about 53% of health disposals. This is INFERRED from CIO data and must not be shown to users as a success rate. | — |
| AS-14 | Every PROVISIONAL target in this document (metrics, thresholds, latencies, costs, limits) is a proposal, not a benchmark. | Gold-set run; beta |
