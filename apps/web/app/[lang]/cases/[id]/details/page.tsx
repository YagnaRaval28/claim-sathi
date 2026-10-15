"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Callout, CaseSteps, Disclaimer, PageTitle, ProblemNote, ProvenanceTag } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { formatInr } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useRequireUser } from "@/lib/use-session";

type Field = { name: string; value: string | null; display: string | null; status: string;
  confidence_flag: string; provenance: "document" | "user"; required: boolean };
type Facts = { fields: Field[]; confirmed: boolean; version: number };
type Item = { id: string; description: string; deducted_paise: number; clause_cited_verbatim: string | null;
  reason_verbatim: string | null };
type Items = { items: Item[]; totals: { deducted_paise: number; matches_disallowed: boolean }; confirmed: boolean;
  version: number };

export default function Details() {
  const { t, href } = useI18n();
  const { id } = useParams<{ id: string }>();
  const me = useRequireUser();
  const [facts, setFacts] = useState<Facts | null>(null);
  const [items, setItems] = useState<Items | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    try {
      setFacts(await api<Facts>(`/cases/${id}/facts`));
      setItems(await api<Items>(`/cases/${id}/line-items`));
    } catch (e) { setError(e); }
  }, [id]);
  useEffect(() => {
    if (!me) return;
    let alive = true;
    Promise.all([api<Facts>(`/cases/${id}/facts`), api<Items>(`/cases/${id}/line-items`)])
      .then(([f, i]) => { if (alive) { setFacts(f); setItems(i); } })
      .catch((e) => { if (alive) setError(e); });
    return () => { alive = false; };
  }, [me, id]);

  async function save(name: string) {
    if (!facts) return;
    try {
      setFacts(await api<Facts>(`/cases/${id}/facts`, { method: "PATCH",
        body: { base_version: facts.version, fields: [{ name, value: draft || null }] } }));
      setEditing(null);
      setItems(await api<Items>(`/cases/${id}/line-items`));
    } catch (e) { setError(e); }
  }

  async function confirm() {
    setError(null);
    try {
      if (!facts!.confirmed) await api(`/cases/${id}/facts/confirm`, { body: { base_version: facts!.version } });
      const li = await api<Items>(`/cases/${id}/line-items`);
      if (!li.confirmed) await api(`/cases/${id}/line-items/confirm`, { body: { base_version: li.version } });
      await load();
    } catch (e) { setError(e); await load(); }
  }

  if (!facts || !items) return <div className="page"><ProblemNote error={error} />{!error && t("common.loading")}</div>;
  const missing = error instanceof ApiError && error.problem.code === "required_fields_missing";
  const sorted = [...facts.fields].sort((x, y) => Number(y.confidence_flag === "please_check") - Number(x.confidence_flag === "please_check"));
  const shown = (f: Field) => f.name === "decision_type" && f.value ? t(`details.decisionTypes.${f.value}`) : f.display;
  const allConfirmed = facts.confirmed && items.confirmed;

  return (
    <div className="page">
      <CaseSteps caseId={id} current="details" />
      <PageTitle>{t("details.title")}</PageTitle>
      <p>{t("details.intro")}</p>
      {sorted.map((f) => (
        <div className="card" key={f.name} style={f.confidence_flag === "please_check" ? { borderColor: "var(--color-warning-border)" } : undefined}>
          <div className="ledger-row">
            <div>
              <div className="muted">{t(`details.fields.${f.name}`)}{f.required ? " *" : ""}</div>
              {editing === f.name ? (
                <input className="input" aria-label={t(`details.fields.${f.name}`)} value={draft} autoFocus
                       onChange={(e) => setDraft(e.target.value)} />
              ) : (
                <div className={f.name.endsWith("_paise") ? "amount" : undefined}>{shown(f) ?? t("details.notFound")}</div>
              )}
              {f.value !== null && <ProvenanceTag kind={f.provenance} />}
              {f.confidence_flag === "please_check" && <span className="pill pill-warning">⚑ {t("details.needsCheck")}</span>}
            </div>
            <div>
              {editing === f.name ? (
                <>
                  <button className="btn btn-primary" onClick={() => save(f.name)}>{t("details.save")}</button>{" "}
                  <button className="btn btn-ghost" onClick={() => setEditing(null)}>{t("details.cancel")}</button>
                </>
              ) : (
                <button className="btn btn-ghost" onClick={() => { setEditing(f.name); setDraft(f.display ?? ""); }}>
                  {t("details.edit")}
                </button>
              )}
            </div>
          </div>
        </div>
      ))}
      <h2>{t("details.deductions")}</h2>
      <p className="muted">{t("details.deductionsIntro")}</p>
      {items.items.map((i) => (
        <div className="card ledger-row" key={i.id}>
          <div>
            <strong>{i.description}</strong>
            <div className="muted">{t("details.clauseCited")}: {i.clause_cited_verbatim ?? t("details.noClause")}</div>
            {i.reason_verbatim && <div className="quote">{i.reason_verbatim}</div>}
          </div>
          <div className="amount">{formatInr(i.deducted_paise)}</div>
        </div>
      ))}
      <Callout tone={items.totals.matches_disallowed ? "success" : "warning"}>
        {formatInr(items.totals.deducted_paise)} · {items.totals.matches_disallowed ? t("details.matches") : t("details.mismatch")}
      </Callout>
      {missing && <Callout tone="error">{t("details.missing")}</Callout>}
      {!missing && <ProblemNote error={error} />}
      <div className="action-bar">
        {allConfirmed ? (
          <Link className="btn btn-primary btn-block" href={href(`/cases/${id}/findings`)}>{t("common.continue")} →</Link>
        ) : (
          <button className="btn btn-primary btn-block" onClick={confirm}>{t("details.confirm")}</button>
        )}
      </div>
      <Disclaimer />
    </div>
  );
}
