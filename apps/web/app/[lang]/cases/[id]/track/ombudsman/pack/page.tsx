"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { LetterActions, LetterPaper, type Letter } from "@/components/letter-paper";
import { Callout, CaseSteps, Disclaimer, PageTitle, ProblemNote } from "@/components/ui";
import { api, newKey } from "@/lib/api";
import { todayIst } from "@/lib/escalation";
import { useI18n } from "@/lib/i18n";
import { useRequireUser } from "@/lib/use-session";

type Pack = {
  letter: Letter | null;
  signatory: { name: string; is_helper: boolean };
  enclosures: { key: string; present: boolean }[];
  filing: { portal_url: string; free: boolean };
};

// CASE-10 (FR-026): signatory notice, complaint letter, enclosures, how to file. Generated only by the API,
// which re-checks the Ombudsman rules every time.
export default function OmbudsmanPack() {
  const { t, href } = useI18n();
  const { id } = useParams<{ id: string }>();
  const { me, gate } = useRequireUser();
  const [pack, setPack] = useState<Pack | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [filedOn, setFiledOn] = useState(todayIst());
  const [reference, setReference] = useState("");
  const [filed, setFiled] = useState(false);
  const key = useRef<string | null>(null);

  useEffect(() => { if (me) api<Pack>(`/cases/${id}/packs/ombudsman`).then(setPack).catch(setError); }, [me, id]);

  async function logFiled(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api(`/cases/${id}/events`, { idempotencyKey: (key.current ??= newKey()),
        body: { kind: "s3_filed", event_date: filedOn, metadata: reference.trim() ? { reference: reference.trim() } : {} } });
      setFiled(true);
    } catch (err) { key.current = null; setError(err); }
  }

  if (!me) return gate;
  if (!pack) return <div className="page"><ProblemNote error={error} />{!error && t("common.loading")}</div>;

  return (
    <div className="page">
      <CaseSteps caseId={id} current="track" />
      <PageTitle>{t("pack.title")}</PageTitle>
      <ProblemNote error={error} />
      <Callout tone="info">
        {pack.signatory.is_helper ? t("ombudsman.messages.complainant_must_sign", { name: pack.signatory.name })
          : t("ombudsman.messages.you_sign")}
      </Callout>
      {!pack.letter ? (
        <p>{t("pack.notYet")} <Link href={href(`/cases/${id}/track/ombudsman`)}>{t("pack.checks")}</Link></p>
      ) : (
        <>
          <h2>{t("pack.letter")}</h2>
          <LetterPaper caseId={id} letter={pack.letter} />
          <div className="action-bar">
            <LetterActions letter={pack.letter} onError={setError}
                           onChange={(l) => setPack((p) => (p ? { ...p, letter: l } : p))} />
          </div>

          <h2>{t("pack.enclosures")}</h2>
          <ul>
            {pack.enclosures.map((e) => (
              <li key={e.key}>
                <span aria-hidden="true">{e.present ? "✓" : "!"}</span> {t(`pack.enclosure.${e.key}`)}
                {!e.present && <> · <Link href={href(`/cases/${id}/documents`)}>{t("pack.addDocument")}</Link></>}
              </li>
            ))}
          </ul>

          <h2>{t("pack.howToFile")}</h2>
          <Callout tone="success">{t("pack.free")}</Callout>
          <h3>{t("pack.online")}</h3>
          <p>{t("pack.onlineBody")} <a href={pack.filing.portal_url} target="_blank" rel="noopener noreferrer">
            {pack.filing.portal_url.replace("https://", "")}</a></p>
          <h3>{t("pack.emailPost")}</h3>
          <p>{t("pack.emailPostBody")}</p>

          <h2>{t("pack.logFiledTitle")}</h2>
          {filed ? (
            <Callout tone="success">{t("pack.filedDone")}{" "}
              <Link href={href(`/cases/${id}/track`)}>{t("steps.track")} →</Link>
            </Callout>
          ) : (
            <form className="card" onSubmit={logFiled}>
              <div className="field">
                <label htmlFor="filed-on">{t("track.sheet.date")}</label>
                <input id="filed-on" className="input" type="date" required max={todayIst()} value={filedOn}
                       onChange={(e) => setFiledOn(e.target.value)} />
              </div>
              <div className="field">
                <label htmlFor="filed-ref">{t("track.sheet.reference")}</label>
                <input id="filed-ref" className="input" maxLength={40} value={reference}
                       onChange={(e) => setReference(e.target.value)} />
              </div>
              <button className="btn btn-primary">{t("ombudsman.logFiled")}</button>
            </form>
          )}
        </>
      )}
      <Disclaimer />
    </div>
  );
}
