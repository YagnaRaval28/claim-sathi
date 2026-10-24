import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { newCase, syn002Pdf, uploadAndContinue } from "./helpers";

// NFR-012 / A11Y-DAC03-1: axe (WCAG 2.2 AA rules) finds no serious or critical violation on public pages in
// three languages and on the case screens. Manual keyboard and screen-reader scripts remain separate (MAN-A11Y-*).
const PUBLIC = ["", "/how-it-works", "/what-we-dont-do", "/free-official-channels", "/accuracy", "/glossary",
  "/privacy", "/terms", "/contact", "/sign-in"];

async function expectNoSeriousViolations(page: Page, label: string) {
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  const serious = result.violations
    .filter((v) => v.impact === "serious" || v.impact === "critical")
    .map((v) => `${label}: ${v.id} (${v.impact}) at ${v.nodes.map((n) => n.target.join(" ")).slice(0, 3).join(", ")}`);
  expect(serious).toEqual([]);
}

for (const lang of ["en", "gu", "hi"]) {
  test(`public pages have no serious accessibility violations (${lang})`, async ({ page }) => {
    for (const path of PUBLIC) {
      await page.goto(`/${lang}${path}`, { waitUntil: "networkidle" });
      await expect(page.locator("h1:visible").first()).toBeVisible();
      await expectNoSeriousViolations(page, `/${lang}${path}`);
    }
  });
}

test("case screens have no serious accessibility violations", async ({ page }) => {
  await newCase(page, "Rejected");
  await uploadAndContinue(page, syn002Pdf());
  const caseUrl = page.url().replace(/\/details$/, "");
  await expectNoSeriousViolations(page, "details");
  await page.getByRole("button", { name: "These details are correct" }).click();
  await page.getByRole("link", { name: /Continue/ }).click();
  await page.getByRole("button", { name: "Check my case" }).click();
  await expect(page.getByRole("link", { name: /Write my letter/ })).toBeVisible({ timeout: 60_000 });
  const id = caseUrl.split("/cases/")[1];
  for (const lang of ["en", "gu", "hi"]) {
    for (const screen of ["findings", "letter"]) {
      await page.goto(`/${lang}/cases/${id}/${screen}`, { waitUntil: "networkidle" });
      await expect(page.locator(screen === "letter" ? "article.paper:visible" : ".card:visible").first()).toBeVisible();
      await expectNoSeriousViolations(page, `${lang} ${screen}`);
    }
  }
  for (const screen of ["documents", "track", "track/ombudsman", "track/bima-bharosa", "settings"]) {
    await page.goto(`/en/cases/${id}/${screen}`, { waitUntil: "networkidle" });
    await expect(page.locator("h1:visible").first()).toBeVisible();
    await expectNoSeriousViolations(page, screen);
  }
});
