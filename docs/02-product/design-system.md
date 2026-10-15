# ClaimSathi: UI/UX Design System and Experience Specification

| Field | Value |
|---|---|
| Version | 1.1 (₹0 MVP: Google + email-code sign-in, lower upload caps, calendar export) |
| Date | 15 October 2026 |
| Inputs | `docs/01-discovery/competitor-research.md`, `docs/02-product/PRD.md` v1.0 |
| Scope | Every MVP screen in the PRD (FR-001 to FR-044), plus the admin console |
| Status | Specification only. **No design-tool frames have been created.** The design tool connectors in this environment (for example Figma) were not authorised, so this document provides text wireframes and tokens instead of frames. |

### How to read this document

- **PRD references.** References such as `FR-015` point to `PRD.md`. Every screen and component traces to a PRD requirement or to a usability need stated here.
- **PROVISIONAL.** A value marked PROVISIONAL is a proposal and must be confirmed in usability testing.
- **New functionality.** This document adds **no** functionality beyond the PRD. Where the PRD left a UI decision open, this document makes it and records it under "Design decisions" (Section 1.6). Product-level open questions are listed in Section 11.

---

## 1. Experience strategy

### 1.1 Brand personality

**"A calm, sharp-eyed neighbour who reads the fine print with you."**

| Is | Is not |
|---|---|
| Calm, plain-spoken, precise | Alarmist, salesy, "fight the insurer!" aggressive |
| Document-native: feels like well-organised paperwork | A chatbot, or a fintech dashboard |
| Warm and respectful of elders | Childish, cute, emoji-heavy |
| Honest about weak cases (`APPEARS_VALID`) | Optimistic by default |
| Clearly Indian in language and number formats | Decorated with clichéd ornament |

**Voice rules (all three languages):**

- Use short sentences.
- Address the reader in the second person ("you"; in Gujarati and Hindi, the respectful form તમે / आप).
- Use verbs on buttons ("Upload letter", not "Submit").
- Never promise outcomes. "You will win" and similar phrases are banned (PRD FR-017).

### 1.2 Design principles

| # | Principle | What it means in the UI |
|---|---|---|
| P1 | **Show where every fact came from** | Every fact, quote and suggestion carries a provenance tag (Section 7.1). There are no untagged claims. |
| P2 | **One clear next step** | Each screen has exactly one primary action. The case always shows "what to do next" and by when. |
| P3 | **Paper first, then screen** | Letters and source excerpts look like documents (serif, margins, page feel). The app chrome is quiet and sans-serif. |
| P4 | **Language is a first-class layout input** | Layouts are tested with Gujarati and Hindi text, which runs longer and needs taller line-height. Nothing is designed for English and then translated in afterwards. |
| P5 | **Honest states** | No fake progress, no confidence percentages, no "success" before the work exists. Loading, empty, error and partial states are designed with the same care as the happy path. |
| P6 | **Light on the phone** | Assume a 2 GB RAM Android phone on Slow 4G. No decorative imagery or animation that costs bandwidth or attention. |

### 1.3 User needs and key usability challenges

| Challenge (from PRD personas, all HYPOTHESES) | Design response |
|---|---|
| Fear of making a mistake (P2 Meena) | Every step can be undone or edited. Nothing is sent by the app. Reassurance copy at decision points: "Nothing is sent until you send it." |
| English legal jargon | Glossary popovers on terms (FR-017). Quotes shown in English with a labelled translation. |
| Comfortable reading Gujarati but less comfortable typing it | Choices instead of typing: radio cards, segmented date fields, numeric keypads. Typed confirmation uses digits, not words (Section 6.6). |
| Low-end phones, intermittent network | Resumable uploads. "You can leave this page" messaging during processing. A small font budget. |
| Multi-step process spread over months | A persistent case path, deadlines on the case card, and email reminders that deep-link to the exact screen. |
| Helper acting for a parent (P3) | The complainant's name and the signatory are shown prominently on letters and on the Ombudsman pack (RULE-ESC-06). |
| Deductions are opaque (₹ amounts, many lines) | A ledger layout with tabular figures, Indian digit grouping and per-line status badges. |
| Trust in an unknown site with medical documents | A privacy summary before upload, no success-fee messaging, visible links to free official channels (FR-044), and a published accuracy page (FR-043). |

### 1.4 Desired emotional response

| Moment | From | To |
|---|---|---|
| Arrival | Anxious, wronged | "This understands my exact situation." |
| Upload and review | Overwhelmed | "I'm in control; it showed me what it read." |
| Findings | Confused | "Now I know which cuts are questionable, and which aren't." |
| Letter | Intimidated | "This is a proper letter, and I can check every reference." |
| Waiting | Forgetful, worried | "It will remind me. I know the date." |

### 1.5 Visual differentiation from competitors

The research documented competitors' *features and pricing*, not their visual identities, so this document makes **no claims** about how competitors look. A visual audit of fairClaims, ClaimAssist Pro, ClaimBhai AI and UnDeny is recommended (Section 11, DQ-01).

ClaimSathi's distinct visual approach rests on choices that follow from its product position:

1. **A document-native aesthetic.** Warm paper background, ink-coloured text and serif letter previews. This replaces the common SaaS pattern of gradient heroes and chat bubbles.
2. **A provenance colour system.** Five tagged sources of truth (Section 7.1). This is the product's signature UI pattern, because verified citations are its core differentiator (PRD G-3).
3. **Margin-note citations.** Numbered tabs that open the source excerpt with the quoted span highlighted, like a highlighter on paper.
4. **The rupee ledger.** Disputed amounts shown as a ledger with status badges, not charts.
5. **Script-aware typography.** One harmonised Noto family across Latin, Gujarati and Devanagari, so the product looks equally deliberate in all three languages.
6. **Restrained colour.** Teal ink as primary. Marigold is used **only** as a highlight fill, never for text.

### 1.6 Design decisions and trade-offs

| ID | Decision | Trade-off |
|---|---|---|
| DD-01 | Light theme only in the MVP. Tokens are structured so a dark theme can be added later. | Fewer states to QA on a solo build; no dark preference support yet. |
| DD-02 | Noto Sans and Noto Serif families for Latin, Gujarati and Devanagari, self-hosted as subsetted variable WOFF2. Only the active script's font loads. | Less distinctive than a custom Latin face, but consistent across scripts and free (SIL OFL). Performance budget in Section 9.7. |
| DD-03 | Western Arabic numerals (0–9) for amounts and dates in all languages. | Matches insurer documents and the PRD verifier (AI-005), and avoids mixed numeral systems. **Confirmed by product owner, 15 Oct 2026.** |
| DD-04 | Amounts use Indian grouping (₹1,20,000) and tabular figures. | — |
| DD-05 | No uppercase text styles, and no italics for emphasis. | Gujarati and Devanagari have no letter case or true italics. Emphasis uses weight 600. |
| DD-06 | No illustrations or stock photography in the MVP. The only imagery is a line-icon set and the logo. | Less "friendly" at first glance; faster and more trustworthy. |
| DD-07 | No confidence percentages anywhere. Low confidence becomes the "Please check" flag. | Follows PRD AI-006 and avoids fake precision. |
| DD-08 | Admin console is English-only and desktop-first (minimum width 1024 px). | It is an internal tool. The PRD's i18n rule (NFR-018) covers user-facing strings. **Confirmed by product owner, 15 Oct 2026.** |
| DD-09 | The emailed sign-in code is entered in a single input with `autocomplete="one-time-code"`, not six separate boxes. | Better for screen readers and paste from the email app; slightly less "app-like". |
| DD-10 | Typed confirmations for destructive actions use a 4-digit code shown on screen. | Language-neutral; uses the numeric keypad (Section 6.6). |
| DD-11 | Motion is limited to state feedback (100–300 ms). No decorative motion; no shimmering skeletons when reduced motion is on. | — |
| DD-12 | No logo in the MVP. The brand appears as a **text wordmark**: "ClaimSathi" in `font.ui`, weight 700, `color.primary`, at `type.h3` size (20 px in the header). The `◧` symbol in the wireframes stands for this wordmark, not for a graphic mark. Favicon and social image are text-only placeholders (Section 9.6). | **Confirmed by product owner, 15 Oct 2026.** No design dependency before launch; a logo can replace the wordmark later without layout changes, because the header slot is fixed at 56/64 px height. |

---

## 2. Information architecture

### 2.1 Sitemap

```
ClaimSathi
├── Public (no sign-in)
│   ├── Home
│   ├── How it works
│   ├── What we don't do
│   ├── Accuracy
│   ├── Free official channels           (FR-044)
│   ├── Glossary                         (FR-017 support)
│   ├── Privacy notice · Terms · Contact / Grievance officer
│   └── Sign in → Verify code
├── First run (signed in, not onboarded)
│   ├── Choose language                  (FR-004)
│   └── Consent & disclaimer             (FR-005)
├── App (signed in + current consent)
│   ├── My cases                         (FR-007)
│   ├── New case: eligibility            (FR-006)
│   │   └── Out-of-scope result
│   ├── Case workspace  [case path: 1 Documents → 2 Check details → 3 Findings → 4 Letter → 5 Track]
│   │   ├── 1 Documents (+ processing)   (FR-008, FR-009)
│   │   ├── 2 Check details
│   │   │   ├── Facts                    (FR-010, FR-011)
│   │   │   └── Deductions               (FR-012)       [partial cases only]
│   │   ├── 3 Findings                   (FR-013 to FR-019)
│   │   ├── 4 Letter (insurer)           (FR-024, FR-027 to FR-029)
│   │   ├── 5 Track                      (FR-020 to FR-023)
│   │   │   ├── Bima Bharosa content     (FR-025, P1)
│   │   │   └── Ombudsman: checks → pack (FR-020, FR-026)
│   │   ├── Close case & outcome         (FR-034)
│   │   └── Case settings                (FR-030, FR-031, FR-042)
│   └── Account settings                 (FR-036, FR-032, FR-030)
│       └── Consent history
└── Admin (separate sign-in + MFA)
    ├── Review queue → Review item       (FR-040)
    ├── Knowledge base → Source          (FR-038)
    ├── Rules → Rule                     (FR-039)
    └── Metrics                          (FR-041, P1)
```

### 2.2 Navigation

**Public header**

- Wordmark (links to Home; DD-12), How it works, Accuracy, Free official channels, language switcher, "Sign in" button.
- Mobile: logo, language switcher and a menu button that opens a full-height sheet.

**App header (signed in)**

- Wordmark (links to My cases; DD-12), the case title when inside a case, language switcher, help button (opens the help sheet with official channels and glossary), and an account menu (Settings, Sign out).
- Mobile: the same, but the help and account items collapse into the menu.

**Case navigation: the case path**

| Viewport | Layout |
|---|---|
| Desktop (≥ 960 px) | Left rail, 240 px wide, with 5 steps plus "Case settings". |
| Mobile | A sticky compact bar under the header: "Step 3 of 5 · Findings ▾". Tapping it opens the step list in a bottom sheet. |

Step states are `not started`, `current`, `done`, `needs attention`, `locked`, and `stale` (Section 6.3). A step is locked only for a dependency reason; tapping a locked step explains why.

**Secondary navigation**

- Footer: privacy, terms, contact, what we don't do, free official channels, disclaimer line.
- Inside Findings: in-page anchor tabs (Summary / Deductions / Reasons / Checklist).

### 2.3 Page hierarchy, routes and auth boundaries

All user-facing routes carry a locale prefix `/{lang}` with `lang` ∈ `en`, `gu`, `hi`. For a signed-in user, the stored language preference wins; the app redirects to the matching prefix on sign-in.

| Route | Page ID | Access | Layout |
|---|---|---|---|
| `/{lang}` | PUB-01 Home | Public | PublicLayout |
| `/{lang}/how-it-works` | PUB-02 | Public | PublicLayout |
| `/{lang}/what-we-dont-do` | PUB-03 | Public | PublicLayout |
| `/{lang}/accuracy` | PUB-04 | Public | PublicLayout |
| `/{lang}/free-official-channels` | PUB-05 | Public | PublicLayout |
| `/{lang}/glossary` | PUB-06 | Public | PublicLayout |
| `/{lang}/privacy` · `/terms` · `/contact` | PUB-07 to PUB-09 | Public | PublicLayout (ReadingLayout) |
| `/{lang}/sign-in` | AUTH-01 | Signed-out only | AuthLayout |
| `/{lang}/sign-in/verify` | AUTH-02 | Signed-out with a pending email code | AuthLayout |
| `/auth/google/callback` | AUTH-03 (redirect only) | — | none |
| `/{lang}/welcome/language` | ONB-01 | Signed in, not onboarded | AuthLayout |
| `/{lang}/welcome/consent` | ONB-02 | Signed in; consent missing or outdated | AuthLayout |
| `/{lang}/cases` | APP-01 My cases | Protected | AppLayout |
| `/{lang}/cases/new` | APP-02 Eligibility | Protected | AppLayout (FocusLayout) |
| `/{lang}/cases/new/out-of-scope` | APP-03 | Protected | FocusLayout |
| `/{lang}/cases/{id}` | (redirects to current step) | Protected + owner | — |
| `/{lang}/cases/{id}/documents` | CASE-01 | Protected + owner | CaseLayout |
| `/{lang}/cases/{id}/details` | CASE-02 Facts | Protected + owner | CaseLayout |
| `/{lang}/cases/{id}/details/deductions` | CASE-03 | Protected + owner; partial cases | CaseLayout |
| `/{lang}/cases/{id}/findings` | CASE-04 | Protected + owner; facts confirmed | CaseLayout (with SourcePanel) |
| `/{lang}/cases/{id}/letter` | CASE-05 Letter: choose items | Protected + owner; findings ready | CaseLayout |
| `/{lang}/cases/{id}/letter/{letterId}` | CASE-06 Letter editor | Protected + owner | EditorLayout |
| `/{lang}/cases/{id}/track` | CASE-07 | Protected + owner | CaseLayout |
| `/{lang}/cases/{id}/track/bima-bharosa` | CASE-08 (P1) | Protected + owner | CaseLayout |
| `/{lang}/cases/{id}/track/ombudsman` | CASE-09 Checks | Protected + owner | CaseLayout |
| `/{lang}/cases/{id}/track/ombudsman/pack` | CASE-10 Pack | Protected + owner; no Block rule failing | CaseLayout / EditorLayout |
| `/{lang}/cases/{id}/close` | CASE-11 | Protected + owner | FocusLayout |
| `/{lang}/cases/{id}/settings` | CASE-12 | Protected + owner | CaseLayout |
| `/{lang}/settings` | ACC-01 | Protected | AppLayout |
| `/{lang}/settings/consent-history` | ACC-02 | Protected | AppLayout |
| `/admin/sign-in` · `/admin/mfa` | ADM-01, ADM-02 | Admin signed out | AdminAuthLayout |
| `/admin/review` · `/admin/review/{itemId}` | ADM-03, ADM-04 | `admin`, `reviewer` | AdminLayout |
| `/admin/knowledge` · `/admin/knowledge/{sourceId}` | ADM-05, ADM-06 | `admin` | AdminLayout |
| `/admin/rules` · `/admin/rules/{ruleKey}` | ADM-07, ADM-08 | `admin` | AdminLayout |
| `/admin/metrics` | ADM-09 (P1) | `admin` | AdminLayout |
| any unknown path | SYS-01 Not found | — | Minimal layout |

