import { expect, test } from "@playwright/test";
import { newCase, syn002Pdf, uploadAndContinue } from "./helpers";

// M7 in a real browser: log the sent letter, see deadlines, and find the Ombudsman step blocked (RULE-ESC-02).
test("track: log the sent letter, see deadlines, Ombudsman blocked until a month passes", async ({ page }) => {
  await newCase(page, "Rejected");
  await uploadAndContinue(page, syn002Pdf());
  await page.getByRole("button", { name: "These details are correct" }).click();
  await page.getByRole("link", { name: /Continue/ }).click();
  await page.getByRole("button", { name: "Check my case" }).click();
  await page.getByRole("link", { name: /Write my letter/ }).click();
  await page.getByRole("link", { name: /I've sent it: track deadlines/ }).click();

  await expect(page).toHaveURL(/\/track$/);
  await expect(page.getByText("Log when you send your letter, so we can track deadlines.")).toBeVisible();
  await page.getByRole("button", { name: "Log an update" }).click();
  await page.getByRole("radio", { name: "Letter sent to the insurer" }).check();
  await page.getByRole("radio", { name: "by post" }).check();
  await page.getByRole("button", { name: "Save" }).click();

  await expect(page.locator(".timeline")).toContainText("Letter sent to the insurer");
  await expect(page.getByText("Last day to go to the Ombudsman")).toBeVisible();
  await expect(page.getByText("You can go to the Ombudsman from", { exact: true })).toBeVisible();
  await expect(page.getByText(/days left/).first()).toBeVisible();

  await page.getByRole("link", { name: "Go to Ombudsman" }).first().click();
  await expect(page).toHaveURL(/\/track\/ombudsman$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Can you go to the Ombudsman yet?");
  await expect(page.getByText("Not yet").first()).toBeVisible();
  await expect(page.getByText(/Wait for your insurer's reply/).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Log that I filed" })).toHaveCount(0);

  // FR-025: copy-ready Bima Bharosa content from the optional stage 2.
  await page.goBack();
  await page.getByRole("link", { name: /Copy-ready complaint text/ }).click();
  await expect(page).toHaveURL(/\/track\/bima-bharosa$/);
  await expect(page.getByLabel("Claim number")).toHaveValue("SHI/CL/2026/000456");
  await expect(page.getByLabel("Date you wrote to the insurer")).toBeVisible();
  await expect(page.getByRole("link", { name: /Call 155255/ })).toHaveAttribute("href", "tel:155255");
});
