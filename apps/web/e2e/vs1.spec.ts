import { expect, test } from "@playwright/test";
import { newCase, signIn, syn001Pdf, syn002Pdf, textPdf, uploadAndContinue } from "./helpers";

// SCN-VS1 and the MVP variants, in a real browser: SYNTHETIC letters, fake AI provider, real API and database.

test("VS-1: partly paid claim from upload to letter download", async ({ page }) => {
  await newCase(page, "Partly paid");
  await uploadAndContinue(page, syn001Pdf());
  await expect(page.getByText("₹2,64,820")).toBeVisible();
  await expect(page.getByText("₹18,400")).toBeVisible();
  await page.getByRole("button", { name: "These details are correct" }).click();
  await page.getByRole("link", { name: /Continue/ }).click();

  await expect(page).toHaveURL(/\/findings$/);
  await page.getByRole("button", { name: "Check my case" }).click();
  await expect(page.getByText("Your insurer paid ₹2,10,500 of ₹2,64,820.")).toBeVisible({ timeout: 60_000 });
  await expect(page.locator(".cite-tab")).toHaveCount(3);
  await page.locator(".cite-tab").first().click();
  await expect(page.getByRole("dialog")).toContainText("Para 17(b)");
  await page.getByRole("button", { name: "Close" }).click();

  await page.getByRole("link", { name: /Write my letter/ }).click();
  await expect(page).toHaveURL(/\/letter$/);
  await expect(page.locator("article.paper")).toContainText("₹25,900");
  await page.getByLabel("I've read this letter and it's correct").check();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download PDF" }).click();
  expect((await download).suggestedFilename()).toMatch(/\.pdf$/);
});

test("Word download works (also on Windows, where PDF needs GTK)", async ({ page }) => {
  await newCase(page, "Rejected");
  await uploadAndContinue(page, syn002Pdf());
  await page.getByRole("button", { name: "These details are correct" }).click();
  await page.getByRole("link", { name: /Continue/ }).click();
  await page.getByRole("button", { name: "Check my case" }).click();
  await page.getByRole("link", { name: /Write my letter/ }).click();
  await page.getByLabel("I've read this letter and it's correct").check();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download Word (.docx)" }).click();
  expect((await download).suggestedFilename()).toBe("claimsathi-letter.docx");
});

test("rejected claim: the reason without a clause gets a finding and a letter", async ({ page }) => {
  await newCase(page, "Rejected");
  await uploadAndContinue(page, syn002Pdf());
  await expect(page.getByText("₹1,85,000")).toBeVisible();
  await expect(page.getByText("No deductions listed")).toBeVisible();
  await page.getByRole("button", { name: "These details are correct" }).click();
  await page.getByRole("link", { name: /Continue/ }).click();
  await page.getByRole("button", { name: "Check my case" }).click();
  await expect(page.getByText("Your insurer rejected your claim of ₹1,85,000.")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText("non-disclosure of pre-existing Diabetes Mellitus").first()).toBeVisible();
  await expect(page.locator(".cite-tab:visible")).toHaveCount(2);  // Para 17(b) and Para 17(a)
  await page.getByRole("link", { name: /Write my letter/ }).click();
  await expect(page.locator("article.paper")).toContainText("was rejected");
  await expect(page.locator("article.paper")).toContainText("non-disclosure of pre-existing Diabetes Mellitus");
});

test("unrecognised letter: details and deductions can be typed in by hand", async ({ page }) => {
  await newCase(page, "Partly paid");
  await uploadAndContinue(page, textPdf(["A synthetic letter with no recorded extraction", "Nothing to read here"]));

  const field = async (label: string, value: string) => {
    await page.getByRole("button", { name: `Edit: ${label}` }).click();
    await page.getByRole("textbox", { name: label }).fill(value);
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByRole("button", { name: `Edit: ${label}` })).toBeVisible();
  };
  await field("Insurer", "Sample Health Insurance Co. Ltd.");
  await field("Date of insurer's letter", "10/09/2026");
  await page.getByRole("button", { name: "Edit: Decision" }).click();
  await page.getByRole("radio", { name: "Partly paid" }).check();
  await page.getByRole("button", { name: "Save" }).click();
  await field("Amount claimed", "264820");
  await field("Amount paid", "2,10,500");
  await expect(page.getByText("₹2,64,820")).toBeVisible();

  await page.getByRole("button", { name: "Edit deductions" }).click();
  await page.getByRole("button", { name: "+ Add a deduction" }).click();
  await page.getByLabel("What was deducted").fill("Consumables");
  await page.getByLabel("Amount deducted (₹)").fill("6,250");
  await page.getByRole("button", { name: "Save deductions" }).click();
  await expect(page.getByText("₹6,250").first()).toBeVisible();

  await page.getByRole("button", { name: "These details are correct" }).click();
  await page.getByRole("link", { name: /Continue/ }).click();
  await page.getByRole("button", { name: "Check my case" }).click();
  await expect(page.getByText("No clause cited").first()).toBeVisible({ timeout: 60_000 });
  await page.getByRole("link", { name: /Write my letter/ }).click();
  await expect(page.locator("article.paper")).toContainText("Consumables (₹6,250)");
});

test("a signed-in user is not bounced back to sign-in, and can sign out", async ({ page }) => {
  await signIn(page, `bounce-${Date.now()}@example.com`);
  await expect(page).toHaveURL(/\/en\/welcome\/consent$/);
  await page.waitForTimeout(1500); // any late redirect would land here
  await expect(page).toHaveURL(/\/en\/welcome\/consent$/);
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/en$/);
  await page.goto("/en/cases");
  await expect(page).toHaveURL(/\/en\/sign-in$/);
});

test("Gujarati: sign-in leads to the Gujarati consent screen", async ({ page }) => {
  await signIn(page, `gu-${Date.now()}@example.com`, "gu");
  await expect(page).toHaveURL(/\/gu\/welcome\/consent$/);
  await expect(page.locator("html")).toHaveAttribute("lang", "gu");
  await expect(page.getByRole("heading", { level: 1 })).not.toHaveText("Before we read your documents");
});
