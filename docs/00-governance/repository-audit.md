# ClaimSathi: Repository Audit

| Field | Value |
|---|---|
| Date | 15 October 2026 |
| Method | Commands run on the developer machine (Windows 11, Git Bash), plus read-only npm and PyPI registry queries. Every finding below is **VERIFIED** unless labelled otherwise. |

---

## 1. Repository status

| Check | Finding |
|---|---|
| Git | **Not a git repository.** `git rev-parse` returned "fatal: not a git repository". There is no branch, history or remote. |
| Local changes | Not applicable: no version control, so no work is protected by history |
| Ignored files | No `.gitignore` |
| Secrets and environment files | No `.env*`, `*.pem` or credential files found under the project, to depth 3 |
| Generated files | None |
| CI/CD | None (no `.github/`) |

### Files present (complete list)

```
ClaimSathi/
├─ ClaimSathi — Product Requirements Document.md     # v0 PRD, SUPERSEDED by docs/02-product/PRD.md (CI-18)
├─ docs/
│  ├─ 00-governance/                                  # created by this audit
│  ├─ 01-discovery/competitor-research.md             # 608 lines
│  ├─ 02-product/PRD.md                               # 1,663 lines, v1.1
│  ├─ 02-product/design-system.md                     # 1,685 lines, v1.1
│  ├─ 03-architecture/system-design.md                # 1,687 lines, v1.1 (₹0 profile)
│  ├─ 04-ai/evaluation-plan.md                        # 417 lines
│  └─ 05-quality/testing-strategy.md                  # 687 lines
└─ eval/
   ├─ schema/benchmark-case.schema.json               # JSON Schema 2020-12
   └─ fixtures/synthetic/cases.jsonl                   # 10 synthetic cases
```

---

## 2. Implementation status

| Area | Status |
|---|---|
| Frontend (Next.js) | **Not started.** No `package.json`. |
| Backend (FastAPI) | **Not started.** No `pyproject.toml`. |
| Database migrations and seeds | None |
| Tests | None (only the evaluation schema and fixtures) |
| Environment configuration | `.env.example` created by this audit (placeholders only) |
| Integrations | None configured: no Supabase project, GCP project, SES identity or OAuth client seen |

---

## 3. Toolchain on the developer machine

| Tool | Version found | Required by the architecture | Status |
|---|---|---|---|
| git | 2.40.0.windows.1 | Any recent | ✅ |
| Node.js | v22.17.0 | ≥ 20.9 (Next.js 16.4.1); ≥ 22.12 (Vitest 5.0.4) | ✅ |
| npm | 11.2.0 | — | ✅ |
| Corepack | 0.33.0 | To enable pnpm | ✅ |
| pnpm | **not installed** | Package manager (recommendation) | ⚠️ run `corepack enable pnpm` |
| Python | 3.13.5 (default), 3.11 (py launcher), 3.12.4 (Anaconda) | **3.12** (architecture) | ⚠️ provision 3.12 per project with uv (`uv python install 3.12`; uv reports `cpython-3.12.13` available) |
| uv | 0.10.9 | Python env and package management (recommendation) | ✅ |
| Docker / Compose | 29.2.0 / v5.0.2 | Local Postgres, MinIO, clamd, Mailpit | ⚠️ **daemon not running** ("cannot find dockerDesktopLinuxEngine"). Start Docker Desktop. |
| psql | 18.1 | Optional client | ✅ |
| AWS CLI | 2.37.6 | SES setup at M9 | ✅ installed (configured profiles **not inspected**, to avoid reading credentials) |
| gcloud | **not installed** | M9 | ⏳ |
| Terraform | **not installed** | M9 | ⏳ |
| Supabase CLI | **not installed** | Optional (local Supabase; migrations go through Alembic) | ⏳ optional |

**Windows note.** WeasyPrint needs the Pango/GTK libraries. On Windows, run the API and worker **in Docker** (or WSL2) for parity with Cloud Run, rather than natively. This is a recommendation; it is not tested yet because there is no code.

---

## 4. Dependency versions and compatibility (registry query, 15 October 2026)

### 4.1 Web (npm)

