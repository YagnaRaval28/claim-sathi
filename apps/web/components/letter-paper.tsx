"use client";

import { useState } from "react";
import { ReportLink } from "@/components/dialogs";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export type Block = { type: string; text?: string; items?: string[]; footnote?: number };
export type Letter = {
  id: string; stage: "S1" | "S3"; version: number; reviewed_version: number | null; stale: boolean;
  doc: { blocks: Block[]; footnotes: { n: number; source_title: string; clause_ref: string | null; version: string;
    synthetic: boolean }[]; disclaimer: string };
};

/** Plain text of the letter, for "Copy as email text" (FR-028). Footnotes are kept as numbered sources. */
export function letterPlainText(letter: Letter, syntheticLabel: string): string {
  const body = letter.doc.blocks.map((b) => (b.type === "list" ? (b.items ?? []).join("\n")
    : b.type === "quote" ? `${b.text} [${b.footnote}]` : b.text ?? "")).join("\n\n");
  const notes = letter.doc.footnotes.map((n) =>
    `[${n.n}] ${n.source_title}, ${n.clause_ref ?? ""}, v${n.version}${n.synthetic ? ` ${syntheticLabel}` : ""}`);
  return [body, notes.join("\n"), letter.doc.disclaimer].filter(Boolean).join("\n\n");
}

/** The letter as paper. Grounds and verified quotes carry a "Something's wrong?" control (FR-035). */
export function LetterPaper({ caseId, letter }: { caseId: string; letter: Letter }) {
  const { t } = useI18n();
  return (
    <article className="paper" lang="en">
      {letter.doc.blocks.map((b, i) => (
        <div key={i}>
          {b.type === "list" ? (
            <ul style={{ listStyle: "none", paddingLeft: 16 }}>{b.items!.map((x) => <li key={x}>{x}</li>)}</ul>
          ) : b.type === "quote" ? (
            <blockquote className="quote">{b.text}<sup>[{b.footnote}]</sup></blockquote>
          ) : b.type === "heading" ? (
            <h3>{b.text}</h3>
          ) : (
            <p style={b.type === "subject" ? { fontWeight: 600 } : undefined}>{b.text}</p>
          )}
          {b.type === "quote" || (b.type === "para" && /^\d+\./.test(b.text ?? "")) ? (
            <ReportLink caseId={caseId} targetType="letter_block" targetId={letter.id} blockIndex={i} />
          ) : null}
        </div>
      ))}
      <hr />
      {letter.doc.footnotes.map((n) => (
        <p key={n.n} style={{ fontSize: 14 }}>[{n.n}] {n.source_title}, {n.clause_ref}, v{n.version}
          {n.synthetic && ` ${t("letter.syntheticSource")}`}</p>
      ))}
      <p className="muted">{letter.doc.disclaimer}</p>
    </article>
  );
}

/** Review gate + PDF download + copy-as-text. The API refuses export before review (AI-007). */
export function LetterActions({ letter, onChange, onError }: {
  letter: Letter; onChange: (l: Letter) => void; onError: (e: unknown) => void;
}) {
  const { t } = useI18n();
  const [read, setRead] = useState(false);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  async function download(format: "pdf" | "docx") {
    if (!read) return;
    setBusy(true);
    onError(null);
    try {
      if (letter.reviewed_version !== letter.version) {
        onChange(await api<Letter>(`/letters/${letter.id}/review`, { body: { version: letter.version } }));
      }
      const exp = await api<{ download_path: string }>(`/letters/${letter.id}/exports`, { body: { format } });
      window.location.assign(exp.download_path);
    } catch (e) { onError(e); }
    setBusy(false);
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(letterPlainText(letter, t("letter.syntheticSource")));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      window.getSelection()?.selectAllChildren(document.querySelector("article.paper") as Node);
    }
  }

  return (
    <>
      <label className="check">
        <input type="checkbox" checked={read} onChange={(e) => setRead(e.target.checked)} />
        <span>{t("letter.read")}</span>
      </label>
      <button className="btn btn-primary btn-block" onClick={() => download("pdf")} disabled={!read || busy}
              aria-disabled={!read || busy} aria-busy={busy}>
        {busy ? t("letter.downloading") : t("letter.download")}
      </button>
      <button className="btn btn-secondary btn-block" onClick={() => download("docx")} disabled={!read || busy}
              aria-disabled={!read || busy}>
        {t("letter.downloadDocx")}
      </button>
      {!read && <p className="muted">{t("letter.readFirst")}</p>}
      <button className="btn btn-secondary btn-block" onClick={copy} aria-live="polite">
        {copied ? `✓ ${t("letter.copied")}` : t("letter.copyText")}
      </button>
    </>
  );
}
