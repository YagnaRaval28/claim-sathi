"use client";

import { useEffect, useState } from "react";
import { PAGES_UPDATED } from "@/components/content-page";
import { Callout, PageTitle } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDateDmy } from "@/lib/format";
import { useI18n } from "@/lib/i18n";

type Audit = { period: string; sample_size: number; correct: number; published_at: string };

// PUB-04 (FR-043): the figure comes only from the latest audit an admin published; it is never hard-coded.
// Before the first audit the page shows the empty state and no number.
export default function Accuracy() {
  const { t } = useI18n();
  const [audit, setAudit] = useState<Audit | null | undefined>(undefined);
  useEffect(() => {
    api<{ audit: Audit | null }>("/public/accuracy").then((r) => setAudit(r.audit)).catch(() => setAudit(null));
  }, []);
  return (
    <div className="page reading">
      <PageTitle>{t("pages.accuracy.title")}</PageTitle>
      <p className="muted">{t("pages.updated", { date: PAGES_UPDATED })}</p>
      {audit === undefined ? <p>{t("common.loading")}</p> : audit ? (
        <div className="card" aria-live="polite">
          <p style={{ fontSize: 20, margin: 0 }}>
            {t("pages.accuracy.result", { pct: Math.floor((1000 * audit.correct) / audit.sample_size) / 10,
              n: audit.sample_size, date: formatDateDmy(audit.published_at.slice(0, 10)) })}
          </p>
        </div>
      ) : <Callout tone="info">{t("pages.accuracy.empty")}</Callout>}
      <p>{t("pages.accuracy.method")}</p>
      {audit && <p>{t("pages.accuracy.audit")}</p>}
    </div>
  );
}
