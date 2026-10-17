"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ProblemNote } from "@/components/ui";
import type { Block, Letter } from "@/components/letter-paper";
import { api, ApiError } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type EditBlock = Block & { citation_id?: string; quote?: string; edited?: boolean };
const AUTOSAVE_MS = 10_000;

/**
 * FR-027 block editor. Verified quotes are protected spans: changing one shows "no longer a verified quote"
 * (the server then saves it as plain text without its footnote). Undo restores the exact original, which the
 * server recognises as verified again. Autosaves every 10 s and on blur.
 */
export function LetterEditor({ letter, onSaved, onDone }: {
  letter: Letter; onSaved: (l: Letter) => void; onDone: () => void;
}) {
  const { t } = useI18n();
  const [originals] = useState(() => new Map((letter.doc.blocks as EditBlock[])
    .filter((b) => b.type === "quote" && b.citation_id).map((b) => [b.citation_id!, b.text ?? ""])));
  const [blocks, setBlocks] = useState<EditBlock[]>(() => letter.doc.blocks.map((b) => ({ ...b })));
  const [history, setHistory] = useState<EditBlock[][]>([]);
  const [dirty, setDirty] = useState(false);
  const [status, setStatus] = useState<"idle" | "saving" | "saved">("idle");
  const [error, setError] = useState<unknown>(null);
  const version = useRef(letter.version);

  const change = (next: EditBlock[]) => {
    setHistory((h) => [...h.slice(-49), blocks]);
    setBlocks(next);
    setDirty(true);
  };
  const setText = (i: number, text: string) => change(blocks.map((b, n) => (n === i ? { ...b, text } : b)));
  const setItem = (i: number, j: number, text: string) =>
    change(blocks.map((b, n) => (n === i ? { ...b, items: (b.items ?? []).map((x, k) => (k === j ? text : x)) } : b)));
  const addAfter = (i: number) => change([...blocks.slice(0, i + 1), { type: "para", text: "" }, ...blocks.slice(i + 1)]);
  const remove = (i: number) => change(blocks.filter((_, n) => n !== i));
  const undo = () => {
    const prev = history.at(-1);
    if (!prev) return;
    setHistory((h) => h.slice(0, -1));
    setBlocks(prev);
    setDirty(true);
  };
  const verified = (b: EditBlock) =>
    b.type === "quote" && !!b.citation_id && originals.get(b.citation_id) === b.text;

  const save = useCallback(async () => {
    if (!dirty) return;
    setStatus("saving");
    setError(null);
    try {
      const out = await api<Letter>(`/letters/${letter.id}`, { method: "PATCH",
        body: { base_version: version.current, blocks } });
      version.current = out.version;
      setDirty(false);
      setStatus("saved");
      onSaved(out);
    } catch (e) {
      setStatus("idle");
      setError(e);
      if (e instanceof ApiError && e.problem.code === "version_conflict" && e.problem.current_version !== undefined) {
        version.current = e.problem.current_version;
      }
    }
  }, [blocks, dirty, letter.id, onSaved]);

  useEffect(() => {
    if (!dirty) return;
    const h = setTimeout(() => void save(), AUTOSAVE_MS);
    return () => clearTimeout(h);
  }, [dirty, save]);

  return (
    <div className="paper" lang="en">
      <div className="ledger-row" style={{ marginBottom: 12 }}>
        <span aria-live="polite" className="muted">
          {status === "saving" ? t("letter.saving") : status === "saved" && !dirty ? `✓ ${t("letter.saved")}` : ""}
        </span>
        <span>
          <button type="button" className="btn btn-ghost" onClick={undo} disabled={!history.length}>{t("letter.undo")}</button>{" "}
          <button type="button" className="btn btn-primary" onClick={async () => { await save(); onDone(); }}>
            {t("letter.doneEditing")}
          </button>
        </span>
      </div>
      {blocks.map((b, i) => (
        <div key={i} style={{ marginBottom: 12 }}>
          {b.type === "list" ? (
            (b.items ?? []).map((x, j) => (
              <textarea key={j} className="input" rows={2} value={x} aria-label={`${t("letter.paragraph")} ${i + 1}.${j + 1}`}
                        onChange={(e) => setItem(i, j, e.target.value)} onBlur={() => void save()} />
            ))
          ) : (
            <textarea className="input" rows={b.type === "para" || b.type === "quote" ? 3 : 1} value={b.text ?? ""}
                      aria-label={`${t("letter.paragraph")} ${i + 1}`}
                      onChange={(e) => setText(i, e.target.value)} onBlur={() => void save()} />
          )}
          {b.type === "quote" && (verified(b)
            ? <span className="pill pill-verified">✓ {t("provenance.verified")}</span>
            : <span className="pill pill-warning" role="status">⚠ {t("letter.unverified")}</span>)}
          {b.edited && <span className="pill pill-neutral">✎ {t("letter.editedNote")}</span>}
          <span>
            <button type="button" className="btn btn-ghost" onClick={() => addAfter(i)}>{t("letter.addParagraph")}</button>
            {b.type === "para" && !b.citation_id && (
              <button type="button" className="btn btn-ghost" onClick={() => remove(i)}>{t("details.remove")}</button>
            )}
          </span>
        </div>
      ))}
      <ProblemNote error={error} />
    </div>
  );
}
