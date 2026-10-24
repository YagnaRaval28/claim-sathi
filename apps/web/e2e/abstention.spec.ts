import { expect, test } from "@playwright/test";
import { newCase, textPdf, uploadAndContinue } from "./helpers";

// FR-019 in a real browser: no reason found → a specific state with recovery actions → the typed reason is checked.
test("no reason found: the user types it and the case is checked again", async ({ page }) => {
  await newCase(page, "Rejected");
  await uploadAndContinue(page, textPdf(["A synthetic letter with no recorded extraction", "No reason given here"]));

  const field = async (label: string, value: string) => {
    await page.getByRole("button", { name: `Edit: ${label}` }).click();
    await page.getByRole("textbox", { name: label }).fill(value);
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByRole("button", { name: `Edit: ${label}` })).toBeVisible();
  };
  await field("Insurer", "Sample Health Insurance Co. Ltd.");
  await field("Date of insurer's letter", "02/07/2026");
  await page.getByRole("button", { name: "Edit: Decision" }).click();
  await page.getByRole("radio", { name: "Rejected" }).check();
  await page.getByRole("button", { name: "Save" }).click();
  await field("Amount claimed", "185000");
  await page.getByRole("button", { name: "These details are correct" }).click();
  await page.getByRole("link", { name: /Continue/ }).click();
  await page.getByRole("button", { name: "Check my case" }).click();

  await expect(page.getByText("We couldn't find a reason in your letter")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole("link", { name: "Upload another page" })).toBeVisible();
  await page.getByRole("button", { name: "Type the reason yourself" }).click();
  await page.getByLabel("The reason, exactly as your letter states it").fill("Claim not payable as per policy terms.");
  await page.getByRole("button", { name: "Save and check again" }).click();

  await expect(page.getByText("“Claim not payable as per policy terms.”")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText("We couldn't find a reason in your letter")).toHaveCount(0);
  await expect(page.locator(".pill:visible", { hasText: "You entered" })).toHaveCount(1);
  await expect(page.getByText("No clause cited").first()).toBeVisible();
  await page.getByRole("link", { name: /Write my letter/ }).click();
  await expect(page.locator("article.paper:visible")).toContainText("Claim not payable as per policy terms.");
});
