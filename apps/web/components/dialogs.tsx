"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { ProblemNote } from "@/components/ui";
import { api, newKey } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

/** Modal shell (design §6): labelled, focus moved in and trapped, Escape closes (unless busy), focus returned. */
export function Dialog({ title, onClose, busy, children }: {
  title: string; onClose: () => void; busy?: boolean; children: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const opener = useRef<Element | null>(null);
  useEffect(() => {
    opener.current = document.activeElement;
    ref.current?.querySelector<HTMLElement>("input, button, textarea, select, [tabindex]")?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) onClose();
      if (e.key !== "Tab" || !ref.current) return;
      const items = ref.current.querySelectorAll<HTMLElement>("input, button, textarea, select, a[href]");
      if (!items.length) return;
      const first = items[0], last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    window.addEventListener("keydown", key);
    return () => {
      window.removeEventListener("keydown", key);
      (opener.current as HTMLElement | null)?.focus?.();
    };
  }, [onClose, busy]);
  return (
    <>
      <div className="sheet-backdrop" onClick={() => !busy && onClose()} />
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="dlg-title" ref={ref}>
        <h2 id="dlg-title" style={{ marginTop: 0 }}>{title}</h2>
        {children}
      </div>
    </>
  );
}

/**
 * TypedConfirmDialog (DD-10): the server issues a 4-digit code; the user types it; the confirm button stays
 * disabled until it matches. The challenge travels in `X-Confirm-Challenge`.
 */
export function TypedConfirmDialog({ title, body, confirmLabel, challengePath, run, onClose }: {
  title: string; body: string; confirmLabel: string; challengePath: string;
  run: (code: string, challenge: string) => Promise<void>; onClose: () => void;
}) {
  const { t } = useI18n();
  const [challenge, setChallenge] = useState<{ challenge_id: string; code: string } | null>(null);
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    let alive = true;  // a discarded effect's code must never replace the one on screen
    api<{ challenge_id: string; code: string }>(challengePath, { body: {} })
      .then((ch) => { if (alive) setChallenge(ch); })
      .catch((e) => { if (alive) setError(e); });
    return () => { alive = false; };
  }, [challengePath]);

  async function confirm() {
    if (!challenge || typed !== challenge.code) return;
    setBusy(true);
    setError(null);
    try {
      await run(typed, challenge.challenge_id);
    } catch (e) {
      setError(e);
      setBusy(false);
    }
  }

  return (
    <Dialog title={title} onClose={onClose} busy={busy}>
      <p>{body}</p>
      {challenge && (
        <div className="field">
          <label htmlFor="typed-code">{t("confirm.typeCode", { code: challenge.code })}</label>
          <input id="typed-code" className="input" inputMode="numeric" autoComplete="off" maxLength={4} value={typed}
                 aria-label={t("confirm.codeLabel")} onChange={(e) => setTyped(e.target.value.replace(/\D/g, ""))} />
        </div>
      )}
      <ProblemNote error={error} />
      <button className="btn btn-danger" disabled={!challenge || typed !== challenge.code || busy} aria-busy={busy}
              onClick={confirm}>{confirmLabel}</button>{" "}
      <button className="btn btn-secondary" disabled={busy} onClick={onClose}>{t("confirm.cancel")}</button>
    </Dialog>
  );
}

const REASONS = ["wrong_fact", "wrong_rule", "bad_translation", "other"] as const;

/** ReportDialog (FR-035, design F10). The API stores only the flagged output and its citations. */
export function ReportLink({ caseId, targetType, targetId, blockIndex }: {
  caseId: string; targetType: "counter_point" | "citation" | "letter_block"; targetId: string; blockIndex?: number;
}) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState<(typeof REASONS)[number]>("wrong_fact");
  const [comment, setComment] = useState("");
  const [grant, setGrant] = useState(false);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const key = useRef<string | null>(null);

  async function send() {
    setBusy(true);
    setError(null);
    try {
      await api("/reports", {
        idempotencyKey: (key.current ??= newKey()),
        body: { case_id: caseId, target_type: targetType, target_id: targetId, block_index: blockIndex ?? null,
          reason, comment: comment.trim() || null, grant_access: grant },
      });
      setDone(true);
      setOpen(false);
    } catch (e) { setError(e); }
    setBusy(false);
  }

  if (done) return <span className="pill pill-neutral" role="status">{t("report.reported")} · {t("report.thanks")}</span>;
  return (
    <>
      <button type="button" className="btn btn-ghost" onClick={() => setOpen(true)}>{t("report.link")}</button>
      {open && (
        <Dialog title={t("report.title")} onClose={() => setOpen(false)} busy={busy}>
          <fieldset className="field" style={{ border: 0, padding: 0 }}>
            <legend className="visually-hidden">{t("report.title")}</legend>
            {REASONS.map((r) => (
              <label key={r} className="check">
                <input type="radio" name="report-reason" checked={reason === r} onChange={() => setReason(r)} />
                <span>{t(`report.reasons.${r}`)}</span>
              </label>
            ))}
          </fieldset>
          <div className="field">
            <label htmlFor="report-comment">{t("report.comment")}</label>
            <textarea id="report-comment" className="input" maxLength={1000} rows={3} value={comment}
                      onChange={(e) => setComment(e.target.value)} />
          </div>
          <label className="check">
            <input type="checkbox" checked={grant} onChange={(e) => setGrant(e.target.checked)} />
            <span>{t("report.grant")}</span>
          </label>
          <ProblemNote error={error} />
          <button className="btn btn-primary" disabled={busy} aria-busy={busy} onClick={send}>{t("report.send")}</button>{" "}
          <button className="btn btn-secondary" disabled={busy} onClick={() => setOpen(false)}>{t("confirm.cancel")}</button>
        </Dialog>
      )}
    </>
  );
}

export function Saved({ show }: { show: boolean }) {
  const { t } = useI18n();
  return show ? <span className="pill pill-success" role="status">✓ {t("common.saved")}</span> : null;
}
