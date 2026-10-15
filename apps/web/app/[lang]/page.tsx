"use client";

import Link from "next/link";
import { Callout, Disclaimer } from "@/components/ui";
import { useI18n } from "@/lib/i18n";

export default function Home() {
  const { t, href } = useI18n();
  return (
    <div className="page reading">
      <h1>{t("home.title")}</h1>
      <p style={{ fontSize: 18 }}>{t("home.subtitle")}</p>
      <Link href={href("/sign-in")} className="btn btn-primary">
        {t("home.cta")} →
      </Link>
      <p className="muted">{t("home.free")}</p>
      <ol>
        <li>{t("home.point1")}</li>
        <li>{t("home.point2")}</li>
        <li>{t("home.point3")}</li>
      </ol>
      <Callout tone="info">{t("home.scope")}</Callout>
      <Callout tone="warning">{t("common.freeChannels")}</Callout>
      <Disclaimer />
    </div>
  );
}