**Auth boundary rules**

1. A protected route without a session redirects to `/{lang}/sign-in?next=…`.
2. A signed-in user who has not onboarded goes to ONB-01. A user whose consent is missing or outdated goes to ONB-02 (FR-005).
3. A case route for a case the user does not own shows SYS-03 (Not available). The page **never** reveals whether the case exists.
4. Consumer sessions on `/admin/*` show the admin sign-in. They are never shown a "permission denied" page that reveals admin routes exist.
5. A reviewer opening a case without a support grant sees SYS-04 (Access not granted) with a short explanation (FR-042).

### 2.4 Role experiences

| Role | Experience |
|---|---|
| Visitor | Public pages; can switch language; "Start your case" leads to sign-in |
| User | Their own cases only; the full case workspace |
| Reviewer | Review queue and review items. Case content appears only within an active support grant. |
| Admin | Everything a reviewer can do, plus the knowledge base, rules and metrics |

---

## 3. User flows

Notation: `[Screen]`, `(action)`, `<decision>`, `{system state}`.

### F1: First use through to the first letter (PRD J1)

| Stage | Detail |
|---|---|
| **Entry** | Home, a shared link, or a reminder email |
| **Flow** | `[PUB-01]` (Start your case) → `[AUTH-01]` Continue with Google, **or** enter email → `[AUTH-02]` enter emailed code → `<first time?>` yes → `[ONB-01]` pick language → `[ONB-02]` read notice; tick processing (required) and reminders (optional) → `[APP-02]` eligibility (6 questions, one per screen on mobile) → `<in scope?>` no → `[APP-03]`; yes → case created → `[CASE-01]` upload → `{processing}` → `[CASE-02]` confirm facts → `<partial?>` yes → `[CASE-03]` deductions → `{analysis running}` → `[CASE-04]` findings → (Write my letter) → `[CASE-05]` choose items + language → `{generating}` → `[CASE-06]` review; tick "I've read this letter" → (Download PDF) → prompt "Did you send it?" → (Log as sent) → `[CASE-07]` track |
| **Loading** | Code sending (button spinner). Document processing (per-document status). Analysis (step list). Letter generation (step list). |
| **Errors** | Code email failed (offer Google). Wrong code (inline, with attempts left). Upload errors (per file). Processing failed (retry per document). Analysis failed (F6). |
| **Completion** | The Track page shows "Sent on DD/MM/YYYY" and the next deadline card: "You can go to the Ombudsman from 15/11/2026 if the insurer doesn't reply." |

### F2: Escalation to the Ombudsman (J2, J9, J10, J11)

- **Entry:** the reminder email "It's been a month", or Track (Go to Ombudsman).
- **Flow:** `[CASE-07]` → `[CASE-09]` checks run (deterministic, instant) →
  - `<any Block?>` yes: blocked state listing each failing rule with "what to do" (for example "Log that you wrote to the insurer"). No pack button.
  - `<only Warn/Inform?>`: acknowledgement checkbox per warning (for example "I understand my complaint is late"), then (Create Ombudsman pack).
  - `{generating}` → `[CASE-10]` pack: letter review, copy fields, enclosures, filing instructions, signatory notice → (Download) → (Log that I filed) → Track.
- **Helper branch:** the signatory notice is shown above the letter and again in the download dialog.
- **Completion:** Track shows "Filed with the Ombudsman on …", plus an informational card that awards usually come within 3 months of a complete complaint.

### F3: Missing policy wording, limited mode (J3)

- **Entry:** CASE-04 after analysis, with no wording available.
- **Flow:** a limited-mode callout (info) at the top of Findings: "We couldn't check your policy wording, so we checked the rules only." → checklist item "Policy wording" → (Upload wording) → returns to CASE-01 with the type preselected → `{processing}` → Findings marked **stale**, with the banner "New document added. Update findings" → (Update findings) → `{analysis}` → full Findings.

### F4: Validation errors (J4)

| Error | Response |
|---|---|
| File over 20 MB | Rejected immediately on that file tile: "This file is 24 MB. The limit is 20 MB. Try taking photos instead." |
| HEIC | "This photo format isn't supported. Use 'Take photo' instead." |
| Unreadable photo | The document goes to `needs_attention` with a "Retake" action and guidance. |
| Line items don't add up | Warning callout on CASE-03. The user can continue; the warning persists on Findings. |
| Invalid event date | Inline error on the field, with an error summary at the top of the sheet. |

### F5: Cancellation and resume (J5)

- Every form autosaves. Leaving mid-review and returning shows the case card on My cases with "Continue: Check details".
- Leaving an unsaved letter edit is not possible to lose, because autosave runs every 10 s and on blur (FR-027). Navigating away mid-save shows the native "Changes may not be saved" prompt.
- **Delete case** mid-processing: the confirm dialog says "Processing will stop and everything will be deleted." Then the deletion state, then a return to My cases with a success notice.

### F6: Failed AI call (J6)

| Situation | Response |
|---|---|
| Analysis is retrying | The step list shows "Taking longer than usual. We're retrying. You can leave; we'll email you." This is a neutral info state, not an error. |
| Retries exhausted | Error state: "We couldn't finish your findings." Primary action: **Try again**. Secondary: **Write a basic letter now**, which goes to CASE-05 with only the deterministic grounds and is labelled as such (PRD AI-008). |
| Translation failed | The letter shows English with a warning callout: "Gujarati version unavailable right now." Action: **Try again**. Never shows partial text. |

### F7: Sign-in recovery and new device (J7)

- New device: sign in with Google or an email code, then My cases.
- Code email not arriving after 60 s: "Resend code" becomes active, with the hint "Check your spam folder". After 2 failures, a link appears: "Continue with Google instead".
- Lost access to the email account: the sign-in help text links to Contact. No in-app recovery exists in the MVP (PRD R-14). The design must not suggest one.

### F8: Account deletion (J8)

ACC-01 → Danger zone → (Delete my account) → dialog listing what will be deleted → type the 4-digit code shown → (Delete permanently) → `{deleting}` (button spinner, inputs disabled) → signed-out page "Your account and all cases have been deleted."

### F9: Insurer reply arrives (J12)

Track → (Log an update) → "Insurer replied" → date + upload + "Are you satisfied?" →
- **No:** prompt "Make this the current decision and update findings?" → Findings stale → update.
- **Yes:** prompt to close the case → CASE-11.

### F10: Report a problem (FR-035)

The "Something's wrong?" link on a counter-point, citation or paragraph opens the ReportDialog: reason radios, optional comment, and an unticked checkbox "Allow a reviewer to see this case for 7 days". On submit, the dialog closes, a toast says "Thanks, we'll review this", and the item shows a small "Reported" tag.

### F11: Admin review (FR-040)

Review queue (filters: source, status, language) → item → view the flagged output and citations → `<needs case content?>` → shows a grant status chip (Granted until … / Not granted) → mark correct / incorrect + category / needs knowledge-base fix → next item.

---

## 4. Wireframes and screen inventory

### 4.0 Conventions and shared state patterns

The wireframes are low-fidelity and show structure, hierarchy and content order. Mobile is drawn at 360 px; desktop at 1280 px where the layout differs materially.

| State | Standard treatment |
|---|---|
| Loading (first load) | Skeletons of the real layout (no shimmer when reduced motion is on). After 10 s, add the text "Still loading…". |
| Processing (AI or OCR) | `ProcessingSteps` component with real step states (Section 7.6). |
| Empty | `EmptyState`: icon, title, one sentence, one action. |
| Error (recoverable) | `ErrorState` in place of the content: what happened, what to do, Retry. The error reference ID is shown in small text for support. |
| Error (network) | `OfflineBanner` at the top. Actions that need the network are disabled with "You're offline". |
| Success | Inline confirmation in context. Toasts only for minor confirmations (Section 6.9). |
| Permission denied | SYS-03 or SYS-04 page. |
| Stale | `StaleBanner` (Section 6.3) with an "Update" action. |

---

### PUB-01 Home
- **Purpose:** explain the scope and the value proposition, build trust, and start a case.
- **User:** visitors, including arrivals from search, shared links and WhatsApp forwards.
- **PRD:** FR-043, FR-044.
- **Layout:** PublicLayout with a single column. Reading sections are capped at 680 px wide; the desktop hero uses 2 columns (text left, sample "ledger" card right, built from real UI components, not an image).
- **Actions:** primary "Start your case" (to sign-in). Secondary "How it works".
- **Content order:**
  1. Headline and subhead
  2. Three-step strip
  3. "What you get": a sample ledger card with the badge legend
  4. "What we don't do" summary
  5. "Free official channels" callout
  6. Privacy summary
  7. Footer disclaimer
- **States:** static page. The language switch preserves the scroll position.
- **Rules:** no statistics without a source link (FR-043). No testimonials.

```
┌─────────────────────────────┐
│ ◧ ClaimSathi   ગુ हि EN  ☰ │
├─────────────────────────────┤
│ Health claim cut or        │
│ rejected?                  │
│ Find out why, and write to │
│ your insurer with the      │
│ rules on your side.        │
│ [ Start your case → ]      │
│ Free · No success fee ·    │
│ You send everything        │
├─────────────────────────────┤
│ ① Upload letter & bill      │
│ ② Check what we read        │
│ ③ Get findings + letter     │
├─────────────────────────────┤
│ Sample ledger card          │
│ Room charges  ₹18,400 ▲No   │
│               clause cited  │
│ Consumables   ₹6,250  ◇Cited│
│               – may not apply│
├─────────────────────────────┤
│ ⓘ Insurer, Bima Bharosa and │
│ Ombudsman are FREE. Never   │
│ pay anyone claiming to be   │
│ the Ombudsman. [Learn more] │
├─────────────────────────────┤
│ Footer · disclaimer         │
└─────────────────────────────┘
```

### PUB-02 How it works · PUB-03 What we don't do · PUB-07 to PUB-09 Privacy, Terms, Contact
- **Purpose:** explanation, trust and legal pages (FR-043).
- **Layout:** ReadingLayout. A 680 px column, a table of contents (sticky on desktop, a collapsible "On this page" on mobile), and a "Last updated" date.
- **Components:** Prose, Callout, ContentsNav.
- **States:** static.
- **PUB-09 Contact** includes the grievance officer contact (OQ-13) and an email link. There is no contact form in the MVP, because the PRD does not specify one.

### PUB-04 Accuracy
- **Purpose:** publish the latest citation audit (FR-043, M-04).
- **Layout:** ReadingLayout with a single metric panel: "Citation accuracy in our last audit: X% of N citations (audited DD/MM/YYYY)". Below it, the method and a link to the "what we check" explanation.
- **Empty state (before the first audit):** "We haven't published an audit yet. We will publish one before we open to everyone." Shows no number.
- **Rule:** the number must come from the latest stored audit. It is never hard-coded.

### PUB-05 Free official channels
- **Purpose:** FR-044. It is also reachable from the help sheet on every case screen.
- **Content:** three cards (Insurer grievance officer, Bima Bharosa, Insurance Ombudsman). Each card states what the channel is, when to use it, that it is free, and an external link (opens in a new tab with an external-link icon and "opens official site").
- **Warning callout:** "Never pay anyone claiming to be the Ombudsman."

### PUB-06 Glossary
- **Purpose:** the full list behind the glossary popovers (FR-017).
- **Layout:** a search field, then terms in alphabetical order for the current language. Each term shows the English term alongside.
- **Empty search:** "No term matches '…'."

