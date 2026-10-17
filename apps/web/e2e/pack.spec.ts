import { expect, test } from "@playwright/test";
import { newCase, syn002Pdf, uploadAndContinue } from "./helpers";

const iso = (d: Date) => new Date(d.getTime() + 330 * 60_000).toISOString().slice(0, 10);
const dmy = (s: string) => s.split("-").reverse().join("/");

// FR-026 in a real browser: a letter sent more than a month ago makes the Ombudsman pack available.
test("ombudsman pack: checks pass, pack created with the logged history, filing logged", async ({ page }) => {
  await newCase(page, "Rejected");
  await uploadAndContinue(page, syn002Pdf());
  await page.getByRole("button", { name: "These details are correct" }).click();
  await page.getByRole("link", { name: /Continue/ }).click();
  await page.getByRole("button", { name: "Check my case" }).click();
  await page.getByRole("link", { name: /Write my letter/ }).click();
  await page.getByRole("link", { name: /I've sent it: track deadlines/ }).click();

  const sent = iso(new Date(Date.now() - 35 * 86_400_000));
  await page.getByRole("button", { name: "Log an update" }).click();
  await page.getByRole("radio", { name: "Letter sent to the insurer" }).check();
  await page.locator("#ev-date").fill(sent);
  await page.getByRole("radio", { name: "by email" }).check();
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("You can now go to the Insurance Ombudsman.")).toBeVisible();

  await page.getByRole("link", { name: /Go to Ombudsman/ }).first().click();
  await expect(page.getByText("Not yet")).toHaveCount(0);
  await page.getByRole("button", { name: "Create Ombudsman pack" }).click();
  await expect(page).toHaveURL(/\/track\/ombudsman\/pack$/);
  const paper = page.locator("article.paper:visible");  // Next 16 keeps visited pages mounted but hidden
  await expect(paper).toContainText(`On ${dmy(sent)} I wrote to the insurer's grievance redressal officer by email`);
  await expect(paper).toContainText("The insurer has not replied within one month of my letter.");
  await expect(paper).toContainText("non-disclosure of pre-existing Diabetes Mellitus");
  await expect(page.locator(".callout:visible", { hasText: "You sign and file the complaint yourself." })).toHaveCount(1);
  await expect(page.getByRole("link", { name: "cioins.co.in" })).toHaveAttribute("href", "https://cioins.co.in");

  await page.getByRole("button", { name: "Log that I filed" }).click();
  await expect(page.getByText(/Logged\./)).toBeVisible();
  await page.goto(page.url().replace(/\/ombudsman\/pack$/, ""), { waitUntil: "networkidle" });
  await expect(page.locator(".timeline")).toContainText("Filed with the Ombudsman");
});
