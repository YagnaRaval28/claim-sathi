"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Callout, CaseSteps, Disclaimer, PageTitle, ProblemNote } from "@/components/ui";
import { api } from "@/lib/api";
import type { CheckResult, Escalation } from "@/lib/escalation";
import { formatDateDmy } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useRequireUser } from "@/lib/use-session";

const STYLE: Record<CheckResult, [string, string]> = {
  block: ["pill-error", "✕"],
  unavailable: ["pill-error", "✕"],
  warn: ["pill-warning", "⚠"],
  inform: ["pill-info", "ⓘ"],
  pass: ["pill-success", "✓"],
};

// CASE-09: every row comes from the API's deterministic RULE-ESC checks; nothing is decided here.
export default function OmbudsmanChecks() {
  const { t, href } = useI18n();
  const { id } = useParams<{ id: string }>();
  const { me, gate } = useRequireUser();
  const [e, setE] = useState<Escalation | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(() => api<Escalation>(`/cases/${id}/escalation`).then(setE).catch(setError), [id]);
  useEffect(() => { if (me) void load(); }, [me, load]);

  async function ack(ruleKey: string) {
    setError(null);
    try {
      await api(`/cases/${id}/escalation/acknowledgements`, { body: { rule_keys: [ruleKey] } });
      await load();
    } catch (err) { setError(err); }
  }

  if (!me) return gate;
  if (!e) return <div className="page"><ProblemNote error={error} />{!error && t("common.loading")}</div>;
  const warnings = e.ombudsman_checks.filter((c) => c.result === "warn");
  const allAcked = warnings.every((c) => c.acknowledged);
  const filed = e.events.some((x) => x.kind === "s3_filed");
  const message = (key: string, params: Record<string, string>) =>
    t(`ombudsman.messages.${key}`, { date: params.date ? formatDateDmy(params.date) : "", name: params.name ?? "" });

  return (
    <div className="page">
      <CaseSteps caseId={id} current="track" />
      <PageTitle>{t("ombudsman.title")}</PageTitle>
      <ProblemNote error={error} />
      {e.ombudsman_checks.map((c) => {
        const [pill, icon] = STYLE[c.result];
        return (
          <div className="card check-row" key={c.rule_key}>
            <span className={`pill ${pill}`}><span aria-hidden="true">{icon}</span> {t(`ombudsman.results.${c.result}`)}</span>
            <div style={{ flex: 1 }}>
              <p style={{ marginTop: 0 }}>{message(c.message_key, c.params)}</p>
              {c.source_ref && <p className="muted">{t("ombudsman.source")}: {c.source_ref}</p>}
              {c.fix_action && (
                <Link className="btn btn-secondary" href={href(`/cases/${id}/track`)}>{t(`ombudsman.fix.${c.fix_action}`)}</Link>
              )}
              {c.result === "warn" && (
                <label className="check">
                  <input type="checkbox" checked={c.acknowledged} disabled={c.acknowledged} onChange={() => ack(c.rule_key)} />
                  <span>{t("ombudsman.acknowledge")}</span>
                </label>
              )}
            </div>
          </div>
        );
      })}
      {!e.blocked && !filed && (
        <div className="action-bar">
          {allAcked ? (
            <>
              <Callout tone="success">{t("ombudsman.ready")}</Callout>
              <Link className="btn btn-primary btn-block" href={href(`/cases/${id}/track`)}>{t("ombudsman.logFiled")}</Link>
            </>
          ) : <p className="muted">{t("ombudsman.needAck")}</p>}
        </div>
      )}
      <Disclaimer />
    </div>
  );
}
