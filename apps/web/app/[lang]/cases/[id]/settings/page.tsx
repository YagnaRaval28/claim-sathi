"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { TypedConfirmDialog } from "@/components/dialogs";
import { ExportPanel } from "@/components/export-panel";
import { CaseSteps, Disclaimer, PageTitle, ProblemNote } from "@/components/ui";
import { api } from "@/lib/api";
import type { CaseSummary } from "@/lib/cases";
import { formatDateDmy } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useRequireUser } from "@/lib/use-session";

type CaseWithRetention = CaseSummary & { retention: { delete_after: string | null; extended: boolean } };

// CASE-12: download case data, retention, danger zone. (Nickname edit and support access come with FR-042.)
export default function CaseSettings() {
  const { t, href } = useI18n();
  const router = useRouter();
  const { id } = useParams<{ id: string }>();
  const { me, gate } = useRequireUser();
  const [c, setC] = useState<CaseWithRetention | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [confirming, setConfirming] = useState(false);

  const load = useCallback(() => api<CaseWithRetention>(`/cases/${id}`).then(setC).catch(setError), [id]);
  useEffect(() => { if (me) void load(); }, [me, load]);

  async function extend() {
    setError(null);
    try {
      setC(await api<CaseWithRetention>(`/cases/${id}/retention/extend`, { body: {} }));
    } catch (e) { setError(e); }
  }

  if (!me) return gate;
  if (!c) return <div className="page"><ProblemNote error={error} />{!error && t("common.loading")}</div>;
  const deleteAfter = c.retention.delete_after;

  return (
    <div className="page">
      <CaseSteps caseId={id} current="track" />
      <PageTitle>{t("caseSettings.title")}</PageTitle>
      <ProblemNote error={error} />

      <section className="card">
        <h2 style={{ marginTop: 0 }}>{t("caseSettings.download")}</h2>
        <ExportPanel scope="case" caseId={id} label={t("caseSettings.download")} />
      </section>

      <section className="card">
        <h2 style={{ marginTop: 0 }}>{t("caseSettings.retention")}</h2>
        {c.status === "closed" && deleteAfter ? (
          <>
            <p>{t("caseSettings.retentionOn", { date: formatDateDmy(deleteAfter.slice(0, 10)) })}</p>
            {c.retention.extended ? <p className="muted">{t("caseSettings.retentionExtended")}</p>
              : <button className="btn btn-secondary" onClick={extend}>{t("caseSettings.extend")}</button>}
          </>
        ) : <p>{t("caseSettings.retentionOpen")}</p>}
      </section>

      <section className="danger-zone">
        <h2 style={{ marginTop: 0 }}>{t("caseSettings.danger")}</h2>
        <button className="btn btn-danger" onClick={() => setConfirming(true)}>{t("caseSettings.deleteCase")}</button>
      </section>
      {confirming && (
        <TypedConfirmDialog
          title={t("caseSettings.deleteCaseTitle")}
          body={t("caseSettings.deleteCaseBody")}
          confirmLabel={t("caseSettings.deleteCase")}
          challengePath={`/cases/${id}/delete-challenge`}
          onClose={() => setConfirming(false)}
          run={async (code, challenge) => {
            await api(`/cases/${id}`, { method: "DELETE", body: { confirm_code: code },
              headers: { "X-Confirm-Challenge": challenge } });
            router.replace(href("/cases"));
          }}
        />
      )}
      <Disclaimer />
    </div>
  );
}
