import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import path from "node:path";
import { newCase, syn001Pdf } from "./helpers";

const PROTECTED = readFileSync(path.resolve(__dirname, "../../../eval/fixtures/documents/SYN-001-password-01011980.pdf"));

// FR-008 AC2/AC3 and FR-009 AC1 in a real browser.
test("password-protected letter opens with the password", async ({ page }) => {
  await newCase(page, "Partly paid");
  await page.locator("#file").setInputFiles({ name: "letter.pdf", mimeType: "application/pdf", buffer: PROTECTED });
  await page.getByRole("button", { name: "Upload" }).click();
  await expect(page.getByText("This PDF is protected with a password.", { exact: false })).toBeVisible({ timeout: 60_000 });
  await page.getByLabel("PDF password").fill("31121999");
  await page.getByRole("button", { name: "Open file" }).click();
  await expect(page.getByText("That password didn't open the file.", { exact: false })).toBeVisible();
  await page.getByLabel("PDF password").fill("01011980");
  await page.getByRole("button", { name: "Open file" }).click();
  await expect(page.getByRole("link", { name: /Continue to check details/ })).toBeVisible({ timeout: 60_000 });
});

test("a file over 20 MB is refused before upload; a dropped connection is retried", async ({ page }) => {
  await newCase(page, "Partly paid");
  await page.locator("#file").setInputFiles({ name: "big.pdf", mimeType: "application/pdf",
    buffer: Buffer.alloc(21 * 1024 * 1024, 32) });
  await expect(page.locator(".field-error[role=alert]")).toContainText("This file is too large.");
  await expect(page.getByRole("button", { name: "Upload" })).toBeDisabled();

  let dropped = false;
  await page.route("**/api/v1/cases/*/documents", async (route) => {
    if (!dropped && route.request().method() === "POST") {
      dropped = true;
      await route.abort("connectionreset");
    } else {
      await route.continue();
    }
  });
  await page.locator("#file").setInputFiles({ name: "letter.pdf", mimeType: "application/pdf", buffer: syn001Pdf() });
  await page.getByRole("button", { name: "Upload" }).click();
  await expect(page.getByRole("link", { name: /Continue to check details/ })).toBeVisible({ timeout: 60_000 });
  expect(dropped).toBe(true);
});
