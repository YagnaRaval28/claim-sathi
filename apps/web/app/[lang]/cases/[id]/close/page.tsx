"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Callout, CaseSteps, Disclaimer, PageTitle, ProblemNote } from "@/components/ui";
import { api, newKey } from "@/lib/api";
import type { CaseSummary } from "@/lib/cases";
import { todayIst } from "@/lib/escalation";
import { formatDateDmy, parseRupeesToPaise } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useRequireUser } from "@/lib/use-session";

type Closed = CaseSummary & { retention: { delete_after: string | null; extended: boolean } };
const OUTCOMES = ["paid_in_full", "partly_paid", "not_paid", "withdrew"] as const;
const OMB = ["accepted", "dismissed_not_admissible", "dont_know"] as const;

// CASE-11 (FR-034): every question is optional; closing stops reminders and starts the retention clock.
export default function CloseCase() {
  const { t, href } = useI18n();
  const { id } = useParams<{ id: string }>();
  const { me, gate } = useRequireUser();
  const [c, setC] = useState<Closed | null>(null);
  const [outcome, setOutcome] = useState<string | null>(null);
  const [amount, setAmount] = useState("");
  const [omb, setOmb] = useState<string | null>(null);
  const [rating, setRating] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<Closed | null>(null);
  const key = useRef<string | null>(null);

  useEffect(() => { if (me) api<Closed>(`/cases/${id}`).then(setC).catch(setError); }, [me, id]);

  async function close(withAnswers: boolean) {
    setBusy(true);
    setError(null);
    try {
      if (withAnswers) {
        const paise = amount.trim() ? parseRupeesToPaise(amount) : null;
        await api(`/cases/${id}/outcome`, { method: "PUT", body: { outcome, amount_received_paise: paise,
          ombudsman_accepted: omb, rating, comment: comment.trim() || null } });
      }
      await api(`/cases/${id}/events`, { body: { kind: "closed", event_date: todayIst(), metadata: {} },
        idempotencyKey: (key.current ??= newKey()) });
      setDone(await api<Closed>(`/cases/${id}`));
    } catch (e) {
      setError(e);
      setBusy(false);
    }
  }

  if (!me) return gate;
  if (!c) return <div className="page"><ProblemNote error={error} />{!error && t("common.loading")}</div>;
  if (done || c.status === "closed") {
    const after = (done ?? c).retention.delete_after;
    return (
      <div className="page">
        <PageTitle>{t("close.title")}</PageTitle>
        <Callout tone="success">{t("close.done", { date: after ? formatDateDmy(after.slice(0, 10)) : "—" })}</Callout>
        <Link className="btn btn-secondary" href={href("/cases")}>{t("common.myCases")} →</Link>
      </div>
    );
  }
  const radios = (name: string, label: string, opts: readonly string[], prefix: string, v: string | null,
                  set: (x: string) => void) => (
    <fieldset className="field" style={{ border: 0, padding: 0 }}>
      <legend style={{ fontWeight: 600 }}>{label}</legend>
      {opts.map((o) => (
        <label key={o} className="check">
          <input type="radio" name={name} checked={v === o} onChange={() => set(o)} />
          <span>{t(`${prefix}.${o}`)}</span>
        </label>
      ))}
    </fieldset>
  );

  return (
    <div className="page reading">
      <CaseSteps caseId={id} current="track" />
      <PageTitle>{t("close.title")}</PageTitle>
      <p className="muted">{t("close.optional")}</p>
      {radios("outcome", t("close.outcome"), OUTCOMES, "close.outcomes", outcome, setOutcome)}
      <div className="field">
        <label htmlFor="amount">{t("close.amount")}</label>
        <input id="amount" className="input" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} />
      </div>
      {c.stage === "S3_OMBUDSMAN" && radios("omb", t("close.ombudsman"), OMB, "close.ombudsmanAnswers", omb, setOmb)}
      <fieldset className="field" style={{ border: 0, padding: 0 }}>
        <legend style={{ fontWeight: 600 }}>{t("close.rating")}</legend>
        {[1, 2, 3, 4, 5].map((n) => (
          <label key={n} className="check" style={{ display: "inline-flex", marginRight: 12 }}>
            <input type="radio" name="rating" checked={rating === n} onChange={() => setRating(n)} />
            <span>{n}</span>
          </label>
        ))}
      </fieldset>
      <div className="field">
        <label htmlFor="comment">{t("close.comment")}</label>
        <textarea id="comment" className="input" rows={3} maxLength={1000} value={comment}
                  onChange={(e) => setComment(e.target.value)} />
      </div>
      <ProblemNote error={error} />
      <div className="action-bar">
        <button className="btn btn-primary btn-block" disabled={busy} aria-busy={busy} onClick={() => close(true)}>
          {t("close.submit")}
        </button>
        <button className="btn btn-ghost btn-block" disabled={busy} onClick={() => close(false)}>{t("close.skip")}</button>
      </div>
      <Disclaimer />
    </div>
  );
}
