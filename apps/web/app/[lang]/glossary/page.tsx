"use client";

import { PAGES_UPDATED } from "@/components/content-page";
import { PageTitle } from "@/components/ui";
import { useI18n } from "@/lib/i18n";

// PUB-06: insurance words in plain language. Each term has an anchor so explanations can link to it (FR-017).
export default function Glossary() {
  const { t, raw } = useI18n();
  const terms = (raw("glossary.terms") as [string, string, string][] | undefined) ?? [];
  return (
    <div className="page reading">
      <PageTitle>{t("glossary.title")}</PageTitle>
      <p className="muted">{t("pages.updated", { date: PAGES_UPDATED })}</p>
      <p>{t("glossary.intro")}</p>
      <dl>
        {terms.map(([id, term, meaning]) => (
          <div key={id} id={id} className="glossary-term">
            <dt>{term}</dt>
            <dd>{meaning}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
