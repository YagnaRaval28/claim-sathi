"use client";

import { ExternalLink, PAGES_UPDATED } from "@/components/content-page";
import { Callout, PageTitle } from "@/components/ui";
import { useI18n } from "@/lib/i18n";

// PUB-05 (FR-044). Details verified on policyholder.gov.in (IRDAI) and cioins.co.in (research source S50).
const CHANNELS = [
  { key: "insurer", url: null },
  { key: "bima", url: "https://bimabharosa.irdai.gov.in" },
  { key: "ombudsman", url: "https://cioins.co.in" },
] as const;

export default function FreeOfficialChannels() {
  const { t, raw } = useI18n();
  return (
    <div className="page reading">
      <PageTitle>{t("pages.free.title")}</PageTitle>
      <p className="muted">{t("pages.updated", { date: PAGES_UPDATED })}</p>
      <p>{t("pages.free.intro")}</p>
      <Callout tone="warning">{t("pages.free.warning")}</Callout>
      {CHANNELS.map(({ key, url }) => {
        const [heading, body] = (raw(`pages.free.${key}`) as [string, string] | undefined) ?? ["", ""];
        return (
          <section className="card" key={key}>
            <h2 style={{ marginTop: 0 }}>{heading}</h2>
            <p>{body}</p>
            {url && <p><ExternalLink href={url}>{url.replace("https://", "")}</ExternalLink></p>}
          </section>
        );
      })}
      <p className="muted">{t("pages.free.source")}</p>
    </div>
  );
}
