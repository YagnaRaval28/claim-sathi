import { expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import path from "node:path";
import { deflateSync } from "node:zlib";

export const MAILPIT = process.env.MAILPIT_URL ?? "http://127.0.0.1:8025";
const FIXTURES = path.resolve(__dirname, "../../../eval/fixtures/documents");

/** The sign-in code from the newest Mailpit message to `email` (local mail catcher only). */
export async function codeFor(email: string): Promise<string> {
  for (let i = 0; i < 40; i++) {
    const r = await fetch(`${MAILPIT}/api/v1/search?query=${encodeURIComponent(`to:${email}`)}`);
    const msgs = ((await r.json()) as { messages?: { ID: string }[] }).messages ?? [];
    if (msgs.length) {
      const m = (await (await fetch(`${MAILPIT}/api/v1/message/${msgs[0].ID}`)).json()) as { Text: string };
      const code = /\b(\d{6})\b/.exec(m.Text)?.[1];
      if (code) return code;
    }
    await new Promise((res) => setTimeout(res, 500));
  }
  throw new Error("no sign-in email arrived in Mailpit");
}

function fixtureLines(name: string): string[] {
  return readFileSync(path.join(FIXTURES, name), "utf-8").split(/\r?\n/).filter((l) => l.length > 0);
}

export const syn001Pdf = () => textPdf(fixtureLines("SYN-001-settlement-letter.txt"));
export const syn002Pdf = () => textPdf(fixtureLines("SYN-002-repudiation-letter.txt"));

/** A minimal text-layer PDF (same layout as apps/api devtools/pdfgen.py). SYNTHETIC text only. */
export function textPdf(lines: string[]): Buffer {
  const esc = (s: string) => s.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");
  const ops = ["BT", "/F1 10 Tf", "12 TL", "50 800 Td", ...lines.map((l) => `(${esc(l)}) Tj T*`), "ET"].join("\n");
  const stream = deflateSync(Buffer.from(ops, "latin1"));
  const objs: Buffer[] = [
    Buffer.from("<< /Type /Catalog /Pages 2 0 R >>"),
    Buffer.from("<< /Type /Pages /Kids [3 0 R] /Count 1 >>"),
    Buffer.from("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"),
    Buffer.concat([Buffer.from(`<< /Length ${stream.length} /Filter /FlateDecode >>\nstream\n`), stream, Buffer.from("\nendstream")]),
    Buffer.from("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"),
  ];
  const parts: Buffer[] = [Buffer.from("%PDF-1.4\n")];
  const offsets: number[] = [];
  let pos = parts[0].length;
  objs.forEach((o, i) => {
    const b = Buffer.concat([Buffer.from(`${i + 1} 0 obj\n`), o, Buffer.from("\nendobj\n")]);
    offsets.push(pos);
    parts.push(b);
    pos += b.length;
  });
  const xref = [`xref\n0 ${objs.length + 1}\n0000000000 65535 f \n`, ...offsets.map((o) => `${String(o).padStart(10, "0")} 00000 n \n`)].join("");
  parts.push(Buffer.from(`${xref}trailer\n<< /Size ${objs.length + 1} /Root 1 0 R >>\nstartxref\n${pos}\n%%EOF\n`));
  return Buffer.concat(parts);
}

export async function signIn(page: Page, email: string, lang = "en"): Promise<void> {
  await page.goto(`/${lang}/sign-in`, { waitUntil: "networkidle" });
  await page.locator("#email").fill(email);
  await page.locator("form button").click();
  await expect(page).toHaveURL(new RegExp(`/${lang}/sign-in/verify$`));
  await page.waitForLoadState("networkidle");
  await page.locator("#code").fill(await codeFor(email));
}

/** Sign in, consent and create a case (English). Returns on the documents page. */
export async function newCase(page: Page, situation: "Partly paid" | "Rejected"): Promise<void> {
  await signIn(page, `e2e-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`);
  await expect(page).toHaveURL(/\/en\/welcome\/consent$/);
  await page.getByRole("checkbox").first().check();
  await page.getByRole("button", { name: "Agree and continue" }).click();
  await expect(page).toHaveURL(/\/en\/cases$/);
  await page.getByRole("link", { name: /New case/ }).click();
  const pick = (group: string, option: string) =>
    page.getByRole("group", { name: group }).getByLabel(option, { exact: true }).check();
  await pick("Is this a health insurance claim with an insurer in India?", "Yes");
  await pick("What happened to the claim?", situation);
  await pick("What kind of policy is it?", "Family floater");
  await page.getByLabel("Policyholder's full name").fill("Ravi K. Mehta");
  await pick("Your relationship to the policyholder", "Self");
  await pick("Is this matter already in any court, consumer commission or arbitration?", "No");
  await page.getByRole("button", { name: "Create case" }).click();
  await expect(page).toHaveURL(/\/documents$/);
}

export async function uploadAndContinue(page: Page, pdf: Buffer): Promise<void> {
  await page.locator("#file").setInputFiles({ name: "letter.pdf", mimeType: "application/pdf", buffer: pdf });
  await page.getByRole("button", { name: "Upload" }).click();
  const next = page.getByRole("link", { name: /Continue to check details/ });
  await expect(next).toBeVisible({ timeout: 60_000 });
  await next.click();
  await expect(page).toHaveURL(/\/details$/);
}
