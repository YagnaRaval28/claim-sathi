import { expect, test } from "@playwright/test";
import { newCase, syn002Pdf, uploadAndContinue } from "./helpers";

// FR-013/016/018 in a real browser: picking a reason type runs the deterministic rules; a ticked checklist item
// becomes an enclosure in the letter.
test("reason type and checklist: moratorium finding and enclosure", async ({ page }) => {
  await newCase(page, "Rejected");
  await uploadAndContinue(page, syn002Pdf());
  await page.getByRole("button", { name: "Edit: First policy start date" }).click();
  await page.getByRole("textbox", { name: "First policy start date" }).fill("01/04/2020");
  await page.getByRole("button", { name: "Save" }).click();
  await page.getByRole("button", { name: "These details are correct" }).click();
  await page.getByRole("link", { name: /Continue/ }).click();
  await page.getByRole("button", { name: "Check my case" }).click();

  await expect(page.getByText("What reason did the insurer give?")).toBeVisible({ timeout: 60_000 });
  await page.getByRole("radio", { name: "You didn't disclose something when buying the policy" }).check();
  await page.getByRole("button", { name: "Check again" }).click();
  await expect(page.getByText(/more than 60 months of continuous cover/).first()).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText("You chose: You didn't disclose something when buying the policy")).toBeVisible();

  await expect(page.getByText("Documents that would help")).toBeVisible();
  await page.getByRole("checkbox", { name: "Earlier policy schedules that show continuous cover" }).check();
  await page.getByRole("link", { name: /Write my letter/ }).click();
  const paper = page.locator("article.paper:visible");
  await expect(paper).toContainText("cannot be contested for non-disclosure except for established fraud");
  await expect(paper).toContainText("my earlier policy schedules showing continuous cover");
  await expect(paper).toContainText("(c) confirm that your claims review committee approved the rejection;");
});
