"use client";

import { useEffect, useRef, useState } from "react";
import { Callout, ProblemNote } from "@/components/ui";
import { api, newKey } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type ExportView = { id: string; status: "queued" | "ready" | "failed" | "expired"; download_path: string | null };

/** "Download my data" (FR-030): request a ZIP, poll its real status, then offer the 24-hour link. */
export function ExportPanel({ scope, caseId, label }: { scope: "case" | "account"; caseId?: string; label: string }) {
  const { t } = useI18n();
  const [exp, setExp] = useState<ExportView | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);

  async function poll(id: string) {
    const v = await api<ExportView>(`/exports/${id}`);
    setExp(v);
    if (v.status === "queued") timer.current = setTimeout(() => void poll(id), 1500);
  }

  async function start() {
    setBusy(true);
    setError(null);
    try {
      const r = await api<{ id: string }>("/exports", { body: { scope, case_id: caseId ?? null }, idempotencyKey: newKey() });
      await poll(r.id);
    } catch (e) { setError(e); }
    setBusy(false);
  }

  return (
    <div>
      {(!exp || exp.status === "expired" || exp.status === "failed") && (
        <button className="btn btn-secondary" disabled={busy} aria-busy={busy} onClick={start}>{label}</button>
      )}
      {exp?.status === "queued" && <p aria-live="polite">{t("caseSettings.preparing")}</p>}
      {exp?.status === "ready" && exp.download_path && (
        <Callout tone="success">{t("caseSettings.ready")}{" "}
          <a className="btn btn-primary" href={exp.download_path} download>{t("caseSettings.downloadLink")}</a>
        </Callout>
      )}
      {exp?.status === "failed" && <Callout tone="error">{t("caseSettings.exportFailed")}</Callout>}
      <ProblemNote error={error} />
    </div>
  );
}
