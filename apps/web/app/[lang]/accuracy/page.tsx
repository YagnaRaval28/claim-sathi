"use client";

import { PAGES_UPDATED } from "@/components/content-page";
import { Callout, PageTitle } from "@/components/ui";
import { useI18n } from "@/lib/i18n";

// PUB-04 (FR-043): the figure must come from a stored audit and is never hard-coded. No audit exists yet,
// so the page shows the empty state and no number.
export default function Accuracy() {
  const { t } = useI18n();
  return (
    <div className="page reading">
      <PageTitle>{t("pages.accuracy.title")}</PageTitle>
      <p className="muted">{t("pages.updated", { date: PAGES_UPDATED })}</p>
      <Callout tone="info">{t("pages.accuracy.empty")}</Callout>
      <p>{t("pages.accuracy.method")}</p>
    </div>
  );
}
