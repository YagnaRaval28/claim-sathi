import { defineConfig, devices } from "@playwright/test";

// SCN-VS1 end-to-end (backlog T-308). Runs against the real web app, API, Postgres and Mailpit with the fake AI
// provider and synthetic fixtures only. Locally, start Mailpit and the API first (development-setup §3a/§6);
// the web dev server is started here if it isn't already running.
const WEB = process.env.E2E_BASE_URL ?? "http://localhost:3000";

export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  expect: { timeout: 30_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: { baseURL: WEB, trace: "retain-on-failure", ...devices["Desktop Chrome"] },
  webServer: {
    command: "pnpm dev --port 3000",
    url: `${WEB}/en`,
    reuseExistingServer: true,
    timeout: 180_000,
  },
});
