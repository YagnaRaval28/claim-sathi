"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Callout, CaseSteps, Disclaimer, PageTitle, ProblemNote } from "@/components/ui";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { useRequireUser } from "@/lib/use-session";
import type { CaseSummary } from "@/lib/cases";

const TYPES = ["decision_letter", "settlement_breakup", "policy_wording", "other"] as const;
const READING = ["queued", "reading", "uploading", "scanning"];

export default function Documents() {
  const { t, href } = useI18n();
  const { id } = useParams<{ id: string }>();
  const { me, gate } = useRequireUser();
  const [c, setC] = useState<CaseSummary | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [type, setType] = useState<string>("decision_letter");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(() => api<CaseSummary>(`/cases/${id}`).then(setC).catch(setError), [id]);
  useEffect(() => { if (me) void load(); }, [me, load]);

  // Poll real task state while files are read and details extracted (design §7.6: no fake progress).
  const reading = c?.documents.some((d) => READING.includes(d.status)) ?? false;
  const extracting = c?.extraction === "running";
  useEffect(() => {
    if (!reading && !extracting) return;
    const h = setInterval(() => void load(), 2000);
    return () => clearInterval(h);
  }, [reading, extracting, load]);

  async function upload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    const form = new FormData();
    form.append("file", file);
    form.append("type", type);
    try {
      await api(`/cases/${id}/documents`, { form });
      setFile(null);
      (document.getElementById("file") as HTMLInputElement).value = "";
      await load();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  if (!me) return gate;
  const errMap = Object.fromEntries(
    ["duplicate_file", "payload_too_large", "unsupported_media_type", "case_upload_limit", "storage_full"]
      .map((k) => [k, t(`documents.errors.${k}`)]));
  const letterReady = c?.documents.some((d) => d.type === "decision_letter" && d.status === "ready") ?? false;
  const canContinue = letterReady && !reading && !extracting;

  return (
    <div className="page">
      <CaseSteps caseId={id} current="documents" />
      <PageTitle>{t("documents.title")}</PageTitle>
      <p>{t("documents.intro")}</p>
      <form className="card" onSubmit={upload}>
        <div className="field">
          <label htmlFor="file">{t("documents.choose")}</label>
          <input id="file" type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        </div>
        <div className="field">
          <label htmlFor="type">{t("documents.type")}</label>
          <select id="type" className="input" value={type} onChange={(e) => setType(e.target.value)}>
            {TYPES.map((k) => <option key={k} value={k}>{t(`documents.types.${k}`)}</option>)}
          </select>
        </div>
        <p className="muted">{t("documents.limits")}</p>
        <ProblemNote error={error} map={errMap} />
        <button className="btn btn-secondary" disabled={!file || busy} aria-busy={busy}>
          {busy ? t("documents.uploading") : t("documents.upload")}
        </button>
      </form>
      <ul aria-live="polite" style={{ listStyle: "none", padding: 0 }}>
        {c?.documents.map((d) => (
          <li key={d.id} className="card">
            <strong>{t(`documents.types.${d.type}`)}</strong> · {t(`documents.status.${d.status}`)}
            {d.status_reason && <p className="field-error">{t(`documents.errors.${d.status_reason}`)}</p>}
          </li>
        ))}
      </ul>
      {letterReady && extracting && <p aria-live="polite">{t("documents.extracting")}</p>}
      {letterReady && c?.extraction === "failed" && <Callout tone="info">{t("documents.extractFailed")}</Callout>}
      <div className="action-bar">
        {canContinue ? (
          <Link className="btn btn-primary btn-block" href={href(`/cases/${id}/details`)}>{t("documents.continue")} →</Link>
        ) : (
          <>
            <button className="btn btn-primary btn-block" aria-disabled="true" disabled>{t("documents.continue")}</button>
            <p className="muted">{reading || extracting ? t("documents.waiting") : t("documents.needLetter")}</p>
          </>
        )}
      </div>
      <Disclaimer />
    </div>
  );
}
