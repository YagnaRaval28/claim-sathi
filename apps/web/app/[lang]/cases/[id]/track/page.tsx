"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { Callout, CaseSteps, Disclaimer, PageTitle, ProblemNote } from "@/components/ui";
import { api, newKey } from "@/lib/api";
import { EVENT_KINDS, todayIst, urgency, type EventKind, type Escalation } from "@/lib/escalation";
import { formatDateDmy, formatInr, parseRupeesToPaise } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useRequireUser } from "@/lib/use-session";

type Draft = { kind: EventKind; date: string; method: string; satisfied: string; token: string; reference: string;
  result: string; amount: string };

const EMPTY: Draft = { kind: "s1_sent", date: "", method: "email", satisfied: "no", token: "", reference: "",
  result: "award", amount: "" };

function EventSheet({ caseId, initial, onDone, onCancel }: {
  caseId: string; initial: EventKind; onDone: (kind: EventKind) => void; onCancel: () => void;
}) {
  const { t } = useI18n();
  const [d, setD] = useState<Draft>({ ...EMPTY, kind: initial, date: todayIst() });
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const key = useRef<string | null>(null);
  const set = (k: keyof Draft) => (v: string) => setD((x) => ({ ...x, [k]: v }));

  async function save(e: React.FormEvent) {
    e.preventDefault();
    const metadata: Record<string, unknown> = {};
    if (d.kind === "s1_sent") metadata.method = d.method;
    if (d.kind === "insurer_reply") metadata.satisfied = d.satisfied === "yes";
    if (d.kind === "s2_filed" && d.token.trim()) metadata.token = d.token.trim();
    if (d.kind === "s3_filed" && d.reference.trim()) metadata.reference = d.reference.trim();
    if (d.kind === "ombudsman_outcome") metadata.result = d.result;
    if (d.kind === "payment_received" && d.amount.trim()) {
      const paise = parseRupeesToPaise(d.amount);
      if (paise === null) { setError(new Error("amount")); return; }
      metadata.amount_paise = paise;
    }
    setBusy(true);
    setError(null);
    try {
      await api(`/cases/${caseId}/events`, { body: { kind: d.kind, event_date: d.date, metadata },
        idempotencyKey: (key.current ??= newKey()) });
      onDone(d.kind);
    } catch (err) {
      key.current = null;
      setError(err);
      setBusy(false);
    }
  }

  const radios = (name: keyof Draft, label: string, options: [string, string][]) => (
    <fieldset className="field" style={{ border: 0, padding: 0 }}>
      <legend style={{ fontWeight: 600 }}>{label}</legend>
      {options.map(([v, text]) => (
        <label key={v} className="check">
          <input type="radio" name={name} value={v} checked={d[name] === v} onChange={() => set(name)(v)} />
          <span>{text}</span>
        </label>
      ))}
    </fieldset>
  );

  return (
    <form className="card" onSubmit={save} aria-labelledby="sheet-title">
      <h2 id="sheet-title" style={{ marginTop: 0 }}>{t("track.sheet.title")}</h2>
      {radios("kind", t("track.sheet.what"), EVENT_KINDS.map((k) => [k, t(`track.events.${k}`)]))}
      <div className="field">
        <label htmlFor="ev-date">{t("track.sheet.date")}</label>
        <input id="ev-date" className="input" type="date" required value={d.date} max={todayIst()}
               onChange={(e) => set("date")(e.target.value)} />
        <span className="muted">{t("track.sheet.dateHint")}</span>
      </div>
      {d.kind === "s1_sent" && radios("method", t("track.sheet.method"),
        (["email", "post", "portal"] as const).map((m) => [m, t(`track.meta.method.${m}`)]))}
      {d.kind === "insurer_reply" && (
        <>
          {radios("satisfied", t("track.sheet.satisfied"), [["no", t("track.sheet.no")], ["yes", t("track.sheet.yes")]])}
          <Callout tone="info">{t("track.sheet.replyHint")}</Callout>
        </>
      )}
      {d.kind === "s2_filed" && (
        <div className="field">
          <label htmlFor="ev-token">{t("track.sheet.token")}</label>
          <input id="ev-token" className="input" maxLength={40} value={d.token} onChange={(e) => set("token")(e.target.value)} />
        </div>
      )}
      {d.kind === "s3_filed" && (
        <div className="field">
          <label htmlFor="ev-ref">{t("track.sheet.reference")}</label>
          <input id="ev-ref" className="input" maxLength={40} value={d.reference}
                 onChange={(e) => set("reference")(e.target.value)} />
        </div>
      )}
      {d.kind === "ombudsman_outcome" && radios("result", t("track.sheet.result"),
        (["award", "dismissed", "settled", "withdrawn", "other"] as const).map((r) => [r, t(`track.meta.result.${r}`)]))}
      {d.kind === "payment_received" && (
        <div className="field">
          <label htmlFor="ev-amount">{t("track.sheet.amount")}</label>
          <input id="ev-amount" className="input" inputMode="decimal" value={d.amount}
                 onChange={(e) => set("amount")(e.target.value)} />
        </div>
      )}
      {error instanceof Error && error.message === "amount"
        ? <Callout tone="error">{t("details.invalidAmount")}</Callout>
        : <ProblemNote error={error} />}
      <button className="btn btn-primary" disabled={busy || !d.date} aria-busy={busy}>{t("track.sheet.save")}</button>{" "}
      <button type="button" className="btn btn-ghost" onClick={onCancel}>{t("track.sheet.cancel")}</button>
    </form>
  );
}

