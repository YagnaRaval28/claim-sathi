# ClaimSathi

**A free assistant, in English, Gujarati and Hindi, that helps Indian policyholders challenge rejected or partly paid health insurance claims.**

ClaimSathi reads the insurer's letter, flags deductions that cite no policy clause, quotes the applicable IRDAI rules with verified citations, drafts the grievance letter and the Ombudsman complaint, and tracks the legal deadlines.

| | |
|---|---|
| Category | AI/ML/GenAI |
| Status | Working prototype |
| Languages | English, Gujarati, Hindi |
| Cost to users | Free, no success fee |
| Data residency | India |

---

## The problem and why it matters

Every year, Indian health insurers leave huge amounts unpaid: ₹26,037 crore in FY24, of which ₹15,100 crore was partial deductions, often made without citing any policy clause. Most policyholders don't know which rules protect them, how to write a proper grievance, or when they can approach the Insurance Ombudsman. Many give up, or pay agents for help that is free.

The official system works when used correctly. In FY25, health made up 61.5% of all Ombudsman complaints (32,655), and about 53% of health disposals went in the policyholder's favour. Yet 5,047 health complaints were dismissed as "non-entertainable", mostly for procedural mistakes such as filing too early or too late.

ClaimSathi is a free assistant in English, Gujarati and Hindi. It reads the insurer's letter, flags deductions with no clause cited, quotes the applicable IRDAI rules with verified citations, drafts the grievance letter and the Ombudsman complaint, and tracks Rule 14 deadlines so complaints aren't lost on technicalities.

It helps families recover money they are owed. It makes free official channels usable for non-English speakers and reduces dependence on paid middlemen. And it pushes insurers towards clearer, rule-compliant decisions.

*Sources: Council for Insurance Ombudsmen Annual Report 2024–25; Lok Sabha replies (see `docs/01-discovery/competitor-research.md`, sources S31 and S33).*

---

## The solution and its key features

ClaimSathi is a free web app, in English, Gujarati and Hindi, that guides a policyholder from a cut or rejected health insurance claim to a properly filed complaint.

### How it works

1. **Upload the insurer's letter.** AI reads it and extracts the claim details, deductions and stated reasons. The user checks and confirms every detail; nothing unconfirmed is used.
2. **See the findings.** Fixed, rule-based checks flag every deduction or reason with no policy clause cited, as required by the IRDAI Master Circular (Para 17(b)). They also apply the five-year moratorium and the rule that a full rejection needs the claims review committee's approval. Every rule quoted is matched word for word against its source, and the user can open it.
3. **Get the letter.** ClaimSathi drafts a firm, polite grievance letter from the confirmed facts and verified rules. The user can edit it, and download it as PDF or Word or copy it as email text.
4. **Track deadlines.** The user logs when the letter was sent. The app works out when they can approach the Insurance Ombudsman and the last date to file, sends reminders, and checks all six Rule 14 conditions before creating the Ombudsman complaint pack.

### Why it solves the problem

- Rules, not AI, decide deadlines, eligibility and deduction audits, so users never get invented legal claims.
- The Rule 14 checks prevent complaints being dismissed on technicalities.
- It points users to free official channels and warns against paid middlemen.
- Data stays in India and is encrypted, and users can download or delete it at any time.

---

## What makes it different

Existing options charge success fees or just generate a letter. Insurance Samadhan takes 20% plus GST, Claimsify 12%, and ClaimAssist Pro 15%. Fast AI tools produce an appeal "in 2 minutes" but stop there, while the government's Bima Bharosa portal only routes complaints. ClaimSathi is different in six ways:

1. **Deduction-level audit.** It checks every deducted line for a cited policy clause, as the IRDAI Master Circular (Para 17(b)) requires, and demands the clause wherever it's missing. Partial deductions are worth more than outright rejections (₹15,100 crore vs ₹10,937 crore in FY24).
2. **Ombudsman Rule 14 checks.** Before filing, it verifies all six conditions: prior written complaint, the one-month wait, the one-year limit, no court case, the ₹50 lakh cap, and the right signatory. About 5,000 health complaints a year are dismissed on such technicalities, and no competitor checks for them.
3. **Verified citations, not AI guesses.** Code matches every quoted rule word for word against its source; anything that doesn't match is dropped.
4. **Deadlines decided by rules.** It tracks the whole journey (insurer, Bima Bharosa, Ombudsman) with reminders, using fixed rules rather than AI.
5. **Gujarati and Hindi**, not just English.
6. **Free forever**, with no success fee, and data kept in India.

---

## Technology stack, architecture and components

**Architecture:** a modular monolith. A Next.js web app talks to a FastAPI backend, backed by PostgreSQL. All personal data stays in India.

