"use client";

import Link from "next/link";
import { useState } from "react";
import { ProblemNote } from "@/components/ui";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export type Abstention = { target_id: string | null; reason_code: string; recovery: string[] };

/**
 * FR-019 AbstentionState: why we couldn't assess something, and what the user can do next. The reason code and the
 * recovery actions come from the API's fixed mapping; this only renders them. Never hidden, never blank.
 */
export function AbstentionState({ caseId, gap, inline = false, onRerun, onRunAgain, busy }: {
  caseId: string; gap: Abstention; inline?: boolean; onRerun: () => void; onRunAgain: () => void; busy?: boolean;
}) {
  const { t, href } = useI18n();
  const [typing, setTyping] = useState(false);
  const code = gap.reason_code;
  const action = (r: string) => {
    if (r === "type_reason") {
      return (
        <button key={r} type="button" className="btn btn-secondary" aria-expanded={typing}
                onClick={() => setTyping(true)}>{t("abstain.actions.type_reason")}</button>
      );
    }
    if (r === "run_again") {
      return (
        <button key={r} type="button" className="btn btn-secondary" disabled={busy} onClick={onRunAgain}>
          {t("abstain.actions.run_again")}
        </button>
      );
    }
    const to = { upload_page: `/cases/${caseId}/documents`, upload_wording: `/cases/${caseId}/documents?type=policy_wording`,
      type_details: `/cases/${caseId}/details`,
      check_insurer: `/cases/${caseId}/details`, contact_support: "/contact" }[r];
    return to ? <Link key={r} className="btn btn-ghost" href={href(to)}>{t(`abstain.actions.${r}`)}</Link> : null;
  };
  return (
    <div className={inline ? "abstention abstention-inline" : "card abstention"} role="status">
      <p style={{ marginTop: 0 }}><span aria-hidden="true">◌ </span><strong>{t(`abstain.${code}.title`)}</strong></p>
      <p className="muted">{t(`abstain.${code}.why`)}</p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>{gap.recovery.map(action)}</div>
      {typing && <TypedReasonForm caseId={caseId} onSaved={() => { setTyping(false); onRerun(); }}
                                  onCancel={() => setTyping(false)} />}
    </div>
  );
}

/** "Type the reason yourself": saved verbatim as a confirmed detail, then the case is checked again. */
function TypedReasonForm({ caseId, onSaved, onCancel }: { caseId: string; onSaved: () => void; onCancel: () => void }) {
  const { t } = useI18n();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    setError(null);
    try {
      await api(`/cases/${caseId}/reasons`, { body: { text: String(f.get("text") ?? ""),
        clause_cited: String(f.get("clause") ?? "") || null } });
      onSaved();
    } catch (err) { setError(err); }
    setBusy(false);
  }

  return (
    <form onSubmit={submit} style={{ marginTop: 12 }}>
      <div className="field">
        <label htmlFor="typed-reason">{t("abstain.form.reason")}</label>
        <p className="muted" id="typed-reason-help">{t("abstain.form.reasonHelp")}</p>
        <textarea id="typed-reason" name="text" className="input" rows={3} required maxLength={500}
                  aria-describedby="typed-reason-help" />
      </div>
      <div className="field">
        <label htmlFor="typed-clause">{t("abstain.form.clause")}</label>
        <input id="typed-clause" name="clause" className="input" maxLength={200} />
      </div>
      <ProblemNote error={error} />
      <button className="btn btn-primary" disabled={busy}>{t("abstain.form.save")}</button>{" "}
      <button type="button" className="btn btn-ghost" onClick={onCancel}>{t("abstain.form.cancel")}</button>
    </form>
  );
}
