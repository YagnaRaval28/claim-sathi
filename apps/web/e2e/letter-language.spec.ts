import { expect, test } from "@playwright/test";
import { newCase, syn002Pdf, uploadAndContinue } from "./helpers";

// FR-024 in a real browser: the letter can be written in Gujarati, with the English copy alongside.
test("letter language: Gujarati letter with its English copy", async ({ page }) => {
  await newCase(page, "Rejected");
  await uploadAndContinue(page, syn002Pdf());
  await page.getByRole("button", { name: "These details are correct" }).click();
  await page.getByRole("link", { name: /Continue/ }).click();
  await page.getByRole("button", { name: "Check my case" }).click();
  await page.getByRole("link", { name: /Write my letter/ }).click();
  await expect(page.locator("article.paper:visible").first()).toContainText("Dear Sir or Madam,");

  await page.getByLabel("Letter language").selectOption("gu");
  const letter = page.locator("article.paper[lang=gu]:visible");
  await expect(letter).toContainText("વિષય:");
  await expect(letter).toContainText("SHI/CL/2026/000456");
  await expect(letter.locator("blockquote")).toHaveCount(2);
  await page.getByText("English copy", { exact: true }).click();
  await expect(page.locator("details.english-copy article.paper[lang=en]")).toContainText("Dear Sir or Madam,");
});
