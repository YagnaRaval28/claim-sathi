# ClaimSathi: Development Setup

| Field | Value |
|---|---|
| Date | 15 October 2026 |
| Status | **In use (15 Oct 2026).** M0–M3 code exists. Commands marked VERIFIED were run on the developer machine (Windows 11, native PostgreSQL 18, no Docker). Others remain *planned*. |
| Principle | **Local-first and ₹0.** Milestones M0–M8 need no cloud account (decision D-D, pending approval). |

---

## 1. Prerequisites

| Tool | Version | Verified on this machine | Install / enable |
|---|---|---|---|
| Git | ≥ 2.40 | 2.40.0 ✅ | — |
| Node.js | 22 LTS line, ≥ 22.12 (Vitest 5 requirement) | 22.17.0 ✅ | — |
| pnpm | 10.34.7 (pinned in root `packageManager`) | via corepack ✅ | `corepack enable pnpm`, or run `corepack pnpm@10.34.7 <cmd>` without enabling |
| Python | **3.12** | 3.13.5 / 3.11 present; 3.12 downloadable via uv ✅ | `uv python install 3.12` |
| uv | ≥ 0.10 | 0.10.9 ✅ | — |
| Docker Desktop (Compose v2+) | 29.x | 29.2.0 installed; **engine does not start** (WSL `docker-desktop` distro stopped) | Optional. Without it, use the native path in §3a. |
| PostgreSQL (native, alternative to Docker) | 16+ | 18.1 ✅ (port 5432) | See §3a |
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

Compose maps Postgres to host port **5433** so it can run next to a native PostgreSQL on 5432 (`.env.example` uses 5433). MinIO and Mailpit are on `:latest` until their digests are pinned (T-003).

### 3a. Without Docker: native PostgreSQL (VERIFIED 15 Oct 2026)

1. As the postgres superuser, run the setup script once. It creates the `claimsathi` role and the `claimsathi` and `claimsathi_test` databases.

   ```bash
   psql -U postgres -h localhost -p 5432 -f infra/local/native-postgres-setup.sql
   ```

2. In `.env`, change the port in `SUPABASE_DB_URL` and `TEST_DATABASE_URL` from 5433 to **5432**.
3. VS-1 needs no `vector` extension; the first migration does not create it. Embeddings arrive at M5, and a native install will need pgvector then.
4. Storage and email without Docker:
   - `STORAGE_BACKEND=memory` keeps uploads in the API process, so they are lost on restart. This is allowed only for `APP_ENV` `local` and `test`.
   - Sign-in codes need an SMTP catcher. Run the Mailpit Windows binary from its GitHub release, checked against the release's SHA-256 digest, with `mailpit.exe --listen 127.0.0.1:8025 --smtp 127.0.0.1:1025`. Or use Docker for Mailpit only. **Do not** print codes to the console: logs never contain sign-in codes.
5. PDF export (WeasyPrint) needs GTK/Pango, which native Windows lacks. Everything else runs natively. Export runs in CI and in the Docker image.

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

## 5. Database initialisation (VERIFIED on native PostgreSQL 18)

```bash
cd apps/api
uv sync
uv run alembic upgrade head && uv run alembic check   # check prints "No new upgrade operations detected."
uv run python -m claimsathi.seeds --env local         # consent v1 (draft), rule patterns, SYNTHETIC knowledge fixtures
```

- `--env local` and `--env test` seed the synthetic regulation and wording fixtures with RULE-MC-01 enabled.
- `--env prod` keeps RULE-MC-01 `disabled_pending_verification` until the real Master Circular is ingested and attested.
- The knowledge ingestion CLI for real PDFs is planned (M5). Until then, `knowledge.ingest.ingest_text()` is used by the seeds.

**Test database:**

- `TEST_DATABASE_URL` points to `claimsathi_test`. If it is unset, integration tests are skipped; CI always sets it.
- The fixtures rebuild the `public` schema once per session (`alembic upgrade head`), then truncate every table before each test.

---

## 6. Start-up

```bash
# Terminal 1: API (Docker recommended on Windows because WeasyPrint needs Pango)
docker compose --profile api up -d api   # or natively:
cd apps/api && uv run uvicorn --factory claimsathi.main_api:create_app --reload --port 8000

# Terminal 2: web
cd apps/web && pnpm install && pnpm dev      # http://localhost:3000; /api/* is proxied to API_UPSTREAM_URL
```

**Background tasks locally:** `TASK_QUEUE=inprocess` runs task handlers in the API process after commit. This exercises the same outbox code path as Cloud Tasks.

### Quality checks (the CI merge gate, testing strategy §6.1)

All rows except E2E, API contract and evaluation schema were VERIFIED on 15 Oct 2026. Those three are planned (T-107, T-308, M10).

| Area | Command |
|---|---|
| API lint and format | `uv run ruff check . && uv run ruff format --check .` |
| API types | `uv run mypy claimsathi` |
| API tests | `uv run pytest -q` (unit + integration + authz + rule suites) |
| Migrations | `uv run alembic upgrade head && uv run alembic check` |
| API dependency audit | `uv export --frozen --no-hashes --format requirements-txt > req.txt && uvx pip-audit -r req.txt` |
| Web dependency audit | `pnpm audit --audit-level high` |
| Web build | `pnpm build` |
| Web lint | `pnpm lint` |
| Web types | `pnpm typecheck` (`tsc --noEmit`) |
| Web unit tests | `pnpm test` (Vitest) |
| E2E | `pnpm --filter web e2e` (Playwright). Needs Mailpit and the API running; starts the web dev server if needed. Run `pnpm --filter web exec playwright install chromium` once. VERIFIED locally on 16 Oct 2026, except the PDF download on Windows (OI-03). |
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
| WeasyPrint `OSError: cannot load library 'gobject'/'pango'` (also `libgobject-2.0-0`) | Native Windows run without GTK | Run the API in Docker or WSL2. Only PDF export is affected. |
| Engine never starts; `wsl -l -v` shows `docker-desktop` Stopped | Docker Desktop WSL backend broken | Restart Docker Desktop or run `wsl --shutdown`, then retry. Or use §3a. |
| `extension "vector" is not available` | A non-pgvector Postgres image | Use the pgvector image in compose |
| Port 5433 or 9000 in use | Another Postgres or MinIO already running | Change the compose port mapping and `.env` |
| `[Errno 10048]` binding the API to port 8000 | Another app already uses 8000 | Start the API with `--port 8010` and the web with `API_UPSTREAM_URL=http://127.0.0.1:8010` |
| API exits: `config error: FIELD_DATA_KEY missing` | `.env` not filled in | Generate the values per §4 |
| Gemini free tier `429` | Free-tier rate limit | Lower concurrency; use `fake` for routine tests |
| Next.js type-check errors after install | TypeScript major mismatch (CI-16) | Use the TypeScript version pinned at scaffold time |
