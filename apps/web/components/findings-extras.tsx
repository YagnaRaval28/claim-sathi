"use client";

import { useState } from "react";
import { ProblemNote } from "@/components/ui";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export const CATEGORIES = [
  "ped_waiting", "non_disclosure", "specific_waiting", "initial_waiting", "exclusion", "not_medically_necessary",
  "documents_or_intimation", "policy_not_in_force", "non_payable_items", "room_rent_proportionate",
  "reasonable_customary", "sub_limit", "copay_deductible", "other_unknown",
] as const;

export type ChecklistRow = { item_key: string; source: string; status: "pending" | "obtained" | "uploaded";
  document_id: string | null };

/**
 * FR-013 plain-language list: the user's choice of reason type. Saving re-runs the deterministic checks
 * (moratorium, documents, claims review committee) on the API; nothing is decided here.
 */
export function CategoryPicker({ caseId, reasonId, current, onRerun }: {
  caseId: string; reasonId: string; current: string | null; onRerun: () => void;
}) {
  const { t } = useI18n();
  const [open, setOpen] = useState(!current || current === "other_unknown");
  const [value, setValue] = useState<string>(current ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function save() {
    if (!value) return;
    setBusy(true);
    setError(null);
    try {
      await api(`/cases/${caseId}/reasons/${reasonId}`, { method: "PATCH", body: { category: value } });
      setOpen(false);
      onRerun();
    } catch (e) { setError(e); }
    setBusy(false);
  }

  if (!open) {
    return (
      <p className="muted">
        {current && t("categories.yours", { category: t(`categories.items.${current}`) })}{" "}
        <button type="button" className="btn btn-ghost" onClick={() => setOpen(true)}>{t("categories.change")}</button>
      </p>
    );
  }
  return (
    <fieldset className="field" style={{ border: 0, padding: 0 }}>
      <legend style={{ fontWeight: 600 }}>{t("categories.question")}</legend>
      <p className="muted">{t("categories.help")}</p>
      {CATEGORIES.map((c) => (
        <label key={c} className="check">
          <input type="radio" name={`cat-${reasonId}`} checked={value === c} onChange={() => setValue(c)} />
          <span>{t(`categories.items.${c}`)}</span>
        </label>
      ))}
      <ProblemNote error={error} />
      <button type="button" className="btn btn-secondary" disabled={!value || busy} aria-busy={busy} onClick={save}>
        {t("categories.save")}
      </button>
    </fieldset>
  );
}

/** FR-018: items come only from the API's evidence map; ticking one adds it to the letters' enclosures. */
export function EvidenceChecklist({ caseId, items, onChange }: {
  caseId: string; items: ChecklistRow[]; onChange: (row: ChecklistRow) => void;
}) {
  const { t } = useI18n();
  const [error, setError] = useState<unknown>(null);

  async function toggle(row: ChecklistRow, have: boolean) {
    setError(null);
    onChange({ ...row, status: have ? "obtained" : "pending" });  // optimistic; corrected from the response
    try {
      onChange(await api<ChecklistRow>(`/cases/${caseId}/checklist/${row.item_key}`, { method: "PATCH",
        body: { status: have ? "obtained" : "pending" } }));
    } catch (e) {
      onChange(row);
      setError(e);
    }
  }

  if (!items.length) return null;
  return (
    <section className="card" aria-labelledby="checklist-title">
      <h2 id="checklist-title" style={{ marginTop: 0 }}>{t("checklist.title")}</h2>
      <p className="muted">{t("checklist.intro")}</p>
      {items.map((row) => (
        <div key={row.item_key} className="check-row" style={{ marginBottom: 8 }}>
          {row.status === "uploaded" ? (
            <span className="pill pill-success">✓ {t("checklist.uploaded")}</span>
          ) : (
            <input type="checkbox" id={`ck-${row.item_key}`} checked={row.status === "obtained"}
                   onChange={(e) => toggle(row, e.target.checked)} aria-label={t(`checklist.items.${row.item_key}`)} />
          )}
          <label htmlFor={`ck-${row.item_key}`}>{t(`checklist.items.${row.item_key}`)}</label>
        </div>
      ))}
      <ProblemNote error={error} />
    </section>
  );
}