### AUTH-01 Sign in
- **PRD:** FR-001, FR-002 (D-006: no phone sign-in in the MVP).
- **Layout:** Google first, because most target users are on Android phones already signed in to Google. Email is the alternative.
- **Actions:**
  - Primary: "Continue with Google" (full-width, Google's brand-compliant button).
  - Secondary: "Use email instead" reveals the email form in place. It is not a new page, so focus moves to the email field.
- **Email form:**
  - **TextField (type email):** `inputmode="email"`, `autocomplete="email"`.
  - **Validation:** on blur and on submit. Error: "Enter a valid email address, like name@example.com".
  - **Button:** "Email me a code".
- **States:**
  - Sending: spinner in the button.
  - Email-send failure: an error callout with "Try again" and "Continue with Google".
  - Rate-limited: "Too many attempts. Try again in 42 minutes."
  - Google cancelled: returns here with no error.
- **Consent note under the buttons:** "By continuing you agree to our Terms. We'll ask your permission before reading any documents."

```
┌─────────────────────────────┐
│ ◧ ClaimSathi        ગુ हि EN│
│                             │
│ Sign in                     │
│ [ G  Continue with Google ] │
│ ───────── or ─────────      │
│ Use email instead ▾         │
│ Email                       │
│ ┌─────────────────────────┐ │
│ │ name@example.com        │ │
│ └─────────────────────────┘ │
│ [ Email me a code ]         │
└─────────────────────────────┘
```

### AUTH-02 Verify code
- **Form:** OTPField, a single input with `autocomplete="one-time-code"`, numeric, maxlength 6. It auto-submits on the 6th digit. Pasting the code from the email app is supported.
- **Copy:** "We sent a 6-digit code to r•••@gmail.com. It expires in 10 minutes. Not there? Check your spam folder. Change email."
- **Resend:** disabled with a countdown "Resend in 0:60", then enabled.
- **Errors:**
  - Wrong code: "That code isn't right. 3 tries left."
  - Expired code: "This code has expired. Send a new one."
  - Locked: "Too many wrong tries. Send a new code."
- **Success:** routes to ONB-01, ONB-02 or the `next` target.

### ONB-01 Choose language
- **PRD:** FR-004.
- **Layout:** three large RadioCards, each showing the language name in its own script (ગુજરાતી, हिन्दी, English) with one sample sentence in that script. The preselected card follows the browser locale.
- **Action:** "Continue", labelled in the selected language.

### ONB-02 Consent and disclaimer
- **PRD:** FR-005.
- **Layout:** FocusLayout, 680 px. A plain-language notice organised as an accordion of 7 sections (what we collect, why, the AI provider, how long we keep it, your rights, the grievance contact, not legal advice). The summary of each section is visible without expanding.
- **Form:** two ConsentItems.
  - Processing: required. Unticking shows the hint "We need this to read your documents."
  - Email reminders: optional, with an email field revealed when ticked.
- **Actions:** primary "Agree and continue" (disabled until processing is ticked, with the hint visible). Secondary "Not now", which signs the user out and returns to Home.
- **Re-consent variant:** a top callout "We've updated how we use your data. What changed: …", with the changed sections expanded.
- **States:** saving, then success (routes on), or a save error (inline error with retry).

### APP-01 My cases
- **PRD:** FR-007.
- **Layout:** AppLayout. A page title with a "New case" button (top right on desktop, a sticky bottom button on mobile), then a list of CaseCards.
- **CaseCard contents:** case nickname, insurer, patient initials, amount in dispute (₹), stage chip, next deadline (urgency colour, Section 5.2.4), status line ("Continue: Check details"), and a "Needs attention" tag if any step needs it.
- **Sort:** by nearest deadline first, then by most recently updated.
- **States:**
  - Empty: "No cases yet. Start with your insurer's letter." and a "Start a case" button.
  - Loading: 3 skeleton cards.
  - Error: ErrorState with Retry.
  - Limit reached (10 open cases): the "New case" button is disabled with the explanation "You have 10 open cases. Close one to start another."
- **Responsive:** one column on mobile. Two columns of cards from 960 px. No table view; the case count is small.

```
┌─────────────────────────────┐
│ ◧  My cases          ☰      │
├─────────────────────────────┤
│ ┌─────────────────────────┐ │
│ │ Papa – Apollo, Mar 2026 │ │
│ │ Star Health · ₹1,20,000 │ │
│ │ ● Step 5 Track          │ │
│ │ ⏱ Ombudsman from 15/11  │ │
│ │ Continue →              │ │
│ └─────────────────────────┘ │
│ ┌─────────────────────────┐ │
│ │ Meena – knee surgery    │ │
│ │ ⚠ Needs attention       │ │
│ │ Continue: Check details →│ │
│ └─────────────────────────┘ │
├─────────────────────────────┤
│ [ + New case ]  (sticky)    │
└─────────────────────────────┘
```

### APP-02 New case: eligibility
- **PRD:** FR-006.
- **Layout:** FocusLayout with a progress indicator "Question 2 of 6" (a real count). One question per screen on mobile. On desktop, the questions run as a single scrolling form with sections.
- **Questions:**
  1. RadioCards: Yes / No / Not sure.
  2. RadioCards: Rejected / Partly paid / Delayed or pending / Other.
  3. RadioCards: policy type.
  4. A name field, a relationship select (Self / Spouse / Parent / Child / Other), and a "Policyholder is…" field.
  5. RadioCards: Yes / No / Not sure.
  6. Segmented month and year, plus "I don't know".
- **Inline explanations:**
  - Q5 "Yes" shows an info callout: "We can still help you write to the insurer, but the Ombudsman can't take a matter that's already in court."
  - Q3 "Employer or group" shows an info caveat (OQ-07).
- **Navigation:** Back and Next, plus a final "Create case" that also asks for a case nickname, prefilled as "{Patient} – {month year}".
- **Branches:**
  - Q1 = No: APP-03.
  - Q2 = Delayed: the case is created in delay mode, and a callout explains what is limited.
- **Validation:** each question is required except the nickname. Pressing Next without an answer shows an inline error.

### APP-03 Out of scope
- An EmptyState-style page: "ClaimSathi only helps with health insurance claims in India." It links to the free official channels and the Ombudsman page, and offers "Back to my cases".

### CaseLayout (shared by CASE-01 to CASE-12)

```
Desktop ≥960                                   Mobile
┌──────────────────────────────────────────┐   ┌──────────────────────┐
│ Header: logo · case title · ગુ हि EN · ? · ◔│   │ ◧ Papa–Apollo  ? ☰   │
├─────────┬────────────────────────────────┤   ├──────────────────────┤
│Case path│  Page title                     │   │ Step 2 of 5 · Check ▾│ (sticky)
│ ✓ 1 Docs│  [StaleBanner / Callouts]      │   ├──────────────────────┤
│ ● 2 Check│  Content (max 760)  │SourcePanel│   │ Content              │
│ ○ 3 Find│                     │(400, opens│   │                      │
│ ○ 4 Lettr│                     │ on demand)│   │                      │
│ ○ 5 Track│                     │           │   ├──────────────────────┤
│ ⚙ Settings│ ─ Disclaimer footer line ─   │   │ [Primary action]     │ (sticky)
└─────────┴────────────────────────────────┘   └──────────────────────┘
```

- **Desktop:** the SourcePanel is a right column (400 px) that pushes the content; it does not overlay it. It opens when a citation is selected.
- **Below 960 px:** the SourcePanel becomes a bottom sheet (90% viewport height) on mobile, or a 480 px overlay drawer on tablet.
- **Mobile action bar:** the sticky bottom action bar holds the page's primary action, with a safe-area inset.
- **Disclaimer:** the self-help disclaimer line appears on every analysis screen (NFR-024).

### CASE-01 Documents
- **PRD:** FR-008, FR-009.
- **Layout:**
  - **Required callout:** "Start with the letter from your insurer (rejection or settlement letter)."
  - **Upload actions:** on mobile, two large buttons, **Take photo** (opens the camera via `capture="environment"`) and **Choose file**. On desktop, an UploadDropzone that also has a "Choose files" button.
  - **List:** DocumentCards.
- **DocumentCard:** a thumbnail, a type select (pre-suggested), the page count, a status chip (`Uploading` with a determinate bar from the real byte count, `Queued`, `Reading`, `Ready`, `Needs attention`, `Failed`), and an overflow menu (Change type, Add page (photos), Remove).
- **Password-protected PDF:** opens the PasswordDialog: "This PDF is locked. Insurers often use your date of birth (for example 15081972). We use it once and never save it." The field has a show/hide toggle.
  - On a wrong password: "That password didn't open the file."
- **Actions:**
  - Primary: "Continue to check details". It is enabled when a `decision_letter` is `Ready`. If disabled, it explains: "Add the insurer's letter first" or "Waiting for 2 documents to finish reading. You can leave this page."
  - Secondary: "Add more".
- **Limits shown:** "Up to 15 files, 50 MB in total, 20 MB each" in helper text. Usage is shown as "4 of 15 files · 18 of 50 MB". When a limit is reached, the upload actions are disabled with the reason (PRD FR-008, D-005).
- **States:**
  - Empty: the upload actions plus a short checklist of useful documents.
  - Processing: per card.
  - Duplicate: "You've already added this file" toast, and the card is not added.
  - Malware: per-card error "We couldn't accept this file."
  - Offline: banner, with queued uploads shown as "Waiting for connection".

```
┌─────────────────────────────┐
│ Step 1 of 5 · Documents ▾   │
├─────────────────────────────┤
│ Upload your documents       │
│ ⓘ Start with the insurer's  │
│   letter.                   │
│ [ 📷 Take photo ][ ⬆ File ] │
│ 3 of 15 files · 12 of 50 MB │
│ ┌─────────────────────────┐ │
│ │▣ Settlement letter ▾ 3p │ │
│ │  ● Reading…          ⋯  │ │
│ ├─────────────────────────┤ │
│ │▣ Final bill ▾       6p  │ │
│ │  ✓ Ready             ⋯  │ │
│ ├─────────────────────────┤ │
│ │▣ Policy wording ▾ 42p   │ │
│ │  ⚠ Locked PDF [Unlock]  │ │
│ └─────────────────────────┘ │
│ Also useful: discharge      │
│ summary, policy schedule    │
├─────────────────────────────┤
│ [Continue to check details] │
│ Waiting for 1 document…     │
└─────────────────────────────┘
```

### CASE-02 Check details (facts)
- **PRD:** FR-010, FR-011.
- **Layout:**
  - **Intro:** "Check what we read. Fix anything that's wrong."
  - **"Needs your check" group (pinned first):** low-confidence and empty required fields.
  - **Groups:** Policy, Claim, Decision, each a Fieldset of FieldReviewRows.
- **FieldReviewRow:** a label, the value (read mode), a provenance tag ("From your documents", or "You entered" after an edit), a "Please check" flag where needed, a "See where we read this" link (opens the SourcePanel with the page crop highlighted), and an Edit button that switches the row to edit mode with the right input (DateField, AmountField, Select, Text).
- **Verbatim fields** (stated reasons, cited clauses) are shown in a quote style. Editing them is allowed but warns: "Type it exactly as written in the letter."
- **Decision letter choice:** if several decision letters exist, a RadioCard choice "Which is the current decision?" appears at the top.
- **First inception date:** a DateField plus an "I don't know" checkbox, with helper text: "The date your policy first started, even if renewed since. It's on your policy schedule."
- **Sticky action bar:** "These details are correct". It is disabled until the required fields are confirmed, with a live count: "2 fields still need checking" that links to the first one.
- **States:**
  - Loading: skeleton rows.
  - Extraction failed: ErrorState with "Retry reading" and "Enter details yourself" (opens all fields in edit mode).
  - Post-confirmation edit: a confirm dialog "Changing this will update your findings and letters. Continue?", after which the case is stale.
- **Responsive:** on desktop, a two-column row (label | value + actions). On mobile, stacked rows.

```
┌─────────────────────────────┐
│ Step 2 of 5 · Check ▾       │
├─────────────────────────────┤
│ Check what we read          │
│ ⚠ Needs your check (2)      │
│ ┌─────────────────────────┐ │
│ │ First policy start date │ │
│ │ — not found             │ │
│ │ [Enter date] □ Don't know│ │
│ ├─────────────────────────┤ │
│ │ Amount paid             │ │
│ │ ₹2,10,500  ⚑Please check│ │
│ │ ▣From your documents    │ │
│ │ See where ↗   [Edit]    │ │
│ └─────────────────────────┘ │
│ Policy ▾  Claim ▾  Decision ▾│
├─────────────────────────────┤
│ [These details are correct] │
│ 2 fields still need checking│
└─────────────────────────────┘
```

### CASE-03 Deductions (partial cases)
- **PRD:** FR-012.
- **Layout:**
  - A summary strip: "9 deductions · total ₹54,320 · matches deducted amount ✓", or the warning callout when it does not match.
  - Desktop: an editable LedgerTable with columns Item | Billed | Deducted | Insurer's reason | Clause cited | (edit).
  - Mobile: LineItemCards stacked, each card editable through a bottom sheet.
- **Actions:** primary "Confirm deductions". Secondary "Add a line" (opens the sheet).
- **Edge case:** an `unitemised` single line shows an info callout: "Your insurer didn't list items separately. We'll ask them to."
- **Validation:** deducted amount ≥ 0 and ≤ billed (if billed is known). Required fields are description and deducted amount.
- **Empty state (nothing extracted):** "We couldn't find a list of deductions." Actions "Add lines yourself" and "Upload breakup document".

### CASE-04 Findings
- **PRD:** FR-013 to FR-019.
- **Layout (top to bottom):**
  1. **Limited or delay mode callout**, if applicable.
  2. **Summary card:** the explanation (150 words or fewer) with glossary terms, the amount at stake, and the recommended next step.
  3. **Wording source line:** "Checked against: Star Health Comprehensive, version effective 01/04/2024 (our library) · Use my uploaded copy". This is a link if the user uploaded a copy (FR-014).
  4. **Ledger by status:** a list of status groups with totals, for example "No clause cited: 6 items · ₹38,400". Each group expands to its LineItemCards with AuditStatusBadges.
  5. **Reasons for rejection** (repudiation cases): ReasonCards, each with CounterPointCards.
  6. **Evidence checklist.**
  7. **Sticky action:** "Write my letter".
- **In-page tabs (anchors):** Summary · Deductions · Reasons · Checklist. Shown as horizontal scrolling chips on mobile.
- **CounterPointCard:** see Section 6.11.
- **"Appears consistent with your policy" items** are shown honestly, unselected for the letter, with: "Challenging this may not succeed."
- **States:**
  - Analysis running: ProcessingSteps (Section 7.6) replaces the content.
  - Failed: F6.
  - Abstention per item: CannotAssess rows with recovery actions (FR-019).
  - No grounded points at all: an EmptyState inside the Reasons section: "We found no grounded argument against this reason." This is followed by the deterministic requests that still apply.
  - Stale: StaleBanner "Your details changed. Update findings." The "Write my letter" button is disabled until updated.
- **SourcePanel:** opens on a citation click (Section 6.12).

```
Desktop
┌────────┬──────────────────────────────────────┬──────────────────┐
│ path   │ Findings                              │ Source            │
│        │ [Summary][Deductions][Reasons][List]  │ IRDAI Master Circ.│
│        │ ┌ Summary ─────────────────────────┐ │ 29 May 2024 ·     │
│        │ │ Your insurer paid ₹2,10,500 of   │ │ Para 17(b)        │
│        │ │ ₹2,64,820. 6 deductions (₹38,400)│ │ "…giving reference│
│        │ │ have no clause cited…            │ │ to the specific   │
│        │ │ Next: write to the insurer.      │ │ terms and…" ▒▒▒▒ │
│        │ └──────────────────────────────────┘ │ ▤Verified quote   │
│        │ ▲ No clause cited · 6 · ₹38,400   ▾ │ Translation (ગુ): │
│        │ ◇ Clause found – may not apply · 1 ▾│ …                 │
│        │ ○ Appears consistent · 2 · ₹15,920 ▾│ [Close]           │
│        │ ✓ Checklist (2 of 4)                 │                   │
│        │                    [Write my letter] │                   │
└────────┴──────────────────────────────────────┴──────────────────┘
```

### CASE-05 Letter: choose what to include
- **PRD:** FR-024.
- **Layout:**
  - **Stage label:** "Letter to your insurer's grievance officer".
  - **Checklist of disputed items:** `NO_CLAUSE_CITED`, `CLAUSE_NOT_FOUND` and `QUESTIONABLE` are pre-ticked. `APPEARS_VALID` and `CANNOT_ASSESS` are unticked, with reasons.
  - **Amount requested:** a running total.
  - **Letter language:** RadioCards (ગુજરાતી / हिन्दी / English), with a note when not English: "We'll also include an English copy."
  - **Complainant and signatory:** prefilled, with a link to edit in Check details.
- **Action:** primary "Create letter", which runs ProcessingSteps.
- **Validation:** at least one item must be selected, or the user ticks "Only ask for the clause references", which is the deterministic-only route.

### CASE-06 Letter editor
- **PRD:** FR-027, FR-028, FR-029, AI-007.
- **Layout:** EditorLayout.
  - **Toolbar:** language Tabs (for example "ગુજરાતી | English copy"), an undo/redo group, and minimal formatting (bold, list). No font controls.
  - **Paper canvas:** a white sheet with A4 proportions on desktop (max 794 px wide), with 32 px padding on mobile. Uses the serif letter typography.
  - **ProtectedQuote spans:** quoted text with a citation tab (superscript number in a tinted tab). Selecting one opens the SourcePanel.
  - **Provenance:** a grounds paragraph has a subtle left margin rule in the AI-suggestion colour, with the tag "Written by AI · check it". Facts filled from confirmed fields carry no AI tag. The footnotes list the citations.
  - **Bottom review bar:** checkbox "I've read this letter and it's correct" (required for the first export of each version), then **Download** (menu: PDF, Word (DOCX), Copy as email text).
  - **Autosave indicator:** "Saved" / "Saving…" / "Not saved: offline". Text with an icon, `aria-live="polite"`.
- **Editing a protected quote:** shows an inline warning chip "No longer a verified quote" and a toast offering Undo.
- **States:**
  - Generating: ProcessingSteps.
  - Translation unavailable: a warning callout with Retry; English shown.
  - Stale: the banner "Your findings changed. Update letter", and Download is disabled with the reason.
  - Generation failed: ErrorState with "Try again" and "Write a basic letter now".
- **After download:** the dialog "Did you send it?" with options "Log as sent" (opens the event sheet) and "Not yet".

```
┌─────────────────────────────┐
│ Letter · ગુજરાતી | English  │
│ ↶ ↷  B  •      Saved ✓      │
├─────────────────────────────┤
│ ┌─────────────────────────┐ │
│ │ To: Grievance Officer   │ │
│ │ Star Health…            │ │
│ │ Subject: …              │ │
│ │ 1. …ના નિયમ મુજબ       │ │
│ │ "giving reference to the│ │
│ │ specific terms…" [1]    │ │
│ │ (અનુવાદ: …)             │ │
│ │ ▏AI-written · check it  │ │
│ └─────────────────────────┘ │
├─────────────────────────────┤
│ ☐ I've read this letter     │
│ [ Download ▾ ]              │
└─────────────────────────────┘
```

### CASE-07 Track
- **PRD:** FR-020 to FR-023.
- **Layout:**
  - **NextActionCard** (one primary action), for example: "Wait for the insurer's reply · You can go to the Ombudsman from 15/11/2026 · [Log an update]".
  - **DeadlineList:** Ombudsman eligibility, Ombudsman limitation, expected insurer reply. Each shows a date, "N days left", an urgency colour and a "how we calculated this" link (a disclosure that cites the rule and source).
  - **"Add to calendar" [P1]:** a secondary button under the DeadlineList. It downloads an `.ics` file whose events contain only the case nickname and the action (PRD FR-022). On Android it opens in the user's calendar app.
  - **Stage cards:** Insurer (done, current or pending), Bima Bharosa (optional, labelled "Optional · can run alongside"), Ombudsman (locked or eligible, with the reason).
  - **Timeline:** CaseEvents in order.
- **Actions:**
  - Primary (contextual): "Log an update" or "Go to Ombudsman".
  - Secondary: "Close case".
- **Event sheet:** EventTypes as RadioCards, then fields per type (DateField, method select, file upload, satisfied yes/no, token number).
- **Validation:** dates cannot be in the future or before the decision date (FR-023).
- **States:**
  - No events: an EmptyState in the timeline: "Log when you send your letter, so we can track deadlines."
  - Passed limitation: an error-tone deadline row "Passed on …" with a link to the late-filing explanation.

### CASE-08 Bima Bharosa content (P1)
- **PRD:** FR-025.
- **Layout:**
  - Intro: optional, free, and can run alongside.
  - CopyFields, each with a label, a read-only value box, a character count (no truncation until limits are known, OQ-04) and a Copy button.
  - Link to the official portal, and the toll-free number as a `tel:` link.
- **States:** copied (button label changes to "Copied ✓" for 2 s and announces it). Clipboard unavailable: a "Select text" fallback.

### CASE-09 Ombudsman checks
- **PRD:** FR-020.
- **Layout:**
  - Title: "Can you go to the Ombudsman yet?"
  - **RuleCheckList:** one row per rule, with status (Pass / Block / Warn / Inform), a plain explanation, a "what to do" action and a source link.
  - Block rows sort first.
  - Warn rows require an acknowledgement checkbox each.
- **Actions:**
  - When no Block: primary "Create Ombudsman pack" (enabled when all warnings are acknowledged).
  - When blocked: no primary pack button. Each Block row carries its own fix action, for example "Log that you wrote to the insurer", which opens the event sheet.
- **Helper notice (RULE-ESC-06):** an info callout naming the complainant: "{Name} must sign and file this complaint."

```
┌─────────────────────────────┐
│ Can you go to the Ombudsman?│
│ ✕ Wait for the insurer      │
│   You wrote on 15/10/2026.  │
│   Eligible from 15/11/2026. │
│   Rule 14(3)(a) ↗           │
│ ✓ Not in any court          │
│ ⚠ Claim above ₹50 lakh?  No │
│ ⓘ Your father must sign     │
│   and file this complaint.  │
├─────────────────────────────┤
│ Pack available from 15/11   │
└─────────────────────────────┘
```

### CASE-10 Ombudsman pack
- **PRD:** FR-026.
- **Layout:** sections in order:
  1. Signatory notice.
  2. Complaint letter (EditorLayout reused; a grievance-history section filled from logged events).
  3. Form fields (CopyFields).
  4. Enclosures checklist (each linked to an uploaded document, or flagged as missing).
  5. How to file: three Tabs (Online, Email, Post) with free-of-cost notes.
- **Actions:** primary "Download pack" (PDF of the letter plus an enclosure list). Secondary "Log that I filed".
- **Guard:** if a Block rule starts failing (for example an edited date), the page shows a blocking callout and returns the user to CASE-09.

### CASE-11 Close case and outcome
- **PRD:** FR-034.
- **Layout:**
  - Outcome RadioCards: Paid in full / Partly paid / Not paid / Withdrew.
  - An optional AmountField.
  - At Stage 3: "Did the Ombudsman accept your complaint?" (Accepted / Dismissed as not admissible / Don't know).
  - A RatingInput (1–5) with labels, and an optional comment.
- **Copy:** "All questions are optional."
- **Actions:** primary "Close case". Secondary "Skip and close".
- **Success:** the case card moves to the "Closed" section of My cases, and a note explains retention: "Your files will be deleted on DD/MM/YYYY. You can extend once" (FR-033).

### CASE-12 Case settings
- **PRD:** FR-030, FR-031, FR-042.
- **Sections:**
  1. **Case nickname** (edit).
  2. **Support access:** a toggle "Allow a reviewer to see this case for 7 days". When on, shows "Access until 22/10/2026 · Revoke".
  3. **Download case data:** a button, then a status ("Preparing…"), then a download link (valid 24 h).
  4. **Retention:** "Files will be deleted on …", with a single "Extend 90 days" option for closed cases.
  5. **Danger zone:** "Delete this case" opens the ConfirmDialog with a typed code.

### ACC-01 Account settings
- **PRD:** FR-036, FR-032.
- **Sections:**
  - Language.
  - Email (add or change, with verification-pending status).
  - Email reminders toggle.
  - Large text toggle (applies immediately and previews on the toggle's own label).
  - Analytics opt-out toggle (PRD Section 7).
  - Sign out everywhere (ConfirmDialog).
  - Download all my data.
  - Consent history link.
  - Danger zone: Delete account.
- **States:** a per-setting "Saved" inline confirmation, and per-setting errors.

### ACC-02 Consent history
- A list of consent records: version, purposes, date, language, withdrawn date. Each version opens a read-only notice.
- **Action:** "Withdraw processing consent" opens a ConfirmDialog explaining that processing stops and offering account deletion (FR-005).

### SYS-01 Not found · SYS-02 Server error · SYS-03 Not available · SYS-04 Access not granted · SYS-05 Offline
- Each page has an EmptyState-style layout with one action: Home, My cases or Retry.
- SYS-03 copy: "This page isn't available. It may have been deleted, or it belongs to another account."

### Admin (desktop-first, English, minimum width 1024 px)

**ADM-01 Sign in and ADM-02 MFA** (FR-037)
- Email/password and a TOTP code field.
- Errors: invalid credentials; invalid code. Lockout copy after 5 failures.

**ADM-03 Review queue** (FR-040)
- **DataTable columns:** Created · Source (User report / Verifier / Audit) · Language · Category · Status · Grant (✓ until / –).
- **Filters:** source, status, language, date range.
- **Pagination:** 25 per page.
- **Empty:** "Queue is clear."
- **Row:** opens ADM-04.

**ADM-04 Review item**
- Two panes: the flagged output with its citations on the left; SourceExcerpts with highlights on the right.
- **Case content area:** if there is no grant, shows SYS-04 inline: "User hasn't granted access."
- **Decision radios:** Correct / Incorrect (category select) / Needs knowledge-base fix (link to the source).
- **Actions:** "Save & next" and "Skip".

**ADM-05 Knowledge base** (FR-038)
- **Table columns:** Title · Type · Identifier · Version · Effective · Status (Draft / Published / Retired).
- **Actions:** "Add source".
- **Filters:** type, status.

**ADM-06 Source detail**
- **Metadata form:** all FR-038 fields. Validation: required fields; effective-from earlier than effective-to.
- **Upload:** a PDF upload, then a chunk preview list showing clause IDs, with rows missing an identifier flagged in warning colour.
- **Publish:** requires the checkbox "Text checked against the official PDF".
- **Actions:** "Retire version" (ConfirmDialog).

**ADM-07 Rules** (FR-039)
- **Table columns:** Rule key · Version · Status (Enabled / Disabled pending verification) · Effective · Source · Verified by.

**ADM-08 Rule editor**
- A parameters JSON editor with schema validation, a source citation, effective dates and a verifier name.
- "Enable" is disabled until a source and a verifier are present.
- **Save creates a new version:** a diff view against the previous version is shown before confirming.

**ADM-09 Metrics** (FR-041, P1)
- Funnel steps as a table with counts and step conversion.
- AI quality metrics (M-04, M-05, AI-012), each a stat tile with the value and the date measured.
- Cost per case.
- Reminder delivery.
- **No case-level data.**
- Charts are optional. If used, they follow a separate data-visualisation spec (DQ-04). Tables are acceptable for the MVP.

---

## 5. Visual design system

### 5.1 Colour

All contrast ratios below were **computed** with the WCAG 2.x relative-luminance formula.

#### 5.1.1 Neutrals ("paper and ink")

| Token | Hex | Use | Contrast |
|---|---|---|---|
| `color.paper` | #FBFAF7 | Page background | — |
| `color.surface` | #FFFFFF | Cards, inputs, letter canvas | — |
| `color.surface-sunken` | #F3F1EC | Wells, table headers, disabled fills | — |
| `color.ink` | #1C2321 | Primary text | 15.34 on paper; 16.01 on surface; 14.18 on sunken |
| `color.text-secondary` | #465250 | Secondary text | 7.79 on paper; 7.20 on sunken |
| `color.text-tertiary` | #5F6A67 | Helper text, metadata | 5.37 on paper; 4.97 on sunken (AA for body text) |
| `color.text-disabled` | #8B938F | Disabled labels only | 2.79 (permitted for disabled controls; never used for meaningful text) |
| `color.border` | #D8D4CB | Decorative dividers and card borders | 1.42 (decorative only) |
| `color.border-input` | #7D8783 | Input borders, checkboxes, radio outlines | 3.55 on paper; 3.71 on surface (meets the 3:1 non-text rule) |

#### 5.1.2 Brand

| Token | Hex | Use | Contrast |
|---|---|---|---|
| `color.primary` | #0E5C59 | Primary buttons, links, current step | 7.80 for white text on it; 7.47 as text on paper |
| `color.primary-hover` | #0A4846 | Hover | 10.35 for white text |
| `color.primary-active` | #083735 | Pressed | > 10 |
| `color.primary-subtle` | #E2EFEC | Selected backgrounds, current-step fill | 6.60 with primary text |
| `color.marigold` | #E3A23B | **Non-text accent only**: highlight bars, logo accent | 2.12 on paper; never used for text. Ink text on marigold is 7.24. |
| `color.highlight` | #FBE3B5 | Quoted-span highlight in the source viewer | Ink text on it > 12 |

#### 5.1.3 Semantic

| Token set | Text and icon | Subtle background | Border | Text contrast on white / subtle |
|---|---|---|---|---|
| `success` | #1E6B40 | #E4F1E8 | #8CC3A2 | 6.50 / 5.58 |
| `warning` | #7F4A00 | #FCF1DC | #E0A84A | 7.29 / 6.51 |
| `error` | #B3261E | #FCEBE9 | #E8A39D | 6.54 / 5.66 (white text on solid error: 6.54) |
| `info` | #1C5689 | #E6EFF8 | #9DBFE0 | 7.66 / 6.59 |

#### 5.1.4 Provenance colours (signature system, Section 7.1)

| Token | Text and icon | Background | Meaning |
|---|---|---|---|
| `prov.verified` | `success` text | `success` subtle | A quote checked against a stored source |
| `prov.document` | #465250 | #EEF0EF | Read from the user's documents and confirmed |
| `prov.user` | #465250 | #EEF0EF (plus a pencil icon) | The user typed or changed it |
| `prov.rule` | `info` text | `info` subtle | Deterministic rule check |
| `prov.ai` | #5A4790 | #EFEBF8 | AI-written suggestion; the reader must check it (7.67 / 6.54) |
| `prov.unverified` | `text-tertiary` | transparent, dashed `border-input` | An edited quote that is no longer verified |

**Rule:** provenance is never shown by colour alone. Every tag has an icon **and** a text label.

#### 5.1.5 Focus

`color.focus` is #1F4FC4: 6.77 on paper and 7.06 on surface.

Because it has low contrast against the primary teal (1.10), focus is drawn as a **double ring**: a 2 px `surface` inner ring, then a 2 px `focus` outer ring, offset outward. The outer ring therefore always sits on the page background, never on the teal.

### 5.2 Typography

#### 5.2.1 Families

| Token | Latin | Gujarati | Devanagari | Use |
|---|---|---|---|---|
| `font.ui` | Noto Sans | Noto Sans Gujarati | Noto Sans Devanagari | All UI |
| `font.document` | Noto Serif | Noto Serif Gujarati | Noto Serif Devanagari | Letter canvas, source excerpts, exported PDF and DOCX |
| `font.mono` | System monospace (`ui-monospace`) | — | — | Admin JSON editor and reference IDs only |

- **Loading:** self-hosted, subsetted variable WOFF2 (weights 400–700), with `font-display: swap`. Only the active script loads, together with the Latin face, because English quotes appear in every language.
- **Tabular figures:** `font-variant-numeric: tabular-nums` on amounts, dates and tables.

#### 5.2.2 Type scale

The root size is 16 px. Indic scripts get a size multiplier and taller line-heights (applied via `:lang(gu)` and `:lang(hi)`).

| Token | Size, mobile / ≥ 960 | Weight | Line-height Latin / Indic | Use |
|---|---|---|---|---|
| `type.display` | 30 / 40 | 700 | 1.2 / 1.4 | Home hero only |
| `type.h1` | 26 / 32 | 700 | 1.25 / 1.45 | Page titles |
| `type.h2` | 22 / 24 | 600 | 1.3 / 1.5 | Section titles |
| `type.h3` | 18 / 20 | 600 | 1.35 / 1.55 | Card titles |
| `type.body-lg` | 18 / 18 | 400 | 1.55 / 1.75 | Summaries, explanations |
| `type.body` | 16 / 16 | 400 | 1.5 / 1.7 | Default |
| `type.body-strong` | 16 / 16 | 600 | 1.5 / 1.7 | Emphasis (no italics) |
| `type.small` | 14 / 14 | 400 | 1.45 / 1.65 | Helper text, metadata. **Minimum size for Indic text.** |
| `type.label` | 14 / 14 | 600 | 1.4 / 1.6 | Form labels, badges |
| `type.caption` | 13 / 13 | 400 | 1.4 / — | Latin-only metadata (for example reference IDs). Never used for Indic. |
| `type.amount-lg` | 24 / 28 | 700, tabular | 1.2 | Amount at stake |
| `type.letter` | 16 / 17 | 400 (serif) | 1.6 / 1.8 | Letter canvas |

- **Indic size multiplier:** `type.body`, `type.body-lg` and `type.letter` are rendered at ×1.0625 under `:lang(gu)` and `:lang(hi)` (PROVISIONAL; tune against legibility testing).
- **Rules:**
  - No letter-spacing on Indic text.
  - No text transforms.
  - Reading line length is at most 70 characters (the 680 px column).

#### 5.2.3 Number and date formatting

| Kind | Format |
|---|---|
| Amounts | ₹ + Indian grouping: ₹1,20,000; ₹54,320.50 only when paise are present in the source |
| Dates (short) | DD/MM/YYYY |
| Dates (long) | 15 Nov 2026 / 15 નવે 2026 / 15 नव 2026 (localised month names) |
| Countdown | "12 days left", localised; "Today", "Passed 3 days ago" |

#### 5.2.4 Deadline urgency mapping

| Days remaining | Style |
|---|---|
| > 30 | Neutral (`text-secondary`) |
| 15–30 | `info` |
| 4–14 | `warning` |
| 0–3 | `error` |
| Passed | `error`, with text "Passed" |

Urgency is always shown with an icon and text as well as colour.

### 5.3 Spacing

The base unit is 4 px.

| Token | px |
|---|---|
| `space.0` | 0 |
| `space.1` | 4 |
| `space.2` | 8 |
| `space.3` | 12 |
| `space.4` | 16 |
| `space.5` | 20 |
| `space.6` | 24 |
| `space.8` | 32 |
| `space.10` | 40 |
| `space.12` | 48 |
| `space.16` | 64 |
| `space.20` | 80 |

**Usage:**

- Gap inside a component: 8–12.
- Card padding: 16 (mobile) / 24 (≥ 600).
- Gap between sections: 32 (mobile) / 48 (≥ 960).
- Gap between stacked form fields: 20.

### 5.4 Layout grid, content widths and breakpoints

| Breakpoint | Min width | Columns | Gutter | Outer margin | Notes |
|---|---|---|---|---|---|
| `bp.base` | 0 (designed at 360; must reflow at 320) | 4 | 16 | 16 | Mobile layouts |
| `bp.md` | 600 | 8 | 24 | 32 | Tablet; source drawer 480 |
| `bp.lg` | 960 | 12 | 24 | 32 | Case rail appears; SourcePanel as a column |
| `bp.xl` | 1280 | 12 | 32 | auto (centred) | Max page width 1200 |

| Token | Width | Use |
|---|---|---|
| `width.reading` | 680 | Prose, forms, FocusLayout |
| `width.content` | 760 | Case content column |
| `width.letter` | 794 | Letter canvas (A4 at 96 dpi) |
| `width.rail` | 240 | Case path rail |
| `width.panel` | 400 | SourcePanel column |
| `width.page` | 1200 | Max page width |

### 5.5 Borders and radii

| Token | Value | Use |
|---|---|---|
| `border.width.1` | 1 px | Cards, inputs, dividers |
| `border.width.2` | 2 px | Focus rings, selected RadioCards, error inputs |
| `border.width.4` | 4 px | Left accent bar on callouts and provenance margin rules |
| `radius.sm` | 4 px | Inputs, badges, chips, citation tabs |
| `radius.md` | 8 px | Buttons, cards, menus |
| `radius.lg` | 12 px | Dialogs, sheets (top corners only on bottom sheets) |
| `radius.full` | 9999 px | Pills, toggles, avatar initials |

### 5.6 Elevation

Borders carry structure. Shadows are reserved for layers that float.

| Token | Value | Use |
|---|---|---|
| `elevation.0` | none | Default cards (border only) |
| `elevation.1` | 0 1px 2px rgba(28,35,33,.08) | Sticky bars, hovered interactive cards |
| `elevation.2` | 0 4px 12px rgba(28,35,33,.12) | Dropdowns, popovers, toasts |
| `elevation.3` | 0 12px 32px rgba(28,35,33,.18) | Dialogs, bottom sheets, drawers |
| `scrim` | rgba(28,35,33,.48) | Behind dialogs and sheets |

### 5.7 Icons

- **Set:** Lucide (ISC licence), outline style, 1.75 px stroke.
- **Sizes:** `icon.sm` 16 (inline with small text), `icon.md` 20 (default, buttons), `icon.lg` 24 (navigation, empty states use 40 via `icon.xl`).
- **Accessibility:** icons are decorative (`aria-hidden`) unless they are the only content of a control, in which case the control has an `aria-label`.

### 5.8 Motion

| Token | Value | Use |
|---|---|---|
| `motion.duration.instant` | 0 ms | Reduced motion, and toggles |
| `motion.duration.fast` | 100 ms | Hover, press, colour changes |
| `motion.duration.base` | 200 ms | Expand/collapse, tab change, toast in |
| `motion.duration.slow` | 300 ms | Sheet, drawer and dialog enter |
| `motion.easing.standard` | cubic-bezier(0.2, 0, 0, 1) | Enter and move |
| `motion.easing.exit` | cubic-bezier(0.4, 0, 1, 1) | Exit (use 75% of the enter duration) |

Under `prefers-reduced-motion: reduce`:

- all transforms are removed;
- durations go to 0, except opacity fades of 100 ms or less;
- skeletons are static, with no shimmer;
- spinners become a static icon plus text "Working…".

### 5.9 Interaction states (applies to every interactive component)

| State | Treatment |
|---|---|
| Default | As specified per component |
| Hover (pointer only) | Primary: `primary-hover`. Secondary and ghost: `surface-sunken` fill. Cards: `elevation.1`. 100 ms. |
| Focus-visible | Double ring (5.1.5). Never removed. Not shown on mouse click (`:focus-visible`). |
| Active (pressed) | Primary: `primary-active`. Others: a darker sunken fill. No scale transform. |
| Selected | `primary-subtle` fill, 2 px `primary` border, and a check icon for RadioCards and chips |
| Disabled | `surface-sunken` fill, `text-disabled` label, `cursor: not-allowed`, plus `aria-disabled`. **The reason is always shown nearby** (helper text or tooltip with text). |
| Loading | Label retained, inline spinner at the start, control width fixed, `aria-busy="true"`; repeated clicks ignored |
| Error (inputs) | 2 px `error` border, an error icon and message below, `aria-invalid="true"` |
| Visited links | No change (an app, not a document collection) |

---

## 6. Component specifications

Every component consumes tokens only. No raw hex, px or ms values are allowed in component code (DAC-01).

### 6.1 Button
- **Variants:**

  | Variant | Appearance | Use |
  |---|---|---|
  | `primary` | Filled primary, white text | One per view |
  | `secondary` | Surface fill, 1 px `border-input`, ink text | Secondary actions |
  | `ghost` | Text only, primary colour | Tertiary actions |
  | `danger` | Filled error, white text | Destructive actions, used only inside a ConfirmDialog |
  | `danger-secondary` | Outlined in error colour | Entry point to a destructive action |
  | `link` | Inline text link | Inline navigation |

- **Sizes:**

  | Size | Height | Use |
  |---|---|---|
  | `md` (default) | 48 px | Everything except dense admin tables |
  | `sm` | 40 px | Admin tables only; the hit area is still at least 44 px through padding |

- **Props:** `variant`, `size`, `iconStart`, `iconEnd`, `loading`, `disabled` + `disabledReason`, `fullWidth` (default true on mobile action bars).
- **Behaviour:**
  - Activates on Enter or Space.
  - In the loading state, clicks are ignored.
  - The label never changes to "Success". Results appear in context.
- **Content:** labels are verb-first and at most about 4 words. Labels wrap to 2 lines in Indic text rather than truncate.

### 6.2 IconButton
- A 44×44 hit area, with an icon of 20 or 24.
- `aria-label` is required.
- Variants: `ghost` and `secondary`.

### 6.3 Status and banner components
- **Callout:** variants `info`, `success`, `warning`, `error`.
  - Structure: a 4 px left bar, icon, title (optional), body, optional action.
  - `role="status"` for info and success; `role="alert"` only when it appears as a result of a user action that failed.
- **StaleBanner:** a warning Callout pinned at the top of the content. Text: "Your details changed. Update findings / letter." Action: "Update". Downstream actions are disabled while it shows.
- **OfflineBanner:** a full-width bar under the header, in info tone: "You're offline. We'll continue when you're back."
- **StepState chip** (case path):

  | State | Marker |
  |---|---|
  | `done` | ✓ |
  | `current` | ● plus primary-subtle fill |
  | `needs attention` | ⚠ |
  | `locked` | 🔒, with the reason in a tooltip and an `aria-describedby` text |
  | `stale` | ↻ |
  | `not started` | ○ |

### 6.4 Form inputs

All inputs share:

- A visible label above the field. Placeholders are never used as labels.
- Optional helper text, and an error text slot.
- 48 px height, `radius.sm`, a 1 px `border-input` border.
- Error state as in 5.9.
- Label association through `for`/`id`; error text through `aria-describedby`.

**Validation timing:** on blur and on submit. After the first error, re-validate on change.

| Component | Specifics |
|---|---|
| **TextField** | Types: text, email, search. `maxLength` with a visible counter when relevant. |
| **PhoneField** [Scale-up, not in the MVP] | A non-editable "+91" prefix segment. `inputmode="numeric"`, `autocomplete="tel-national"`. Accepts only 10 digits; non-digits are stripped on paste. Kept for future phone sign-in (D-006). |
| **OTPField** (emailed sign-in code) | A single input: `autocomplete="one-time-code"`, `inputmode="numeric"`, maxlength 6, letter-spacing 0.3em for Latin digits. Auto-submits at 6 digits. |
| **DateField** | Three segments (DD, MM, YYYY), each numeric with its own visible label. Auto-advances. Validates real dates. Optional `allowUnknown` adds an "I don't know" checkbox that disables the segments. Optional `min`/`max` with messages. No native date picker in the MVP (inconsistent across low-end browsers). |
| **AmountField** | A "₹" prefix. `inputmode="decimal"`. Formats with Indian grouping on blur and shows raw digits while focused. Rejects negatives. |
| **Select** | The native `<select>` on mobile for reliability; a custom listbox on desktop (Section 6.10). Used for document type, relationship and category. |
| **Textarea** | Auto-grows to 8 lines, then scrolls. |
| **Checkbox** | A 24 px box inside a 44 px row hit area. The label is clickable. |
| **ConsentItem** | A checkbox, a bold title, a description, and a "Required" or "Optional" tag. |
| **RadioCardGroup** | Full-width cards (minimum height 56) with a title and optional description. Selected state as in 5.9. Arrow keys move the selection within the group, and the group has a `fieldset`/`legend`. |
| **Toggle (switch)** | `role="switch"`, with the label on the left and an "On"/"Off" text state beside it. |
| **PasswordField** | A show/hide toggle IconButton. `autocomplete="off"` for PDF passwords. |
| **RatingInput** | 5 radio buttons styled as numbered chips 1–5, with end labels "Not at all" and "Completely". Not stars. |
| **Fieldset / FormSection** | A legend as `type.h3` and grouped fields. |
| **ErrorSummary** | Appears at the top of a form on submit when there are 2 or more errors. Focus moves to it. It lists linked errors. `role="alert"`. |

### 6.5 Navigation components
- **PublicHeader / AppHeader:** see 2.2. Height is 56 (mobile) / 64 (desktop). Sticky. `elevation.1` once scrolled.
- **LanguageSwitcher:**
  - Desktop: a 3-option segmented control showing native names ("ગુજરાતી", "हिन्दी", "English") with `lang` attributes on each.
  - Mobile: an IconButton (globe) plus the current language code, which opens a menu.
  - Switching preserves the route and the form state.
- **CasePath:** rail (desktop) and compact bar plus bottom sheet (mobile). Items are links with `aria-current="step"`.
- **InPageTabs (anchor chips):** horizontally scrollable on mobile, with scroll-shadow edge hints. They update on scroll (IntersectionObserver).
- **Footer:** links, the disclaimer and the language switcher.
- **SkipLink:** "Skip to content", the first focusable element.

### 6.6 Dialogs and confirmation
- **Dialog:**
  - Mobile: a bottom sheet with a drag handle, which may also be dismissed by a Close button.
  - Desktop: a centred dialog, maximum 520 px wide.
  - Behaviour: `role="dialog"` with `aria-modal`, a labelled title, focus trapped, and focus returned to the trigger on close.
  - Escape closes it, except for destructive dialogs while busy.
- **ConfirmDialog:** title, consequence list, cancel (secondary) and confirm (primary or danger).
- **TypedConfirmDialog (destructive):**
  - Shows a random 4-digit code, for example "Type 2741 to confirm".
  - Input: numeric field.
  - The confirm button is disabled until the code matches.
  - Used for: delete case, delete account, withdraw consent.
- **PasswordDialog** (PDF unlock) and **ReportDialog** (Section 3, F10).
- **EventSheet:** RadioCards for the event type, then the dynamic fields, then Save.

### 6.7 Cards
- **Card:** a surface on `elevation.0` with a border and `radius.md`. Padding is `space.4`/`space.6`. Optional header, body and footer slots. Interactive cards have the whole card as the link target, with one link per card.
- **CaseCard:** Section 4 APP-01.
- **DocumentCard:** Section 4 CASE-01.
- **NextActionCard:** a primary-subtle background, `type.h3` title, one primary button and an optional deadline line.
- **StatTile (admin):** label, value (`type.amount-lg` style), and "measured on" date.

### 6.8 Tables, lists and filters
- **LedgerTable (desktop, ≥ 960):**
  - Columns are fixed in order. Amounts are right-aligned with tabular figures.
  - The status column holds an AuditStatusBadge.
  - A sticky header.
  - Rows expand for detail (button `aria-expanded`).
  - Footer row with totals.
  - Below 960 px, it becomes LineItemCards.
- **LineItemCard (mobile):** description (`body-strong`), the amounts row "Billed ₹… · Deducted ₹…", the insurer's reason as a quote, a clause-cited line, the badge, and an expand button for counter-points.
- **DataTable (admin):**
  - Column sort on header buttons (`aria-sort`).
  - A filter bar above: Select and DateRange (two DateFields).
  - Pagination with "1–25 of 132" and Prev/Next.
  - Empty and loading rows.
  - Rows are 48 px high.
- **Timeline:** a vertical list with a date (left on desktop, above on mobile), an icon per event type and a description.

### 6.9 Notifications
- **Toast:**
  - Only for transient confirmations of reversible actions ("Copied", "Report sent", "Quote edited – Undo").
  - Position: bottom-centre on mobile (above the action bar), bottom-left on desktop.
  - `role="status"`. Shown for 6 s, paused on hover or focus.
  - At most one visible at a time; a new toast replaces the old.
  - **Never** used for errors that need action, or for destructive outcomes.
- **Inline confirmation:** "Saved ✓" text next to the control, which fades after 3 s (removed immediately under reduced motion).
- **Email reminders** are outside this design system. A simple branded template with the case nickname and one deep-link button, with no medical details (FR-022), is listed in Section 9.6 as an asset.

### 6.10 Tabs and dropdowns
- **Tabs:**
  - `role="tablist"`. Arrow keys switch tabs (automatic activation).
  - The selected tab has a 2 px primary underline and weight 600.
  - Used for the letter language versions and the filing methods.
- **Menu (dropdown):**
  - A button with `aria-haspopup="menu"`.
  - Arrow navigation, typeahead, and Escape closes and returns focus.
  - `elevation.2`. Item height 44.
  - Used for: Download (PDF / Word / Copy as email), the DocumentCard overflow menu, and the account menu.
- **Listbox select (desktop custom):** WAI-ARIA combobox-select pattern.

### 6.11 AI response and evidence components

The signature set. Full UX rules are in Section 7.

| Component | Spec |
|---|---|
| **ProvenanceTag** | Pill (`radius.full`, `type.label`) with an icon and a label. Variants: `verified` ("Verified quote", seal-check icon), `document` ("From your documents", file icon), `user` ("You entered", pencil icon), `rule` ("Rule check", list-checks icon), `ai` ("Written by AI · check it", message-square-text icon), `unverified` ("Not verified", dashed outline). Text is localised. Not interactive. |
| **AuditStatusBadge** | Pill with an icon and a label. The 5 PRD statuses map as below (Section 7.4). Never colour-only. |
| **CitationTab** | An inline superscript button: a number in a tinted tab (`info` subtle, `radius.sm`), with an accessible name "Source 1: IRDAI Master Circular, Para 17(b)". A minimum 24×24 hit area inline. Opens the SourcePanel. |
| **CounterPointCard** | Header: the statement (`body`) with `ProvenanceTag ai`. A basis line: BasisTag (Regulation / Your policy / Your documents / Rule check). An "Applies if" condition Callout (info), when present. A Citations list of CitationTabs with source titles. Footer: "Something's wrong?" link. A deterministic-rule point uses `ProvenanceTag rule` instead of `ai`. |
| **ReasonCard** | The insurer's reason as a quote (`prov.document`), the category label, then its CounterPointCards, or an EmptyState "No grounded argument found". |
| **ExplanationBlock** | `type.body-lg` text with GlossaryTerms; `ProvenanceTag ai`; the amounts in it are rendered as `prov.document` inline spans (tabular, weight 600). |
| **GlossaryTerm** | Dotted underline; a button that opens a Popover (desktop) or a bottom sheet (mobile) with the definition and the English term. |
| **SourcePanel** | Section 6.12. |
| **ProtectedQuote** (editor) | Serif text in quotation marks, a 2 px `success` left rule, and a trailing CitationTab. After an edit, it becomes `unverified` styling and the tab is removed. |
| **AbstentionState** | An inline card: "We couldn't assess this item", with the reason ("The policy wording doesn't mention this item") and the recovery actions (FR-019). |
| **ProcessingSteps** | Section 7.6. |
| **DisclaimerLine** | `type.small`, `text-tertiary`, with an info icon: "ClaimSathi is a self-help drafting tool, not legal advice." |

### 6.12 SourcePanel
- **Header:** source title, issuer, version or effective date, and the clause or paragraph ID. A close IconButton.
- **Body:** the full chunk text in `font.document`, with the quoted span highlighted (`color.highlight` background plus a 2 px marigold bottom border, so the highlight is not shown by colour alone) and scrolled into view.
- **For user documents:** the page image crop with a highlight rectangle (2 px focus-blue outline), and a page number.
- **Translation section** (when the display language is not English): labelled "Translation (not the official text)", with `ProvenanceTag ai`.
- **Footer:** "Open full source" (for knowledge-base sources, if public, opens the official URL in a new tab).
- **Behaviour:** a desktop column, or a sheet or drawer on smaller screens. Focus moves into the panel heading on open and returns to the CitationTab on close. Esc closes it.
- **States:** loading (skeleton text); source unavailable ("This source couldn't be loaded. Retry"). A missing source is never treated as acceptable: report it as an error and log it.

### 6.13 Upload components
- **UploadActions (mobile):** two 56 px buttons: Take photo (camera icon) and Choose file.
- **UploadDropzone (desktop):**
  - A dashed `border-input` area at least 160 px high.
  - States: idle, drag-over (primary-subtle fill with a 2 px dashed primary border), and rejected-drag ("Only PDF, JPG, PNG").
  - It includes a real button, because dropzones are not keyboard targets.
- **UploadProgress:** a determinate bar driven by actual bytes uploaded, labelled "3.2 of 8.4 MB". Network retries show "Retrying (2 of 3)…".
- **File rules:** shown in helper text, and enforced client-side before upload (FR-008).

### 6.14 Progress indicators
- **ProgressBar (determinate):** only when a real ratio exists (bytes, documents processed out of total, questions answered). Has `aria-valuenow`.
- **Spinner:** 20 px, only inside buttons or alongside status text. Never alone without text.
- **Skeleton:** layout-matching blocks in `surface-sunken`.
- **StepCounter:** "Question 2 of 6", "Step 3 of 5".

### 6.15 Empty states, error boundaries and system pages
- **EmptyState:** a 40 px icon in `text-tertiary`, an `h3` title, one sentence, and one primary or secondary action. No illustrations.
- **ErrorState:** an error icon, a title naming what failed ("We couldn't load your findings"), what to do, a Retry button, and a reference ID (`type.caption`, selectable).
- **ErrorBoundary:** wraps each route segment. When it catches an error it renders ErrorState inside the layout, so navigation and the case path remain usable. It reports to error tracking without case content (NFR-019).
- **System pages:** SYS-01 to SYS-05 (Section 4).

---

## 7. AI-specific UX

### 7.1 Five kinds of truth, always labelled

| Kind | Source | Visual | Example |
|---|---|---|---|
| **Verified quote** | Knowledge-base or user-wording text that passed the verifier (AI-004) | `prov.verified`, serif quote, CitationTab | "giving reference to the specific terms…" [1] |
| **From your documents** | OCR extraction confirmed by the user | `prov.document` | Amount paid ₹2,10,500 |
| **You entered** | Typed or edited by the user | `prov.user` | First policy start 01/04/2019 |
| **Rule check** | Deterministic rule (FR-020, FR-016 rule checks, `NO_CLAUSE_CITED`) | `prov.rule` | "You've been insured for 74 months (more than 60)." |
| **Written by AI · check it** | Generated wording: explanations, counter-point statements, letter grounds, translations | `prov.ai` | "This deduction may not apply because…" |

**Rules:**

- A generated sentence that contains a verified quote shows **both** tags: the AI tag on the statement and the verified tag on the quote.
- Translations of quotes are always labelled AI and "not the official text".

### 7.2 Source visibility and evidence inspection
- Every CitationTab opens the SourcePanel with the exact highlighted span, in one tap or click (FR-029).
- "See where we read this" on extracted facts shows the page crop.
- Letters export citations as footnotes (FR-028), so the evidence survives outside the app.
- **"How we calculated this"** disclosures on deadlines and rule checks show the rule ID, the rule's plain-language text and its legal source with a link.

### 7.3 Uncertain or incomplete outputs
- **Low-confidence extraction:** a "Please check" flag, with the reason "This was hard to read" or "We didn't find this". **No percentages** (DD-07).
- **Abstention:** AbstentionState with a reason and recovery actions. It is never hidden, and never blank.
- **Limited mode:** a persistent info Callout at the top of Findings and Letter, naming what was skipped.
- **APPEARS_VALID:** shown plainly with a neutral badge and copy: "This deduction appears consistent with your policy." Unselected by default in the letter.
- **Partial output:** if some counter-points failed verification and were dropped, a small note under the section reads "Some suggestions were removed because we couldn't verify their sources." No details of the dropped content are shown.

### 7.4 Audit status visual mapping (FR-015)

| PRD status | Badge label (EN) | Icon | Tone | Default in letter |
|---|---|---|---|---|
| `NO_CLAUSE_CITED` | No clause cited | file-question | warning | Included |
| `CLAUSE_NOT_FOUND` | Cited clause not found | search-x | warning | Included |
| `CLAUSE_FOUND_QUESTIONABLE` | Clause found, may not apply | scale | info | Included |
| `CLAUSE_FOUND_APPEARS_VALID` | Appears consistent with policy | circle-check (neutral grey, not green) | neutral | Not included |
| `CANNOT_ASSESS` | Couldn't assess | circle-dashed | neutral (dashed outline) | Not included |

Green is deliberately **not** used for `APPEARS_VALID`. Green means "verified" or "done", and an appears-valid deduction is not good news for the user.

### 7.5 Retry and correction workflows

| Situation | Action available |
|---|---|
| Fact wrong | Edit in Check details. Downstream steps are marked stale. Update. |
| Reason misclassified | Select the right category in the ReasonCard ("Not right? Choose the reason"). This re-runs the analysis for that reason only. |
| Counter-point wrong | "Something's wrong?" (FR-035). The user can also untick it from the letter. |
| Letter wording | Edit freely. Edited quotes lose verification, visibly. |
| AI step failed | Retry. The deterministic fallback (a basic letter) is offered. |
| Photo unreadable | Retake or replace the document. |

### 7.6 Long-running tasks: ProcessingSteps
- **Structure:** a vertical list of **real** pipeline steps, each with a state (`waiting`, `in progress` with spinner and text, `done` ✓, `retrying`, `failed`).

  | Task | Steps |
  |---|---|
  | Reading | Reading documents (2 of 3) → Finding key details |
  | Analysis | Matching your policy wording → Checking deductions → Checking rules → Writing explanation |
  | Letter | Building letter → Checking every quote → Translating |

- **Elapsed time** text: "Started 40 s ago". **No estimated time remaining**, unless measured p50 data exists later.
- **After 20 s:** a "You can leave this page. We'll email you when it's ready" note (email only if the user consented to reminders; otherwise "Come back to My cases").
- **Live region:** `aria-live="polite"` announces step changes, throttled to at most one announcement every 10 s.
- **Forbidden:** percentage bars without a real ratio; fake step ticking; "Almost done" text not backed by state.

### 7.7 Human approval before consequential actions

| Action | Approval UI |
|---|---|
| Run analysis | "These details are correct" (FR-011) |
| First export of each letter version | "I've read this letter and it's correct" checkbox (AI-007) |
| Create Ombudsman pack | Acknowledge each warning (FR-020) |
| Sending or filing | **Not done by the app.** UI copy always says "You send this". Logging a send is a separate, explicit user action. |
| Delete or withdraw | TypedConfirmDialog |
| Admin publish or enable | Checkbox attestation plus a diff confirmation (FR-038, FR-039) |

### 7.8 Graceful degradation when AI services are unavailable
- **Upload, review and confirmation** keep working. Jobs queue (NFR-010).
- **Findings:** "Taking longer than usual" info state with an email follow-up.
- **Rule checks, deadlines and the Track page** keep working fully. They are deterministic.
- **Letter:** "Write a basic letter now", using deterministic grounds only and labelled "Basic letter: AI suggestions unavailable".
- **Translation:** English with a warning and Retry.
- **Status:** no global status page in the MVP. A dismissible info banner appears in the app when the provider has been degraded for more than 15 minutes (driven by the job-failure alert in NFR-020).

---

## 8. Accessibility and usability (WCAG 2.2 AA)

| Area | Specification |
|---|---|
| **Keyboard** | Every action is reachable by Tab in visual order. Skip link. Arrow keys within RadioCardGroup, Tabs, Menus and Listbox. Enter/Space activate. Escape closes overlays. No keyboard traps except intended modal focus traps. The editor follows standard contenteditable shortcuts, plus Ctrl/Cmd+Z for undo. |
| **Focus visible** | Double ring (5.1.5) on all focusable elements. Focus is never obscured by sticky bars (WCAG 2.4.11): `scroll-padding-top` and `scroll-padding-bottom` equal the sticky header and action bar heights. |
| **Focus management** | On route change, focus moves to the page `h1` and the title is announced. Dialogs focus their title on open and restore focus on close. After deleting a list item, focus goes to the next item, or to the list heading. |
| **Semantics** | Landmarks: `header`, `nav` (main nav, case path), `main`, `aside` (SourcePanel), `footer`. One `h1` per page with an ordered heading hierarchy. Lists for case cards and documents; tables only for tabular data. |
| **Language** | `<html lang>` matches the route locale. Embedded English quotes in Gujarati or Hindi pages carry `lang="en"`. The language switcher options carry their own `lang`. |
| **Labels** | Visible labels on all inputs. IconButtons have `aria-label`s in the current language. CitationTabs have descriptive accessible names. Badges have text, so icon meaning is never lost. |
| **Screen-reader behaviour** | Live regions: ProcessingSteps and autosave status (polite); ErrorSummary (alert, on submit only); toasts (status). Amounts are read naturally, so no visual-only separators carry meaning. Provenance tags are read as part of their content, for example "Written by AI, check it". Deadline urgency is conveyed in text. |
| **Forms and errors** | Errors appear as text next to the field, linked with `aria-describedby`, plus `aria-invalid`. An ErrorSummary appears on submit when there are 2 or more errors. Messages say how to fix the problem. Input is not cleared on error. Paste is allowed everywhere (no OTP or password paste blocking; WCAG 3.3.8). Information already entered is never asked for twice in a flow (WCAG 3.3.7). |
| **Targets** | Minimum 44×44 px, per PRD NFR-012 (stricter than WCAG 2.5.8's 24 px). At least 8 px between adjacent targets. Inline CitationTabs are at least 24×24 with spacing, which is an allowed inline exception. |
| **Dragging** | No functionality depends on dragging. The dropzone has a button alternative, and bottom sheets have a Close button (WCAG 2.5.7). |
| **Reduced motion** | As in 5.8. |
| **Zoom and reflow** | Content reflows at 320 CSS px with no horizontal scrolling, except the admin DataTable and the LedgerTable, which switch to cards. Text resizes to 200% without loss. No fixed heights on text containers. Text spacing overrides (WCAG 1.4.12) must not clip content. |
| **Large-text mode** | (FR-036) Scales the root font size to 20 px (×1.25). Layouts must hold, and is tested as a separate QA pass. |
| **Colour** | Contrast as computed in 5.1. No meaning carried by colour alone (badges, deadlines, provenance and the highlight all have icon or text redundancy). |
| **Timing** | The sign-in code expiry is visible. No other session or interaction time limits run without warning. Toasts pause on hover or focus, and nothing essential appears only in a toast. |
| **Readability** | Copy rules in 1.1. Glossary for terms. English explanations at about Grade 8 (NFR-013). |
| **Consistent help** | The help button sits in the same header position on every app screen (WCAG 3.2.6). |
| **Authentication** | Google sign-in or an emailed code that can be pasted; no cognitive puzzles or CAPTCHAs in the MVP (WCAG 3.3.8). |

---

## 9. Frontend implementation handoff

The tokens and components are framework-agnostic. If the v0 stack is confirmed (PRD NFR-026: Next.js, Tailwind CSS, shadcn/ui), map the tokens into the Tailwind theme and restyle the Radix-based shadcn primitives with these tokens. Do not keep shadcn's default visual style.

### 9.1 Design tokens (structured, DTCG-style JSON)

```json
{
  "color": {
    "paper": {"$value": "#FBFAF7"}, "surface": {"$value": "#FFFFFF"}, "surface-sunken": {"$value": "#F3F1EC"},
    "ink": {"$value": "#1C2321"}, "text-secondary": {"$value": "#465250"}, "text-tertiary": {"$value": "#5F6A67"},
    "text-disabled": {"$value": "#8B938F"}, "border": {"$value": "#D8D4CB"}, "border-input": {"$value": "#7D8783"},
    "primary": {"$value": "#0E5C59"}, "primary-hover": {"$value": "#0A4846"}, "primary-active": {"$value": "#083735"},
    "primary-subtle": {"$value": "#E2EFEC"}, "on-primary": {"$value": "#FFFFFF"},
    "marigold": {"$value": "#E3A23B"}, "highlight": {"$value": "#FBE3B5"}, "focus": {"$value": "#1F4FC4"},
    "success": {"text": {"$value": "#1E6B40"}, "bg": {"$value": "#E4F1E8"}, "border": {"$value": "#8CC3A2"}},
    "warning": {"text": {"$value": "#7F4A00"}, "bg": {"$value": "#FCF1DC"}, "border": {"$value": "#E0A84A"}},
    "error":   {"text": {"$value": "#B3261E"}, "bg": {"$value": "#FCEBE9"}, "border": {"$value": "#E8A39D"}},
    "info":    {"text": {"$value": "#1C5689"}, "bg": {"$value": "#E6EFF8"}, "border": {"$value": "#9DBFE0"}},
    "prov": {
      "verified":   {"text": {"$value": "{color.success.text}"}, "bg": {"$value": "{color.success.bg}"}},
      "document":   {"text": {"$value": "#465250"}, "bg": {"$value": "#EEF0EF"}},
      "user":       {"text": {"$value": "#465250"}, "bg": {"$value": "#EEF0EF"}},
      "rule":       {"text": {"$value": "{color.info.text}"}, "bg": {"$value": "{color.info.bg}"}},
      "ai":         {"text": {"$value": "#5A4790"}, "bg": {"$value": "#EFEBF8"}},
      "unverified": {"text": {"$value": "{color.text-tertiary}"}, "border": {"$value": "{color.border-input}"}}
    },
    "scrim": {"$value": "rgba(28,35,33,0.48)"}
  },
  "font": {
    "family": {
      "ui":       {"$value": "'Noto Sans', 'Noto Sans Gujarati', 'Noto Sans Devanagari', system-ui, sans-serif"},
      "document": {"$value": "'Noto Serif', 'Noto Serif Gujarati', 'Noto Serif Devanagari', Georgia, serif"},
      "mono":     {"$value": "ui-monospace, 'SFMono-Regular', Consolas, monospace"}
    },
    "weight": {"regular": {"$value": 400}, "medium": {"$value": 500}, "semibold": {"$value": 600}, "bold": {"$value": 700}},
    "indic-scale": {"$value": 1.0625}
  },
  "type": {
    "display":   {"size": {"base": "30px", "lg": "40px"}, "weight": 700, "lineHeight": {"latin": 1.2,  "indic": 1.4}},
    "h1":        {"size": {"base": "26px", "lg": "32px"}, "weight": 700, "lineHeight": {"latin": 1.25, "indic": 1.45}},
    "h2":        {"size": {"base": "22px", "lg": "24px"}, "weight": 600, "lineHeight": {"latin": 1.3,  "indic": 1.5}},
    "h3":        {"size": {"base": "18px", "lg": "20px"}, "weight": 600, "lineHeight": {"latin": 1.35, "indic": 1.55}},
    "body-lg":   {"size": {"base": "18px"}, "weight": 400, "lineHeight": {"latin": 1.55, "indic": 1.75}},
    "body":      {"size": {"base": "16px"}, "weight": 400, "lineHeight": {"latin": 1.5,  "indic": 1.7}},
    "small":     {"size": {"base": "14px"}, "weight": 400, "lineHeight": {"latin": 1.45, "indic": 1.65}},
    "label":     {"size": {"base": "14px"}, "weight": 600, "lineHeight": {"latin": 1.4,  "indic": 1.6}},
    "caption":   {"size": {"base": "13px"}, "weight": 400, "lineHeight": {"latin": 1.4}},
    "amount-lg": {"size": {"base": "24px", "lg": "28px"}, "weight": 700, "lineHeight": {"latin": 1.2}, "numeric": "tabular-nums"},
    "letter":    {"size": {"base": "16px", "lg": "17px"}, "weight": 400, "family": "{font.family.document}", "lineHeight": {"latin": 1.6, "indic": 1.8}}
  },
  "space": {"0": "0", "1": "4px", "2": "8px", "3": "12px", "4": "16px", "5": "20px", "6": "24px", "8": "32px", "10": "40px", "12": "48px", "16": "64px", "20": "80px"},
  "breakpoint": {"md": "600px", "lg": "960px", "xl": "1280px"},
  "width": {"reading": "680px", "content": "760px", "letter": "794px", "rail": "240px", "panel": "400px", "drawer": "480px", "page": "1200px", "dialog": "520px"},
  "grid": {"base": {"columns": 4, "gutter": "16px", "margin": "16px"}, "md": {"columns": 8, "gutter": "24px", "margin": "32px"}, "lg": {"columns": 12, "gutter": "24px", "margin": "32px"}, "xl": {"columns": 12, "gutter": "32px"}},
  "border": {"width": {"1": "1px", "2": "2px", "4": "4px"}},
  "radius": {"sm": "4px", "md": "8px", "lg": "12px", "full": "9999px"},
  "elevation": {
    "0": "none",
    "1": "0 1px 2px rgba(28,35,33,0.08)",
    "2": "0 4px 12px rgba(28,35,33,0.12)",
    "3": "0 12px 32px rgba(28,35,33,0.18)"
  },
  "icon": {"sm": "16px", "md": "20px", "lg": "24px", "xl": "40px", "stroke": 1.75},
  "size": {"control": {"md": "48px", "sm": "40px"}, "target-min": "44px", "header": {"base": "56px", "lg": "64px"}},
  "motion": {
    "duration": {"instant": "0ms", "fast": "100ms", "base": "200ms", "slow": "300ms"},
    "easing": {"standard": "cubic-bezier(0.2, 0, 0, 1)", "exit": "cubic-bezier(0.4, 0, 1, 1)"}
  },
  "focus": {"ring": {"inner": {"width": "2px", "color": "{color.surface}"}, "outer": {"width": "2px", "color": "{color.focus}"}}},
  "z": {"base": 0, "sticky": 100, "drawer": 200, "dropdown": 300, "dialog": 400, "toast": 500}
}
```

**CSS custom properties** are generated from these tokens, for example `--color-primary` and `--space-4`. Indic line-heights are applied with:

```css
:lang(gu), :lang(hi) { --lh-body: 1.7; --fs-body: calc(16px * 1.0625); }
```

### 9.2 Component inventory and suggested hierarchy

```
primitives/      Button, IconButton, Link, TextField, OTPField, DateField, AmountField,
                 Select, Listbox, Textarea, Checkbox, Toggle, RadioCardGroup, PasswordField,
                 RatingInput, Tabs, Menu, Popover, Dialog, Sheet, Tooltip(text only), Spinner,
                 ProgressBar, Skeleton, Badge, Pill, Icon, VisuallyHidden
patterns/        Callout, StaleBanner, OfflineBanner, Toast, ErrorSummary, Fieldset, ConsentItem,
                 ConfirmDialog, TypedConfirmDialog, EmptyState, ErrorState, ErrorBoundary,
                 StepCounter, DataTable, Pagination, FilterBar, Timeline, CopyField, ContentsNav,
                 LanguageSwitcher, SkipLink, DisclaimerLine
evidence/        ProvenanceTag, CitationTab, SourcePanel, SourceExcerpt, PageCropViewer,
                 GlossaryTerm, ProtectedQuote, AuditStatusBadge, BasisTag
features/
  auth/          SignInForm, VerifyCodeForm
  onboarding/    LanguagePicker, ConsentForm
  cases/         CaseCard, CaseList, EligibilityWizard, CasePath (Rail + CompactBar)
  documents/     UploadActions, UploadDropzone, UploadProgress, DocumentCard, PasswordDialog
  details/       FieldReviewRow, FieldGroup, DecisionLetterChooser, LedgerTable, LineItemCard, LineItemSheet
  findings/      ExplanationBlock, WordingSourceLine, StatusLedger, ReasonCard, CounterPointCard,
                 AbstentionState, EvidenceChecklist, ProcessingSteps, ReportDialog
  letter/        IncludeItemsForm, LetterEditor, LetterToolbar, AutosaveStatus, ReviewBar, DownloadMenu
  track/         NextActionCard, DeadlineList, StageCard, EventSheet, RuleCheckList, OmbudsmanPack
  settings/      SettingsSection, SupportAccessToggle, DataExportButton, DangerZone
  admin/         AdminNav, ReviewQueueTable, ReviewDecisionForm, SourceForm, ChunkPreviewList,
                 RuleTable, RuleEditor (JSON + diff), StatTile, FunnelTable
layouts/         PublicLayout, ReadingLayout, AuthLayout, FocusLayout, AppLayout, CaseLayout,
                 EditorLayout, AdminAuthLayout, AdminLayout, MinimalLayout
```

### 9.3 Route-to-layout mapping

| Layout | Routes | Regions |
|---|---|---|
| PublicLayout | PUB-01 to PUB-06 | PublicHeader · main · Footer |
| ReadingLayout (inside PublicLayout) | PUB-02, PUB-03, PUB-07 to PUB-09 | ContentsNav · prose 680 |
| AuthLayout | AUTH-01, AUTH-02, ONB-01, ONB-02 | Logo bar + LanguageSwitcher · centred 440 card (mobile full-bleed) |
| AppLayout | APP-01, ACC-01, ACC-02 | AppHeader · main 760 · Footer (compact) |
| FocusLayout | APP-02, APP-03, CASE-11 | AppHeader (minimal, with exit) · main 680 · sticky action bar |
| CaseLayout | CASE-01 to CASE-05, CASE-07 to CASE-09, CASE-12 | AppHeader · CasePath · main 760 · SourcePanel · DisclaimerLine · action bar |
| EditorLayout | CASE-06, CASE-10 letter section | AppHeader · LetterToolbar · canvas 794 · SourcePanel · ReviewBar |
| AdminAuthLayout / AdminLayout | ADM-* | AdminNav (left 220) · main fluid (min 1024) |
| MinimalLayout | SYS-01 to SYS-05 | Logo · message · one action |

### 9.4 Page-to-component mapping

| Page | Key components |
|---|---|
| PUB-01 | Button, StepCounter-style strip, StatusLedger (static sample), AuditStatusBadge, Callout, DisclaimerLine |
| PUB-04 | StatTile-style panel, EmptyState |
| PUB-05 | Card ×3, Callout(warning), Link(external) |
| PUB-06 | TextField(search), definition list, EmptyState |
| AUTH-01, AUTH-02 | SignInForm (GoogleButton, TextField[email], Button), VerifyCodeForm (OTPField), Callout(error) |
| ONB-01 | LanguagePicker (RadioCardGroup) |
| ONB-02 | ConsentForm (Accordion sections, ConsentItem ×2, TextField(email)), Callout |
| APP-01 | CaseList, CaseCard, EmptyState, Button |
| APP-02 | EligibilityWizard (RadioCardGroup, DateField, Select, TextField), StepCounter, Callout(info) |
| CASE-01 | UploadActions/Dropzone, DocumentCard, UploadProgress, PasswordDialog, Callout, Toast |
| CASE-02 | FieldGroup, FieldReviewRow, ProvenanceTag, PageCropViewer (in SourcePanel), DecisionLetterChooser, ErrorSummary, ConfirmDialog |
| CASE-03 | LedgerTable / LineItemCard, LineItemSheet, Callout(warning) |
| CASE-04 | ProcessingSteps, ExplanationBlock, WordingSourceLine, StatusLedger, ReasonCard, CounterPointCard, CitationTab, SourcePanel, AbstentionState, EvidenceChecklist, ReportDialog, StaleBanner |
| CASE-05 | IncludeItemsForm (Checkbox list with AuditStatusBadge), RadioCardGroup(language), ProcessingSteps |
| CASE-06 | LetterEditor, ProtectedQuote, CitationTab, Tabs, AutosaveStatus, ReviewBar, DownloadMenu, SourcePanel, Dialog("Did you send it?") |
| CASE-07 | NextActionCard, DeadlineList, StageCard, Timeline, EventSheet |
| CASE-08 | CopyField, Link(external, tel) |
| CASE-09 | RuleCheckList, Checkbox(acknowledge), Callout(info signatory) |
| CASE-10 | Callout, LetterEditor, CopyField, EvidenceChecklist (enclosures), Tabs (filing methods) |
| CASE-11 | RadioCardGroup, AmountField, RatingInput, Textarea |
| CASE-12, ACC-01, ACC-02 | SettingsSection, Toggle, SupportAccessToggle, DataExportButton, DangerZone, TypedConfirmDialog |
| ADM-03 to ADM-09 | DataTable, FilterBar, Pagination, ReviewDecisionForm, SourceForm, ChunkPreviewList, RuleEditor, StatTile, FunnelTable |

### 9.5 Responsive behaviour summary

| Element | < 600 | 600–959 | ≥ 960 |
|---|---|---|---|
| Case path | Compact sticky bar + sheet | Compact bar + sheet | Left rail |
| Primary action | Sticky bottom bar, full width | Sticky bottom bar | Inline at the end of content, plus a sticky bar on long pages (Findings, Letter) |
| SourcePanel | Bottom sheet 90 vh | Right drawer 480 overlay | Right column 400, pushes content |
| Ledger | LineItemCards | LineItemCards | LedgerTable |
| Dialogs | Bottom sheet | Centred 520 | Centred 520 |
| Eligibility | One question per screen | One question per screen | Single scrolling form |
| Letter canvas | Full width, 16 padding | Full width, 32 padding | 794 sheet centred |
| Admin | Not supported. Message: "Use a wider screen." | Not supported | ≥ 1024 |

### 9.6 Asset requirements

| Asset | Spec | Status |
|---|---|---|
| Wordmark | Live text, not an image: "ClaimSathi", `font.ui` 700, `color.primary`, 20 px. Accessible name "ClaimSathi home". | Specified (DD-12). **No logo in the MVP.** |
| Favicon set (interim) | Letter "C" in Noto Sans Bold, `color.on-primary` on a `color.primary` square, `radius.sm`. SVG + 32 px PNG + 180 px apple-touch icon. | To be produced from the spec; replace if a logo is made later |
| Fonts | Noto Sans/Serif (Latin, Gujarati, Devanagari) variable WOFF2, subsetted to the scripts used. SIL OFL. | Available (Google Fonts; self-host) |
| Icons | Lucide (ISC), tree-shaken | Available |
| PDF and DOCX letter template | Serif document fonts embedded. A4, 25 mm margins. Footnote style. Footer disclaimer. Page numbers "Page X of Y". | To be built with the export service (FR-028) |
| Email templates (sign-in code; reminders) in en, gu, hi | Plain text + simple HTML; text wordmark (no logo, DD-12); the code email holds only the code and expiry; reminders hold one deep-link button and no medical details | To be built |
| Open Graph image | 1200×630, text-only: wordmark + tagline per language on `color.paper` | To be produced from the spec |
| Illustrations / photos | None in the MVP (DD-06) | — |

### 9.7 Performance budget (supports PRD NFR-003)

All values are PROVISIONAL.

| Item | Budget |
|---|---|
| Initial JS per route | ≤ 170 KB gzip |
| Fonts per script, subsetted variable WOFF2 (UI) | ≤ 120 KB, loaded on demand |
| Serif fonts | Loaded only on the letter and source routes |
| Public pages | No client-side JS beyond the language switcher and menu |
| Icons | Inlined SVG; no icon font |
| Images | Only document thumbnails, generated server-side at ≤ 30 KB each |

### 9.8 Animation specifications

| Interaction | Property | Duration / easing | Reduced motion |
|---|---|---|---|
| Button hover / press | background-color | fast / standard | instant |
| Expand / collapse (ledger rows, accordions) | height (via grid-rows), opacity | base / standard | instant |
| Tabs change | underline position | base / standard | instant |
| Bottom sheet / drawer enter | transform translateY/X + opacity | slow / standard; exit 225 ms / exit | opacity fade 100 ms |
| Dialog enter | opacity + translateY(8px) | base / standard | opacity 100 ms |
| Toast in / out | opacity + translateY(8px) | base / standard | opacity 100 ms |
| SourcePanel column open | width (desktop) | base / standard | instant |
| Highlight scroll-into-view | scroll | `smooth` | `auto` |
| Step done ✓ | icon swap only | — | — |
| Skeleton | opacity pulse 1.2 s loop | — | static |

### 9.9 Visual QA checklist

- [ ] No raw colour, spacing, radius, shadow or duration values in component styles (lint rule; token references only).
- [ ] Each page reviewed in `en`, `gu` and `hi` at 360, 768, 1280 px, and at 320 px for reflow.
- [ ] Large-text mode reviewed on every user page.
- [ ] Longest translated strings fit: buttons wrap correctly; no truncated Indic text.
- [ ] Gujarati and Devanagari conjuncts and matras render correctly in the UI, PDF and DOCX (fixture strings provided by a native reviewer).
- [ ] Amounts use Indian grouping, tabular figures and right alignment in tables.
- [ ] Every interactive element shows the focus ring; hover, active, disabled and selected states are present.
- [ ] Every disabled primary action shows its reason.
- [ ] Every screen has designed empty, loading, error and success states (Section 4), plus stale and offline where applicable.
- [ ] Provenance tags appear on all facts, quotes and AI text on CASE-02, CASE-04, CASE-06 and CASE-10.
- [ ] No percentage confidence values, fake progress or ETA text anywhere.
- [ ] Disclaimer line present on CASE-04, CASE-06, CASE-10 and in exports.
- [ ] Only one primary button per view.
- [ ] External links show the external icon and open in a new tab with `rel="noopener"`.

---

## 10. Design acceptance criteria

| ID | Check | Method | Pass condition |
|---|---|---|---|
| DAC-01 | Token discipline | Stylelint/ESLint rule rejecting raw hex, px (except 0 and 1px borders via tokens) and ms in component styles | 0 violations |
| DAC-02 | Colour contrast | Automated (axe) + manual check of token pairs | Text ≥ 4.5:1; large text and non-text UI ≥ 3:1; 0 axe contrast violations |
| DAC-03 | Automated accessibility | axe-core on every route in all 3 languages, in default and error states | 0 serious or critical violations |
| DAC-04 | Keyboard | Manual script: complete F1 (sign-in to download) and F2 with keyboard only | Completed without a mouse; focus always visible and never obscured |
| DAC-05 | Screen reader | NVDA + Chrome (desktop) and TalkBack + Chrome (Android): run F1 in English and Hindi, and the CASE-04 and CASE-06 reading in Gujarati | All controls named; processing and errors announced; `lang` switches pronounced correctly |
| DAC-06 | Reflow and zoom | 320 px viewport and 200% text zoom on all user pages | No horizontal scroll (except the noted tables that switch to cards); no clipped text |
| DAC-07 | Touch targets | Automated measurement on mobile builds | All targets ≥ 44×44, except documented inline CitationTabs ≥ 24×24 |
| DAC-08 | Responsive layouts | Visual regression screenshots at 360, 768, 1280 for every page × 3 languages | Matches approved baselines; mobile uses the mobile patterns in 9.5 |
| DAC-09 | State completeness | Story or fixture per state listed in Section 4 for each page | 100% of listed states have a rendered fixture |
| DAC-10 | AI honesty | Review of all AI-related screens | 0 confidence percentages; 0 untagged AI text; 0 progress indicators without a real ratio; 0 "success" messages before the result exists |
| DAC-11 | Provenance coverage | Automated DOM check on CASE-04 and CASE-06 fixtures | Every counter-point, quote and fact element has a ProvenanceTag or a CitationTab |
| DAC-12 | Reduced motion | Run with `prefers-reduced-motion: reduce` | No transforms or shimmer; only opacity ≤ 100 ms |
| DAC-13 | Performance | Lighthouse mobile (Slow 4G, mid-tier device) on PUB-01, APP-01, CASE-04, against a **warm** service | LCP ≤ 3.0 s (NFR-003); budgets in 9.7 met. Cold-start LCP is recorded separately (₹0 hosting scales to zero). |
| DAC-14 | Indic rendering | Native-reviewer check of UI, PDF and DOCX fixtures | Sign-off recorded for `gu` and `hi` |
| DAC-15 | Destructive safety | Interaction test | Delete case, delete account and withdraw consent each require the TypedConfirmDialog; Escape is disabled while busy |
| DAC-16 | Traceability | Review | Every route in 2.3 maps to a PRD FR or a stated usability need; no unapproved functionality |
| DAC-17 | Interaction consistency | Heuristic review | One primary action per view; verb-first labels; disabled controls explain why; toasts never carry required information |

---

## 11. Open design questions

| ID | Question | Default until decided |
|---|---|---|
| DQ-01 | Run a visual audit of the competitor UIs (fairClaims, ClaimAssist Pro, ClaimBhai AI, UnDeny) to confirm the visual differentiation in 1.5? | Proceed with this system; audit in the validation sprint |
| DQ-02 | Western Arabic numerals in Gujarati and Hindi UI and letters (DD-03)? | **Resolved 15 Oct 2026: yes, 0–9 everywhere** |
| DQ-03 | Admin console English-only (DD-08)? | **Resolved 15 Oct 2026: yes, English only** |
| DQ-04 | Do admin metrics need charts in the MVP (FR-041 is P1)? | Tables and stat tiles only |
| DQ-05 | Logo? | **Resolved 15 Oct 2026: no logo for now.** Text wordmark (DD-12). Revisit after the MVP. |
| DQ-06 | Usability-test the three priority flows (F1, F2, F3) with 5 users per language before high-fidelity polish? | Recommended during the concierge pilot (PRD Section 10.1) |
| DQ-07 | Tune the Indic size multiplier (×1.0625) and line-heights after legibility testing on low-end phones? | Keep the PROVISIONAL values |
