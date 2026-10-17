import { expect, test } from "@playwright/test";
import { newCase } from "./helpers";

// M8 in a real browser: typed-confirmation delete, account settings, close with an optional outcome.
test("case settings: delete a case with the typed 4-digit code", async ({ page }) => {
  await newCase(page, "Partly paid");
  const caseUrl = page.url().replace(/\/documents$/, "");
  await page.goto(`${caseUrl}/settings`);
  await page.getByRole("button", { name: "Delete this case" }).click();
  const dialog = page.getByRole("dialog");
  const label = await dialog.getByText(/^Type \d{4} to confirm$/).textContent();
  const code = /(\d{4})/.exec(label ?? "")?.[1] ?? "";
  const confirm = dialog.getByRole("button", { name: "Delete this case" });
  await expect(confirm).toBeDisabled();
  await dialog.getByLabel("Confirmation code").fill(code);
  await confirm.click();
  await expect(page).toHaveURL(/\/en\/cases$/);
  await expect(page.getByText("No cases yet")).toBeVisible();
  const caseId = caseUrl.split("/").pop();
  expect((await page.request.get(`/api/v1/cases/${caseId}`)).status()).toBe(404);
});

test("account settings: reminders and large text save immediately", async ({ page }) => {
  await newCase(page, "Partly paid");
  await page.goto("/en/settings", { waitUntil: "networkidle" });
  await page.getByLabel("Email me deadline reminders").check();
  await expect(page.getByText("Saved").first()).toBeVisible();
  await page.getByLabel("Large text").check();
  await expect(page.locator("html")).toHaveAttribute("data-large-text", "true");
  await page.reload({ waitUntil: "networkidle" });
  await expect(page.getByLabel("Email me deadline reminders")).toBeChecked();
  await expect(page.getByLabel("Large text")).toBeChecked();
  await expect(page.getByText(/document processing, reminders/)).toBeVisible();
});

test("close a case with an optional outcome", async ({ page }) => {
  await newCase(page, "Partly paid");
  const caseUrl = page.url().replace(/\/documents$/, "");
  await page.goto(`${caseUrl}/close`, { waitUntil: "networkidle" });
  await page.getByRole("radio", { name: "Partly paid" }).check();
  await page.getByRole("radio", { name: "4" }).check();
  await page.getByRole("button", { name: "Close case" }).click();
  await expect(page.getByText(/Case closed\. Your files will be deleted on \d{2}\/\d{2}\/\d{4}/)).toBeVisible();
  await page.goto(`${caseUrl}/track`, { waitUntil: "networkidle" });
  await expect(page.getByText("This case is closed.").first()).toBeVisible();
});
