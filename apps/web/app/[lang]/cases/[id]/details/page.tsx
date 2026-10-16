"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Callout, CaseSteps, Disclaimer, PageTitle, ProblemNote, ProvenanceTag } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { formatInr, parseRupeesToPaise } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useRequireUser } from "@/lib/use-session";

type Field = { name: string; value: string | null; display: string | null; status: string;
  confidence_flag: string; provenance: "document" | "user"; required: boolean };
type Facts = { fields: Field[]; confirmed: boolean; version: number; extraction: "running" | "done" | "failed" | "none" };
type Item = { id: string; description: string; deducted_paise: number; clause_cited_verbatim: string | null;
  reason_verbatim: string | null; user_entered: boolean; billed_paise: number | null };
type Items = { items: Item[]; totals: { deducted_paise: number; matches_disallowed: boolean }; confirmed: boolean;
  version: number };
type Row = { key: string; description: string; amount: string; clause: string; source?: Item };

const DATE_FIELDS = new Set(["decision_letter_date", "admission_date", "discharge_date", "first_inception_date"]);
const DECISIONS = ["partial", "repudiation"] as const;

function toRows(items: Item[]): Row[] {
  return items.map((i) => ({ key: i.id, description: i.description, amount: formatInr(i.deducted_paise).slice(1),
    clause: i.clause_cited_verbatim ?? "", source: i }));
}

