# ClaimSathi: Development Setup

| Field | Value |
|---|---|
| Date | 15 October 2026 |
| Status | **Specification.** No code exists yet. Commands in §6 onwards are *planned*: they become real when milestone M0 creates the files, and each is marked "to verify at T-00x". The tool versions in §1 were VERIFIED on the developer machine. |
| Principle | **Local-first and ₹0.** Milestones M0–M8 need no cloud account (decision D-D, pending approval). |

---

## 1. Prerequisites

| Tool | Version | Verified on this machine | Install / enable |
|---|---|---|---|
| Git | ≥ 2.40 | 2.40.0 ✅ | — |
| Node.js | 22 LTS line, ≥ 22.12 (Vitest 5 requirement) | 22.17.0 ✅ | — |
| pnpm | Pin in `packageManager` at T-001 (10.x or 12.x) | ❌ not enabled | `corepack enable pnpm` |
| Python | **3.12** | 3.13.5 / 3.11 present; 3.12 downloadable via uv ✅ | `uv python install 3.12` |
| uv | ≥ 0.10 | 0.10.9 ✅ | — |
| Docker Desktop (Compose v2+) | 29.x | 29.2.0 ✅ installed; **daemon not running** | Start Docker Desktop. On Windows, the WSL2 backend is recommended. |
| psql (optional) | any | 18.1 ✅ | — |
| gcloud, Terraform, Supabase CLI | — | ❌ | **Only from M9** (cloud) |
| AWS CLI | v2 | 2.37.6 ✅ | Only for SES at M9 |

**Accounts:**

- **None needed for M0–M8.**
- **Optional:** a Gemini Developer API key (free tier) for spike S-5 and AI development, **with synthetic data only**. Google's free-tier terms say not to submit personal information, and decision D-008 forbids it for real documents.

---

## 2. Repository setup (created at T-001; planned)

```bash
git init -b main
git add docs eval AGENTS.md .env.example .gitignore
git commit -m "docs: baseline specifications and readiness pack"
```

The planned layout follows system-design §C.5:

```
apps/web  apps/api  packages/{api-client,design-tokens}  eval/  infra/  docs/
```

Toolchain pins (T-001):

| File | Content |
|---|---|
| `.nvmrc` | `22` |
| `.python-version` | `3.12` |
| root `package.json` | `"packageManager": "pnpm@<pinned>"` |

---

## 3. Local services (`docker-compose.yml`, created at T-003; planned)

| Service | Image (pin a digest at T-003) | Port | Purpose |
|---|---|---|---|
| postgres | `pgvector/pgvector:pg16` (ASSUMPTION: tag exists; verify at T-003) | 5432 | App database (+ `claimsathi_test`) |
| minio | `minio/minio` | 9000 / 9001 | S3-compatible storage standing in for Supabase Storage |
| mailpit | `axllent/mailpit` | 1025 (SMTP) / 8025 (UI) | Captures sign-in codes and reminders |
| clamd | `clamav/clamav` | 3310 | Malware scanning |

```bash
docker compose up -d          # to verify at T-003
docker compose ps
```

---

## 4. Environment variables

1. Run `cp .env.example .env`. The `.env` file is git-ignored and must **never** be committed.
2. For local development, the defaults in `.env.example` point to the docker-compose services. Generate the local secrets as follows:

   ```bash
   python -c "import secrets;print(secrets.token_hex(32))"            # HASH_PEPPER, CODE_PEPPER, CSRF_SECRET
   python -c "import secrets,base64;print(base64.b64encode(secrets.token_bytes(32)).decode())"   # FIELD_DATA_KEY
   ```

3. Leave `LLM_PROVIDER=fake`, `EMBEDDING_PROVIDER=fake`, `OCR_ENGINE=fake` and `TASK_QUEUE=inprocess` unless you are running spike S-5 (`LLM_PROVIDER=gemini_dev` + `GEMINI_DEV_API_KEY`, **synthetic data only**).
4. The API validates its configuration at start-up (T-101). A missing or malformed required variable stops the process with a clear message, and secrets are never printed.

`.env.example` is the authoritative inventory of variables. It refines system-design §C.6 with local and cloud parity names.

---

