"use client";

import Link from "next/link";
import { Callout, PageTitle } from "@/components/ui";
import { useI18n } from "@/lib/i18n";

export const PAGES_UPDATED = "17/10/2026";

/** ReadingLayout page (design PUB-02/03/07-09): title, "last updated", optional DRAFT notice, sections. */
export function ContentPage({ page, draft = false }: { page: string; draft?: boolean }) {
  const { t, raw } = useI18n();
  const sections = (raw(`pages.${page}.sections`) as [string, string][] | undefined) ?? [];
  return (
    <div className="page reading">
      <PageTitle>{t(`pages.${page}.title`)}</PageTitle>
      <p className="muted">{t("pages.updated", { date: PAGES_UPDATED })}</p>
      {draft && <Callout tone="warning">{t("pages.draft")}</Callout>}
      {sections.map(([heading, body]) => (
        <section key={heading}>
          <h2>{heading}</h2>
          <p>{body}</p>
        </section>
      ))}
    </div>
  );
}

export function ExternalLink({ href, children }: { href: string; children: React.ReactNode }) {
  const { t } = useI18n();
  return (
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children} <span aria-hidden="true">↗</span><span className="visually-hidden"> ({t("pages.opensOfficial")})</span>
    </a>
  );
}

const LINKS = [
  ["how-it-works", "how"], ["what-we-dont-do", "dont"], ["free-official-channels", "free"], ["accuracy", "accuracy"],
  ["privacy", "privacy"], ["terms", "terms"], ["contact", "contact"],
] as const;

/** Site footer: on every page, so free official help is one tap away from every case screen (FR-044 AC1). */
export function Footer() {
  const { t, href } = useI18n();
  return (
    <footer className="page" style={{ borderTop: "1px solid var(--color-border)", paddingTop: "var(--space-4)" }}>
      <nav aria-label={t("common.appName")} style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-3)" }}>
        {LINKS.map(([path, key]) => (
          <Link key={path} href={href(`/${path}`)} style={key === "free" ? { fontWeight: 700 } : undefined}>
            {t(`footer.${key}`)}
          </Link>
        ))}
      </nav>
      <p className="disclaimer">ⓘ {t("common.disclaimer")}</p>
    </footer>
  );
}