export default function Details() {
  const { t, href } = useI18n();
  const { id } = useParams<{ id: string }>();
  const { me, gate } = useRequireUser();
  const [facts, setFacts] = useState<Facts | null>(null);
  const [items, setItems] = useState<Items | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [rows, setRows] = useState<Row[] | null>(null);
  const [rowErrors, setRowErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const [f, i] = await Promise.all([api<Facts>(`/cases/${id}/facts`), api<Items>(`/cases/${id}/line-items`)]);
    setFacts(f);
    setItems(i);
    return f;
  }, [id]);

  useEffect(() => {
    if (!me) return;
    let alive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const tick = () => {
      load()
        .then((f) => { if (alive && f.extraction === "running") timer = setTimeout(tick, 2000); })
        .catch((e) => { if (alive) setError(e); });
    };
    tick();
    return () => { alive = false; clearTimeout(timer); };
  }, [me, load]);

  async function reloadAfter(e: unknown) {
    setError(e);
    if (e instanceof ApiError && e.problem.code === "version_conflict") await load().catch(() => undefined);
  }

  async function save(name: string, value: string) {
    if (!facts) return;
    setBusy(true);
    setError(null);
    try {
      setFacts(await api<Facts>(`/cases/${id}/facts`, { method: "PATCH",
        body: { base_version: facts.version, fields: [{ name, value: value.trim() || null }] } }));
      setEditing(null);
      setItems(await api<Items>(`/cases/${id}/line-items`));
    } catch (e) { await reloadAfter(e); }
    setBusy(false);
  }

  async function saveRows() {
    if (!rows || !items) return;
    const errs: Record<string, string> = {};
    const out = rows.map((r) => {
      const paise = parseRupeesToPaise(r.amount);
      if (!r.description.trim()) errs[r.key] = t("details.needDescription");
      else if (paise === null) errs[r.key] = t("details.invalidAmount");
      const unchanged = r.source && r.source.description === r.description.trim()
        && r.source.deducted_paise === paise && (r.source.clause_cited_verbatim ?? "") === r.clause.trim();
      return { description: r.description.trim(), deducted_paise: paise ?? 0,
        clause_cited_verbatim: r.clause.trim() || null, reason_verbatim: r.source?.reason_verbatim ?? null,
        user_entered: unchanged ? r.source!.user_entered : true };
    });
    setRowErrors(errs);
    if (Object.keys(errs).length) return;
    setBusy(true);
    setError(null);
    try {
      setItems(await api<Items>(`/cases/${id}/line-items`, { method: "PUT",
        body: { base_version: items.version, items: out } }));
      setFacts(await api<Facts>(`/cases/${id}/facts`));
      setRows(null);
    } catch (e) { await reloadAfter(e); }
    setBusy(false);
  }

  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      if (!facts!.confirmed) await api(`/cases/${id}/facts/confirm`, { body: { base_version: facts!.version } });
      const li = await api<Items>(`/cases/${id}/line-items`);
      if (!li.confirmed) await api(`/cases/${id}/line-items/confirm`, { body: { base_version: li.version } });
      await load();
    } catch (e) { setError(e); await load().catch(() => undefined); }
    setBusy(false);
  }

  if (!me) return gate;
  if (!facts || !items) return <div className="page"><ProblemNote error={error} />{!error && t("common.loading")}</div>;
  const missing = error instanceof ApiError && error.problem.code === "required_fields_missing";
  const missingNames = new Set(missing ? (error as ApiError).problem.errors?.map((x) => x.field) : []);
  const sorted = [...facts.fields].sort((x, y) =>
    Number(y.confidence_flag === "please_check") - Number(x.confidence_flag === "please_check"));
  const shown = (f: Field) => f.name === "decision_type" && f.value ? t(`details.decisionTypes.${f.value}`) : f.display;
  const allConfirmed = facts.confirmed && items.confirmed;
  const hint = (name: string) => name.endsWith("_paise") ? t("details.amountHint")
    : DATE_FIELDS.has(name) ? t("details.dateHint") : null;
  const startEdit = (f: Field) => {
    setEditing(f.name);
    setDraft(f.name.endsWith("_paise") ? (f.display ?? "").replace("₹", "") : f.name === "decision_type"
      ? (f.value ?? "") : (f.display ?? ""));
  };

  return (
    <div className="page">
      <CaseSteps caseId={id} current="details" />
      <PageTitle>{t("details.title")}</PageTitle>
      <p>{t("details.intro")}</p>
      {facts.extraction === "running" && <Callout tone="info">{t("details.extracting")}</Callout>}
      {facts.extraction === "failed" && <Callout tone="info">{t("details.extractFailed")}</Callout>}
      {sorted.map((f) => (
        <div className="card" key={f.name}
             style={f.confidence_flag === "please_check" || missingNames.has(f.name)
               ? { borderColor: "var(--color-warning-border)" } : undefined}>
          <div className="ledger-row">
            <div style={{ flex: 1 }}>
              <div className="muted">{t(`details.fields.${f.name}`)}{f.required ? ` · ${t("details.required")}` : ""}</div>
              {editing === f.name ? (
                f.name === "decision_type" ? (
                  <fieldset style={{ border: 0, padding: 0 }}>
                    <legend className="visually-hidden">{t(`details.fields.${f.name}`)}</legend>
                    {DECISIONS.map((d) => (
                      <label key={d} className="check">
                        <input type="radio" name="decision_type" value={d} checked={draft === d}
                               onChange={() => setDraft(d)} />
                        <span>{t(`details.decisionTypes.${d}`)}</span>
                      </label>
                    ))}
                  </fieldset>
                ) : (
                  <>
                    <input className="input" aria-label={t(`details.fields.${f.name}`)} value={draft} autoFocus
                           inputMode={f.name.endsWith("_paise") ? "decimal" : undefined}
                           onChange={(e) => setDraft(e.target.value)} />
                    {hint(f.name) && <span className="muted">{hint(f.name)}</span>}
                  </>
                )
              ) : (
                <div className={f.name.endsWith("_paise") ? "amount" : undefined}>{shown(f) ?? t("details.notFound")}</div>
              )}
              {f.value !== null && <ProvenanceTag kind={f.provenance} />}
              {f.confidence_flag === "please_check" && <span className="pill pill-warning">⚑ {t("details.needsCheck")}</span>}
            </div>
            <div>
              {editing === f.name ? (
                <>
                  <button className="btn btn-primary" disabled={busy} onClick={() => save(f.name, draft)}>
                    {t("details.save")}
                  </button>{" "}
                  <button className="btn btn-ghost" onClick={() => setEditing(null)}>{t("details.cancel")}</button>
                </>
              ) : (
                <button className="btn btn-ghost" onClick={() => startEdit(f)}
                        aria-label={`${t("details.edit")}: ${t(`details.fields.${f.name}`)}`}>
                  {t("details.edit")}
                </button>
              )}
            </div>
          </div>
        </div>
      ))}

      <h2>{t("details.deductions")}</h2>
      <p className="muted">{t("details.deductionsIntro")}</p>
      {rows ? (
        <div className="card">
          {rows.map((r, n) => (
            <fieldset key={r.key} style={{ border: 0, padding: 0, marginBottom: 16 }}>
              <legend className="muted">{n + 1}.</legend>
              <div className="field">
                <label htmlFor={`d-${r.key}`}>{t("details.deductionDescription")}</label>
                <input id={`d-${r.key}`} className="input" value={r.description} maxLength={500}
                       onChange={(e) => setRows(rows.map((x) => x.key === r.key ? { ...x, description: e.target.value } : x))} />
              </div>
              <div className="field">
                <label htmlFor={`a-${r.key}`}>{t("details.deductionAmount")}</label>
                <input id={`a-${r.key}`} className="input" inputMode="decimal" value={r.amount}
                       onChange={(e) => setRows(rows.map((x) => x.key === r.key ? { ...x, amount: e.target.value } : x))} />
              </div>
              <div className="field">
                <label htmlFor={`c-${r.key}`}>{t("details.deductionClause")}</label>
                <input id={`c-${r.key}`} className="input" value={r.clause} maxLength={200}
                       onChange={(e) => setRows(rows.map((x) => x.key === r.key ? { ...x, clause: e.target.value } : x))} />
              </div>
              {rowErrors[r.key] && <span className="field-error">{rowErrors[r.key]}</span>}
              <button type="button" className="btn btn-ghost" onClick={() => setRows(rows.filter((x) => x.key !== r.key))}>
                {t("details.remove")}
              </button>
            </fieldset>
          ))}
          <button type="button" className="btn btn-secondary"
                  onClick={() => setRows([...rows, { key: `new-${Date.now()}`, description: "", amount: "", clause: "" }])}>
            {t("details.addDeduction")}
          </button>{" "}
          <button type="button" className="btn btn-primary" disabled={busy} onClick={saveRows}>{t("details.saveDeductions")}</button>{" "}
          <button type="button" className="btn btn-ghost" onClick={() => { setRows(null); setRowErrors({}); }}>
            {t("details.cancel")}
          </button>
        </div>
      ) : (
        <>
          {items.items.length === 0 && <p>{t("details.noDeductions")}</p>}
          {items.items.map((i) => (
            <div className="card ledger-row" key={i.id}>
              <div>
                <strong>{i.description}</strong>
                <div className="muted">{t("details.clauseCited")}: {i.clause_cited_verbatim ?? t("details.noClause")}</div>
                {i.reason_verbatim && <div className="quote">{i.reason_verbatim}</div>}
                <ProvenanceTag kind={i.user_entered ? "user" : "document"} />
              </div>
              <div className="amount">{formatInr(i.deducted_paise)}</div>
            </div>
          ))}
          {items.items.length > 0 && (
            <Callout tone={items.totals.matches_disallowed ? "success" : "warning"}>
              {formatInr(items.totals.deducted_paise)} · {items.totals.matches_disallowed ? t("details.matches") : t("details.mismatch")}
            </Callout>
          )}
          <button type="button" className="btn btn-secondary" onClick={() => setRows(toRows(items.items))}>
            {t("details.editDeductions")}
          </button>
        </>
      )}

      {missing && <Callout tone="error">{t("details.missing")}</Callout>}
      {!missing && <ProblemNote error={error} />}
      <div className="action-bar">
        {allConfirmed ? (
          <Link className="btn btn-primary btn-block" href={href(`/cases/${id}/findings`)}>{t("common.continue")} →</Link>
        ) : (
          <button className="btn btn-primary btn-block" onClick={confirm}
                  disabled={busy || facts.extraction === "running" || rows !== null}>{t("details.confirm")}</button>
        )}
      </div>
      <Disclaimer />
    </div>
  );
}