## 5. Database initialisation (planned; to verify at T-104)

```bash
cd apps/api
uv sync
uv run alembic upgrade head                      # schema, including the pgcrypto and vector extensions
uv run python -m claimsathi.seeds --env local    # consent v1 (draft), rules, glossary (draft), bootstrap admin
uv run python -m claimsathi.knowledge.ingest --file <master-circular.pdf> --type regulation --attest
                                                 # admin-equivalent CLI for local development
```

**Test database:**

- `TEST_DATABASE_URL` points to `claimsathi_test`.
- The test fixtures create a fresh schema per session (`alembic upgrade head`) and wrap each test in a transaction that is rolled back.

---

## 6. Start-up (planned; to verify at T-002 and T-005)

```bash
# Terminal 1: API (Docker recommended on Windows because WeasyPrint needs Pango)
docker compose up -d api          # or natively: cd apps/api && uv run uvicorn claimsathi.main_api:app --reload --port 8000

# Terminal 2: web
cd apps/web && pnpm install && pnpm dev      # http://localhost:3000; /api/* is proxied to API_UPSTREAM_URL
```

**Background tasks locally:** `TASK_QUEUE=inprocess` runs task handlers in the API process after commit. This exercises the same outbox code path as Cloud Tasks.

### Quality checks (planned; become the CI merge gate in testing strategy §6.1)

| Area | Command |
|---|---|
| API lint and format | `uv run ruff check . && uv run ruff format --check .` |
| API types | `uv run mypy claimsathi` |
| API tests | `uv run pytest -q` (unit + integration + authz + rule suites) |
| Migrations | `uv run alembic upgrade head && uv run alembic check` |
| Web lint | `pnpm lint` |
| Web types | `pnpm typecheck` (`tsc --noEmit`) |
| Web unit tests | `pnpm test` (Vitest) |
| E2E | `pnpm e2e` (Playwright, fake AI and OCR adapters) |
| API contract | `pnpm gen:api && git diff --exit-code packages/api-client` |
| Evaluation schema | `uv run python -m eval.validate eval/fixtures/synthetic/cases.jsonl` |

---

## 7. Development versus production configuration

| Aspect | Local | Staging / prod (M9+) |
|---|---|---|
| Database | docker Postgres + pgvector | Supabase Free (Mumbai) via the pooler |
| Storage | MinIO | Supabase Storage (Mumbai), private buckets |
| Tasks | In-process after commit | Cloud Tasks + Cloud Scheduler (3 jobs) |
| Email | Mailpit | Amazon SES ap-south-1 (needs a verified domain, CI-23) |
| AI | `fake`, or `gemini_dev` (synthetic only) | `vertex` (asia-south1), credit guard on |
| OCR | `fake` / Tesseract | Document AI asia-south1 |
| Secrets | `.env` | One Secret Manager bundle |
| Cookies | `Secure` off on http://localhost only | `Secure` on |
| Logging | Pretty console | JSON to the regional Cloud Logging bucket; allowlisted fields |
| Sentry | Off | EU org, scrubbing on |

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `failed to connect to the docker API … dockerDesktopLinuxEngine` | Docker Desktop not running (seen in this audit) | Start Docker Desktop and wait for "Engine running" |
| `pnpm: command not found` | pnpm not enabled (seen in this audit) | `corepack enable pnpm` |
| Wrong Python picked (3.13) | The system default is 3.13 | `uv python install 3.12`; `uv sync` respects `.python-version` |
| WeasyPrint `OSError: cannot load library 'gobject'/'pango'` | Native Windows run without GTK | Run the API in Docker or WSL2 |
| `extension "vector" is not available` | A non-pgvector Postgres image | Use the pgvector image in compose |
| Port 5432 or 9000 in use | Local Postgres or MinIO already running | Stop the local service, or change the compose port mapping and `.env` |
| API exits: `config error: FIELD_DATA_KEY missing` | `.env` not filled in | Generate the values per §4 |
| Gemini free tier `429` | Free-tier rate limit | Lower concurrency; use `fake` for routine tests |
| Next.js type-check errors after install | TypeScript major mismatch (CI-16) | Use the TypeScript version pinned at scaffold time |
