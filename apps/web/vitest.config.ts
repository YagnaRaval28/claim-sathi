import { defineConfig } from "vitest/config";

// Unit tests only. Browser end-to-end tests live in e2e/ and run with Playwright (`pnpm e2e`).
export default defineConfig({
  test: { include: ["lib/**/*.test.ts", "*.test.ts"], exclude: ["e2e/**", "node_modules/**"] },
});
