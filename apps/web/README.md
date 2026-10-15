# ClaimSathi web (Next.js 16)

The user-facing app in English, Gujarati and Hindi. Routes live under `app/[lang]/`. The browser calls `/api/*`, which Next.js forwards to the FastAPI service (`API_UPSTREAM_URL`).

```bash
corepack pnpm@10.34.7 install
corepack pnpm@10.34.7 dev        # http://localhost:3000 (needs the API on :8000)
corepack pnpm@10.34.7 lint && corepack pnpm@10.34.7 typecheck && corepack pnpm@10.34.7 test && corepack pnpm@10.34.7 build
```

Read first: `AGENTS.md`, `docs/02-product/design-system.md` and `docs/00-governance/development-setup.md`. Every UI string goes in all three files in `messages/`; `lib/format.test.ts` fails on a missing key.