| Package | Latest | Engines / peers | Compatibility note |
|---|---|---|---|
| next | 16.4.1 | node ≥ 20.9.0; peers react ^18.2 \|\| ^19 | ✅ with Node 22.17 |
| react / react-dom | 19.3.1 | — | ✅ |
| next-intl | 4.14.9 | peer next ^12–^16; react ^19 | ✅ |
| @tanstack/react-query | 5.104.3 | peer react ^18 \|\| ^19 | ✅ |
| @tiptap/react | 3.32.0 | peer react ^17–^19; @tiptap/pm and @tiptap/core at 3.32.0 | ✅. Pin all `@tiptap/*` to the same version. |
| tailwindcss / @tailwindcss/postcss | 4.3.3 / 4.3.3 | — | ✅. Tailwind v4 uses CSS-first config; design tokens map to `@theme` variables. |
| tus-js-client | 4.3.1 | node ≥ 18 | Only if spike S-2 confirms direct TUS (CI-04) |
| openapi-typescript | 7.13.0 | — | ✅ |
| zod / react-hook-form | 4.6.7 / 7.90.0 | — | ✅ |
| @playwright/test | 1.64.1 | node ≥ 20 | ✅. Also an optional peer of next. |
| vitest | 5.0.4 | node ^22.12 \|\| ^24 \|\| ≥ 26 | ✅ with 22.17 |
| typescript | **7.0.2 latest**; 6.0.3 and 5.9.3 also published | eslint-config-next peer `typescript >= 3.3.1` | ⚠️ **TS 7 (native port) compatibility with Next.js tooling is UNVERIFIED** (CI-16). Use the version `create-next-app@16.4.1` installs and pin it. |
| pnpm | 12.11.2 (10.34.7 also current) | node ≥ 18 | ✅ via Corepack. Pin with `packageManager` in `package.json`. |

### 4.2 API and worker (PyPI)

| Package | Latest | requires_python | Note |
|---|---|---|---|
| fastapi | 0.143.1 | ≥ 3.10 | ✅ |
| pydantic | 2.14.1 | ≥ 3.10 | ✅ |
| SQLAlchemy | 2.1.4 | **≥ 3.11** | ✅ with 3.12 |
| alembic | 1.20.0 | ≥ 3.10 | ✅ |
| psycopg | 3.3.6 | ≥ 3.10 | ✅. Use `psycopg[binary]` locally and in the image. |
| pgvector (Python) | 0.5.1 | ≥ 3.10 | ✅ |
| Authlib / PyOTP | 1.9.1 / 2.10.0 | ≥ 3.10 / ≥ 3.8 | ✅ |
| google-genai | 2.31.0 | ≥ 3.10 | ✅. One SDK for both the Gemini Developer API (spike S-5) and Vertex AI (production). |
| google-cloud-tasks / -documentai / -secret-manager | 2.26.0 / 3.16.0 / 2.31.0 | ≥ 3.10 | ✅ |
| boto3 | 1.43.114 | ≥ 3.10 | ✅ (SES, and S3-compatible Supabase Storage) |
| weasyprint | 70.0 | ≥ 3.10 | ✅. Needs system Pango (Docker image). |
| python-docx | 1.2.0 | ≥ 3.9 | ✅ |
| pikepdf | 10.17.0 | **≥ 3.11** | ✅ with 3.12 |
| pypdfium2 / pillow | 5.14.0 / 12.3.0 | ≥ 3.6 / ≥ 3.10 | ✅ |
| structlog / sentry-sdk | 26.1.0 / 2.72.0 | ≥ 3.10 / ≥ 3.6 | ✅ |
| pyrage | 1.4.0 | ≥ 3.10 | ✅ |
| uvicorn / httpx / pytest | 0.54.0 / 0.28.1 / 9.1.1 | ≥ 3.10 / ≥ 3.8 / ≥ 3.10 | ✅ |

**Result.** All Python packages support **Python 3.12**, the architecture's choice; two of them require ≥ 3.11. No incompatibility was found. Exact versions are pinned in the lock files at T-001/T-002, and nothing is installed by this audit.

---

## 5. Build, lint, type-check and test commands

**None exist yet**, because there is no code. The *planned* commands are in `development-setup.md` §6 and become VERIFIED only when M0 creates them.

---

## 6. Configuration gaps

| Gap | Impact | Fix (backlog) |
|---|---|---|
| No git repository | No history, review or rollback; CI impossible | T-001 |
| No `.gitignore` | Risk of committing `.env`, `node_modules`, `.venv`, uploads | T-001 |
| No lock files or toolchain pins (`.nvmrc`, `.python-version`, `packageManager`) | Non-reproducible builds | T-001, T-002 |
| No `docker-compose.yml` | No local database, storage or mail | T-003 |
| No CI workflow | No merge gate | T-004 |
| No OpenAPI or TypeScript client pipeline | Front end and back end drift | T-107 |
| v0 PRD at the root | Agents may follow superseded requirements | CI-18 (needs permission) |
| Docker daemon stopped | Local stack cannot start | Start Docker Desktop |

---

## 7. Risks and recommendations

1. **Initialise git first (T-001)** and commit the docs as the baseline, before any code.
2. **Keep everything local until M9** (CI-05). Use the Gemini free tier with **synthetic data only** for AI work before then.
3. **Run the API in Docker on Windows**, because WeasyPrint and Pango are hard to set up natively.
4. **Pin toolchains:** Node 22 LTS line (`.nvmrc`), Python 3.12 (`.python-version`), pnpm (`packageManager` field), and a TypeScript version chosen at scaffold time (CI-16).
5. **Do not commit `eval/` consented data.** Only synthetic fixtures belong in git (evaluation plan §9.2).
