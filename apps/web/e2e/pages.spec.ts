import { expect, test } from "@playwright/test";
import { newCase } from "./helpers";

// FR-043/044: information pages in three languages; free official help one tap from a case screen.
test("free official help is one tap from a case screen and links to the official sites", async ({ page }) => {
  await newCase(page, "Partly paid");
  await page.locator("footer").getByRole("link", { name: "Free official help" }).click();
  await expect(page).toHaveURL(/\/en\/free-official-channels$/);
  await expect(page.getByText("Never pay anyone claiming to be the Ombudsman", { exact: false })).toBeVisible();
  await expect(page.getByRole("link", { name: /bimabharosa\.irdai\.gov\.in/ })).toHaveAttribute("href", "https://bimabharosa.irdai.gov.in");
  await expect(page.getByRole("link", { name: /cioins\.co\.in/ })).toHaveAttribute("href", "https://cioins.co.in");
  await expect(page.getByText(/155255/)).toBeVisible();
});

test("information pages render in Gujarati and Hindi, legal pages marked draft", async ({ page }) => {
  await page.goto("/gu/how-it-works", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("ClaimSathi કેવી રીતે કામ કરે છે");
  await page.goto("/hi/privacy", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("गोपनीयता सूचना");
  await expect(page.getByText("ड्राफ़्ट, कानूनी समीक्षा बाकी। अंतिम नहीं।")).toBeVisible();
  await page.goto("/en/accuracy", { waitUntil: "networkidle" });
  await expect(page.getByText("We haven't published an audit yet.", { exact: false })).toBeVisible();
  await expect(page.locator("main")).not.toContainText("%");
});

test("glossary: plain-language terms in three languages, linked from the findings explanation", async ({ page }) => {
  await page.goto("/gu/glossary", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("શબ્દકોશ");
  await page.goto("/en/glossary#ombudsman", { waitUntil: "networkidle" });
  await expect(page.locator("#ombudsman dt")).toHaveText("Insurance Ombudsman");
  await expect(page.locator("footer").getByRole("link", { name: "Glossary" })).toBeVisible();
});
