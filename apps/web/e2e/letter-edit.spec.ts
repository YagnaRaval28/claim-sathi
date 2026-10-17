import { expect, test } from "@playwright/test";
import { newCase, syn002Pdf, uploadAndContinue } from "./helpers";

// FR-027 in a real browser: a changed quote loses its badge, undo restores it, free text is saved.
test("letter editor: protected quote, undo, added paragraph saved", async ({ page }) => {
  await newCase(page, "Rejected");
  await uploadAndContinue(page, syn002Pdf());
  await page.getByRole("button", { name: "These details are correct" }).click();
  await page.getByRole("link", { name: /Continue/ }).click();
  await page.getByRole("button", { name: "Check my case" }).click();
  await page.getByRole("link", { name: /Write my letter/ }).click();
  await page.getByRole("button", { name: "Edit letter" }).click();

  const quote = page.locator("textarea").filter({ hasText: "The applicable rule states" });
  await expect(page.locator(".pill-verified:visible")).toHaveCount(1);
  await quote.fill("The applicable rule states something else entirely.");
  await expect(page.getByText("This is no longer a verified quote")).toBeVisible();
  await page.getByRole("button", { name: "Undo" }).click();
  await expect(page.locator(".pill-verified:visible")).toHaveCount(1);

  await page.getByRole("button", { name: "+ Add paragraph" }).first().click();
  const fresh = page.locator("textarea").nth(1);
  await fresh.fill("I have held this policy for six years.");
  await page.getByRole("button", { name: "Done" }).click();

  const paper = page.locator("article.paper:visible");
  await expect(paper).toContainText("I have held this policy for six years.");
  await expect(paper.locator("blockquote sup")).toHaveText("[1]");
  await page.reload({ waitUntil: "networkidle" });
  await expect(page.locator("article.paper:visible")).toContainText("I have held this policy for six years.");
});
