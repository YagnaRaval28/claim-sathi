"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Callout, CaseSteps, Disclaimer, PageTitle, ProblemNote } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { useRequireUser } from "@/lib/use-session";
import type { CaseSummary } from "@/lib/cases";

const TYPES = ["decision_letter", "settlement_breakup", "policy_wording", "other"] as const;
const READING = ["queued", "reading", "uploading", "scanning"];
const MAX_FILE_BYTES = 20 * 1024 * 1024; // FR-008 AC2: checked here before upload, and again by the API
const RETRY_DELAYS_MS = [1000, 3000, 8000]; // FR-009: up to 3 automatic retries when the connection drops

/** Upload with automatic retries on network loss only; a server answer (even an error) is never retried. */
async function uploadWithRetry(path: string, form: FormData, onRetry: () => void): Promise<void> {
  for (let attempt = 0; ; attempt++) {
    try {
      await api(path, { form });
      return;
    } catch (err) {
      // An earlier attempt may have arrived although its answer was lost: the file is already there.
      if (attempt > 0 && err instanceof ApiError && err.problem.code === "duplicate_file") return;
      if (err instanceof ApiError || attempt >= RETRY_DELAYS_MS.length) throw err;
      onRetry();
      await new Promise((r) => setTimeout(r, RETRY_DELAYS_MS[attempt]));
    }
  }
}

/** FR-008 AC3: the PDF password is sent once to open the file; it is never stored. */
function PasswordForm({ caseId, docId, onOpened }: { caseId: string; docId: string; onOpened: () => void }) {
  const { t } = useI18n();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const input = e.currentTarget.elements.namedItem("password") as HTMLInputElement;
    setBusy(true);
    setError(null);
    try {
      await api(`/cases/${caseId}/documents/${docId}/unlock`, { body: { password: input.value } });
      input.value = "";
      onOpened();
    } catch (err) { setError(err); }
    setBusy(false);
  }
  const map = { pdf_password_incorrect: t("documents.errors.pdf_password_incorrect") };
  return (
    <form onSubmit={submit} style={{ marginTop: 8 }}>
      <div className="field">
        <label htmlFor={`pw-${docId}`}>{t("documents.password.label")}</label>
        <p className="muted" id={`pw-help-${docId}`}>{t("documents.password.help")}</p>
        <input id={`pw-${docId}`} name="password" type="password" className="input" autoComplete="off" required
               maxLength={128} aria-describedby={`pw-help-${docId}`} />
      </div>
      <ProblemNote error={error} map={map} />
      <button className="btn btn-secondary" disabled={busy} aria-busy={busy}>{t("documents.password.submit")}</button>
    </form>
  );
}

export default function Documents() {
  const { t, href } = useI18n();
  const { id } = useParams<{ id: string }>();
  const { me, gate } = useRequireUser();
  const [c, setC] = useState<CaseSummary | null>(null);
  const [file, setFile] = useState<File | null>(null);
  // The "Add your policy wording" recovery (FR-019) opens this page with that type chosen.
  const [type, setType] = useState<string>(() => {
    const wanted = typeof window === "undefined" ? null : new URLSearchParams(window.location.search).get("type");
    return wanted && (TYPES as readonly string[]).includes(wanted) ? wanted : "decision_letter";
  });
  const [busy, setBusy] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [tooBig, setTooBig] = useState(false);
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

  function pick(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    const big = !!f && f.size > MAX_FILE_BYTES;
    setTooBig(big);
    setFile(big ? null : f);
  }

  async function upload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    const form = new FormData();
    form.append("file", file);
    form.append("type", type);
    try {
      await uploadWithRetry(`/cases/${id}/documents`, form, () => setRetrying(true));
      setFile(null);
      for (const input of document.querySelectorAll<HTMLInputElement>("form input[type=file]")) input.value = "";
      await load();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
      setRetrying(false);
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
          <input id="file" type="file" accept="application/pdf,image/jpeg,image/png" onChange={pick} />
          {/* FR-008: on a phone this opens the camera; the photo is read by OCR on our server (FR-010). */}
          <label className="btn btn-secondary" style={{ alignSelf: "flex-start" }}>
            {t("documents.takePhoto")}
            <input type="file" accept="image/*" capture="environment" className="visually-hidden" onChange={pick} />
          </label>
          {file && <p className="muted">{file.name}</p>}
          {tooBig && <p className="field-error" role="alert">{t("documents.errors.payload_too_large")}</p>}
        </div>
        <div className="field">
          <label htmlFor="type">{t("documents.type")}</label>
          <select id="type" className="input" value={type} onChange={(e) => setType(e.target.value)}>
            {TYPES.map((k) => <option key={k} value={k}>{t(`documents.types.${k}`)}</option>)}
          </select>
        </div>
        <p className="muted">{t("documents.limits")}</p>
        <ProblemNote error={error} map={errMap} />
        {retrying && <p className="muted" aria-live="polite">{t("documents.retrying")}</p>}
        <button className="btn btn-secondary" disabled={!file || busy} aria-busy={busy}>
          {busy ? t("documents.uploading") : t("documents.upload")}
        </button>
      </form>
      <ul aria-live="polite" style={{ listStyle: "none", padding: 0 }}>
        {c?.documents.map((d) => (
          <li key={d.id} className="card">
            <strong>{t(`documents.types.${d.type}`)}</strong> · {t(`documents.status.${d.status}`)}
            {d.status_reason && <p className="field-error">{t(`documents.errors.${d.status_reason}`)}</p>}
            {d.status_reason === "password_required" && <PasswordForm caseId={id} docId={d.id} onOpened={load} />}
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
