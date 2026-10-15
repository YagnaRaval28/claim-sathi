"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Callout, PageTitle, ProblemNote } from "@/components/ui";
import { api } from "@/lib/api";
import { LANGS, useI18n } from "@/lib/i18n";
import { useRequireUser } from "@/lib/use-session";

const FULL = { en: "English", gu: "ગુજરાતી", hi: "हिन्दी" } as const;

export default function Consent() {
  const { t, href, lang } = useI18n();
  const router = useRouter();
  const me = useRequireUser({ needConsent: false });
  const [version, setVersion] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [reminders, setReminders] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<{ version: string }>("/consent/notice").then((n) => setVersion(n.version)).catch(setError);
  }, []);

  async function agree() {
    if (!processing || !version) return;
    setBusy(true);
    try {
      await api("/me", { method: "PATCH", body: { display_language: lang } });
      await api("/consents", { body: { version, purposes: reminders ? ["processing", "reminders"] : ["processing"] } });
      router.replace(href("/cases"));
    } catch (e) {
      setError(e);
      setBusy(false);
    }
  }

  if (!me) return <div className="page">{t("common.loading")}</div>;
  return (
    <div className="page reading">
      <nav aria-label={t("language.title")} style={{ marginBottom: 16 }}>
        <span className="muted">{t("language.title")}: </span>
        {LANGS.map((l) => (
          <Link key={l} href={`/${l}/welcome/consent`} lang={l} aria-current={l === lang}
                style={{ marginRight: 12, fontWeight: l === lang ? 700 : 400 }}>{FULL[l]}</Link>
        ))}
      </nav>
      <PageTitle>{t("consent.title")}</PageTitle>
      <Callout tone="warning">{t("consent.draft")}</Callout>
      {(["what", "why", "ai", "keep"] as const).map((k) => (
        <section key={k}>
          <h3>{t(`consent.${k}Title`)}</h3>
          <p>{t(`consent.${k}Body`)}</p>
        </section>
      ))}
      <label className="check">
        <input type="checkbox" checked={processing} onChange={(e) => setProcessing(e.target.checked)} />
        <span><strong>{t("consent.processing")}</strong><br /><span className="muted">{t("consent.processingRequired")}</span></span>
      </label>
      <label className="check">
        <input type="checkbox" checked={reminders} onChange={(e) => setReminders(e.target.checked)} />
        <span>{t("consent.reminders")}</span>
      </label>
      <ProblemNote error={error} />
      <div className="action-bar">
        <button className="btn btn-primary btn-block" onClick={agree} aria-disabled={!processing || busy}
                disabled={busy}>{t("consent.agree")}</button>
        {!processing && <p className="muted">{t("consent.processingRequired")}</p>}
        <Link href={href("")} className="btn btn-ghost btn-block">{t("consent.notNow")}</Link>
      </div>
    </div>
  );
}