### Technology stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (React 19, TypeScript, Tailwind CSS), in English, Gujarati and Hindi |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic migrations |
| Database | PostgreSQL with pgvector (Supabase, Mumbai region) |
| AI | Google Gemini 2.5 Flash on Vertex AI (asia-south1), called through a gateway that checks every response against a fixed schema; the model has no tools |
| OCR (planned, for photos and scans) | Google Document AI (asia-south1) |
| Background jobs | Transactional outbox with Google Cloud Tasks |
| Storage | Private S3-compatible buckets |
| Email | Amazon SES (Mumbai) |
| Documents | WeasyPrint (PDF), python-docx (Word) |
| Hosting | Google Cloud Run (Mumbai), run at zero cost on free tiers and trial credits |

### Major functional components

1. **Sign-in:** Google sign-in or an emailed 6-digit code, secure HttpOnly sessions and CSRF protection.
2. **Documents:** secure PDF upload with file-type checks, size limits and text extraction.
3. **Extraction:** AI proposes the claim details; code accepts only values found word for word in the letter, and the user confirms each one.
4. **Rules engine:** deterministic code for deduction audits, IRDAI rules (moratorium, review-committee approval) and the six Ombudsman Rule 14 checks.
5. **Verification:** a citation verifier and a number scanner. Any quote or amount not traceable to its source is dropped.
6. **Letters:** grievance letter and Ombudsman complaint pack, with an editor that protects verified quotes.
7. **Tracking:** case events, deadline calculation, and email and in-app reminders.
8. **Data controls:** export, delete and automatic retention.
9. **Admin console:** TOTP sign-in, review queue, knowledge base and versioned rules.

**Security and quality:** personal fields are encrypted (AES-GCM); logs keep only approved fields; each user can see only their own cases; and 158 automated backend tests plus browser tests run in CI.

---

## Current status

**Working prototype.** All core user journeys are built and tested locally:

- sign-in, upload, findings, letter, tracking and the Ombudsman pack;
- data controls and the admin console.

**Next steps:**

- switch on the live AI model on Vertex AI (it currently runs on a stand-in with recorded answers for two sample letters);
- add OCR for photos and scans;
- deploy to the cloud;
- get legal review of the privacy notice and terms;
- start a closed beta.

---

## Impact and potential to scale

### Impact

Health insurers in India left ₹26,037 crore of claims unpaid in FY24, including ₹15,100 crore in partial deductions that were often made without citing any policy clause. When policyholders use the official system correctly, they often win: about 53% of health complaints decided by the Insurance Ombudsman in FY25 went in their favour. Yet around 5,000 health complaints a year are dismissed for procedural mistakes alone.

ClaimSathi turns that gap into recovered money for families. It explains decisions in their own language, writes the right letter, and keeps them within the legal deadlines, so a valid complaint is not lost on a technicality. It also reduces dependence on agents who charge 12–22% of the recovered amount, and points people to the free official channels instead. Over time, insurers face more clearly reasoned, rule-based challenges, which pushes them towards clearer, compliant decisions.

### Scale potential

- **Users:** it is a free web app that works on any phone browser. The architecture runs at near-zero cost per user and scales automatically on Google Cloud Run.
- **Languages:** English, Gujarati and Hindi today; the translation and rules layers are built to add more Indian languages.
- **Communities:** NGOs, consumer groups and employer HR teams can use it to help members who can't navigate the process alone.
- **Industry:** the same rules engine, citation verifier and deadline tracker can extend to other kinds of insurance and other grievance systems governed by written rules.

---

## Run it locally

Full instructions, including running without Docker, are in [`docs/00-governance/development-setup.md`](docs/00-governance/development-setup.md). In short:

```bash
# API (Python 3.12, uv)
cd apps/api
uv sync
uv run alembic upgrade head
uv run python -m claimsathi.seeds --env local
uv run uvicorn --factory claimsathi.main_api:create_app --port 8000

# Web (Node 22, pnpm via corepack)
cd apps/web
corepack pnpm@10.34.7 install
corepack pnpm@10.34.7 dev    # http://localhost:3000
```

Sign-in codes are delivered to a local mail catcher (Mailpit) at http://localhost:8025. Sample synthetic letters are in `eval/fixtures/documents/`.

## Repository layout

| Path | Contents |
|---|---|
| `apps/web` | Next.js frontend |
| `apps/api` | FastAPI backend, migrations and tests |
| `docs/` | Product requirements, design system, architecture, AI evaluation and testing strategy |
| `eval/` | Synthetic evaluation fixtures |
| `infra/` | Local infrastructure (Docker Compose, native PostgreSQL setup) |

## Disclaimer

ClaimSathi is a self-help drafting tool, not legal advice. Users review and send every letter themselves. All sample data in this repository is synthetic.