export default function Track() {
  const { t, href } = useI18n();
  const { id } = useParams<{ id: string }>();
  const { me, gate } = useRequireUser();
  const [e, setE] = useState<Escalation | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [sheet, setSheet] = useState<EventKind | null>(null);
  const [replyLogged, setReplyLogged] = useState(false);

  const load = useCallback(() => api<Escalation>(`/cases/${id}/escalation`).then(setE).catch(setError), [id]);
  useEffect(() => { if (me) void load(); }, [me, load]);

  async function remove(eventId: string) {
    setError(null);
    try {
      await api(`/cases/${id}/events/${eventId}`, { method: "DELETE" });
      await load();
    } catch (err) { setError(err); }
  }


  if (!me) return gate;
  if (!e) return <div className="page"><ProblemNote error={error} />{!error && t("common.loading")}</div>;

  const closed = e.status === "closed";
  const blockReason = e.ombudsman_checks.find((c) => c.result === "block" || c.result === "unavailable");
  const reasonText = blockReason ? t(`ombudsman.messages.${blockReason.message_key}`,
    { date: blockReason.params.date ? formatDateDmy(blockReason.params.date) : "" }) : "";
  const s1 = e.events.find((x) => x.kind === "s1_sent");
  const s3 = e.events.find((x) => x.kind === "s3_filed");
  const stageState = (step: "insurer" | "ombudsman") => {
    if (step === "insurer") return s1 ? (e.stage === "S1_INSURER_GRIEVANCE" ? "current" : "done") : "current";
    return s3 ? "current" : "pending";
  };
  const basisText = (from: Record<string, string>) => Object.entries(from)
    .filter(([k]) => k !== "basis")
    .map(([k, v]) => t(`track.basisKeys.${k}`).replace("{date}", formatDateDmy(v)))
    .join(", ");

  return (
    <div className="page">
      <CaseSteps caseId={id} current="track" />
      <PageTitle>{t("track.title")}</PageTitle>
      <ProblemNote error={error} />

      <div className="card" aria-live="polite">
        <p style={{ fontSize: 18, marginTop: 0 }}>
          {t(`track.nextAction.${e.next_action.key}`, { date: e.next_action.date ? formatDateDmy(e.next_action.date) : "" })}
        </p>
        {!closed && (
          <>
            {e.next_action.key === "go_to_ombudsman" ? (
              <Link className="btn btn-primary" href={href(`/cases/${id}/track/ombudsman`)}>{t("track.goOmbudsman")} →</Link>
            ) : (
              <button className="btn btn-primary" onClick={() => setSheet(e.stage === "S0_PREPARE" ? "s1_sent"
                : e.next_action.key === "log_reply" ? "insurer_reply" : "s1_sent")}>{t("track.logUpdate")}</button>
            )}{" "}
            {e.next_action.key !== "go_to_ombudsman" && (
              <Link className="btn btn-secondary" href={href(`/cases/${id}/track/ombudsman`)}>{t("track.goOmbudsman")}</Link>
            )}
          </>
        )}
      </div>

      {sheet && (
        <EventSheet caseId={id} initial={sheet} onCancel={() => setSheet(null)}
                    onDone={(kind) => { setSheet(null); setReplyLogged(kind === "insurer_reply"); void load(); }} />
      )}
      {replyLogged && (
        <Callout tone="info">{t("track.sheet.replyHint")}{" "}
          <Link href={href(`/cases/${id}/documents`)}>{t("track.sheet.goDocuments")}</Link>
        </Callout>
      )}

      <h2>{t("track.deadlines")}</h2>
      {e.deadlines.length === 0 && <p className="muted">{t("track.noDeadlines")}</p>}
      {e.deadlines.map((d) => {
        const u = urgency(d.days_left);
        const pill = { neutral: "pill-neutral", info: "pill-info", warning: "pill-warning", error: "pill-error" }[u.tone];
        return (
          <div className="card" key={d.kind}>
            <div className="ledger-row">
              <div>
                <div className="muted">{t(`track.deadlineKinds.${d.kind}`)}</div>
                <strong>{formatDateDmy(d.due_date)}</strong>
              </div>
              <span className={`pill ${pill}`}>
                <span aria-hidden="true">{u.icon}</span>{" "}
                {d.days_left < 0 ? t("track.passedOn", { date: formatDateDmy(d.due_date) })
                  : d.days_left === 0 ? t("track.dueToday") : t("track.daysLeft", { days: d.days_left })}
              </span>
            </div>
            {d.kind === "insurer_response_expected" && <p className="muted">{t("track.responseNote")}</p>}
            <details>
              <summary>{t("track.howCalculated")}</summary>
              <p className="muted">{t("track.basis", { basis: basisText(d.computed_from), source: d.rule.source_ref ?? d.rule.key })}</p>
            </details>
          </div>
        );
      })}
      {e.deadlines.some((d) => d.status === "active") && (
        <a className="btn btn-secondary" href={`/api/v1/cases/${id}/deadlines.ics`} download>{t("track.addToCalendar")}</a>
      )}

      <h2>{t("track.stages")}</h2>
      <div className="stage-grid">
        <div className="stage-card" data-state={stageState("insurer")}>
          <strong>1. {t("track.stageInsurer")}</strong>
          <p className="muted">{s1 ? t("track.filedOn", { date: formatDateDmy(s1.event_date) }) : t("track.current")}</p>
        </div>
        <div className="stage-card" data-state={e.s2_filed_at ? "current" : "pending"}>
          <strong>2. {t("track.stageBima")}</strong>
          <p className="muted">{t("track.optional")}</p>
          {e.s2_filed_at && <p>{t("track.filedOn", { date: formatDateDmy(e.s2_filed_at) })}</p>}
          <Link href={href(`/cases/${id}/track/bima-bharosa`)}>{t("track.bimaContent")} →</Link>
        </div>
        <div className="stage-card" data-state={stageState("ombudsman")}>
          <strong>3. {t("track.stageOmbudsman")}</strong>
          <p className="muted">
            {s3 ? t("track.filedOn", { date: formatDateDmy(s3.event_date) })
              : e.blocked ? t("track.locked", { reason: reasonText }) : t("track.eligible")}
          </p>
        </div>
      </div>

      <h2>{t("track.timeline")}</h2>
      {e.events.length === 0 ? <p className="muted">{t("track.empty")}</p> : (
        <ol className="timeline">
          {e.events.map((ev) => (
            <li key={ev.id}>
              <div className="muted">{formatDateDmy(ev.event_date)}</div>
              <strong>{t(`track.events.${ev.kind}`)}</strong>
              {ev.kind === "s1_sent" && ev.metadata.method && <> · {t(`track.meta.method.${ev.metadata.method}`)}</>}
              {ev.kind === "insurer_reply" && <> · {t(`track.meta.satisfied.${String(ev.metadata.satisfied)}`)}</>}
              {ev.kind === "ombudsman_outcome" && <> · {t(`track.meta.result.${ev.metadata.result}`)}</>}
              {ev.kind === "payment_received" && typeof ev.metadata.amount_paise === "number" && (
                <> · {formatInr(ev.metadata.amount_paise)}</>
              )}
              {(ev.metadata.token || ev.metadata.reference) && <> · {String(ev.metadata.token ?? ev.metadata.reference)}</>}
              {" "}
              <button className="btn btn-ghost" onClick={() => remove(ev.id)}
                      aria-label={`${t("track.remove")}: ${t(`track.events.${ev.kind}`)}`}>{t("track.remove")}</button>
            </li>
          ))}
        </ol>
      )}

      {!closed && (
        <div className="action-bar">
          <Link className="btn btn-ghost btn-block" href={href(`/cases/${id}/close`)}>{t("track.closeCase")}</Link>
        </div>
      )}
      <p><Link href={href(`/cases/${id}/settings`)}>{t("caseSettings.link")} →</Link></p>
      <Disclaimer />
    </div>
  );
}
