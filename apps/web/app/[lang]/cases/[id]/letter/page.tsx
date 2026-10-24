"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { LetterEditor } from "@/components/letter-editor";
import { LETTER_LANGUAGES, LetterActions, LetterPaper, type Letter, type LetterLanguage } from "@/components/letter-paper";
import { Callout, CaseSteps, Disclaimer, PageTitle, ProblemNote } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { useRequireUser } from "@/lib/use-session";

export default function LetterPage() {
  const { t, href, lang } = useI18n();
  const { id } = useParams<{ id: string }>();
  const { me, gate } = useRequireUser();
  const [letter, setLetter] = useState<Letter | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [editing, setEditing] = useState(false);
  // FR-024: the letter language is chosen per letter; it starts as the language the app is shown in.
  const [letterLang, setLetterLang] = useState<LetterLanguage>(lang);

  useEffect(() => {
    if (!me) return;
    // One letter per analysis and language: the idempotency key replays the same letter on revisit.
    api<{ id: string }>(`/cases/${id}/analyses/latest`)
      .then((a) => api<Letter>(`/cases/${id}/letters`, { body: { language: letterLang },
        idempotencyKey: `letter-${a.id}-${letterLang}` }))
      .then(setLetter)
      .catch(setError);
  }, [me, id, letterLang]);

  if (!me) return gate;
  const stale = letter?.stale || (error instanceof ApiError && error.problem.code === "case_stale");

  return (
    <div className="page">
      <CaseSteps caseId={id} current="letter" />
      <PageTitle>{t("letter.title")}</PageTitle>
      {stale ? (
        <Callout tone="warning">{t("letter.stale")}{" "}
          <Link className="btn btn-secondary" href={href(`/cases/${id}/findings`)}>{t("letter.goFindings")}</Link>
        </Callout>
      ) : <ProblemNote error={error} />}
      {!letter && !error && <p>{t("letter.creating")}</p>}
      {letter && (
        <>
          <Callout tone="info">{t("letter.basic")}</Callout>
          {!editing && (
            <div className="field">
              <label htmlFor="letter-lang">{t("letter.language")}</label>
              <select id="letter-lang" className="input" style={{ width: "auto" }} value={letterLang}
                      onChange={(e) => { setLetter(null); setError(null); setLetterLang(e.target.value as LetterLanguage); }}>
                {LETTER_LANGUAGES.map(([code, name]) => <option key={code} value={code} lang={code}>{name}</option>)}
              </select>
              {letterLang !== "en" && <p className="muted">{t("letter.languageHelp")}</p>}
            </div>
          )}
          {editing ? (
            <LetterEditor letter={letter} onSaved={setLetter} onDone={() => setEditing(false)} />
          ) : (
            <>
              <LetterPaper caseId={id} letter={letter} />
              {!stale && <button className="btn btn-secondary" onClick={() => setEditing(true)}>{t("letter.edit")}</button>}
            </>
          )}
          {!stale && !editing && (
            <div className="action-bar">
              <LetterActions letter={letter} onChange={setLetter} onError={setError} />
              <p className="muted">{t("letter.sendNote")}</p>
              <Link className="btn btn-secondary btn-block" href={href(`/cases/${id}/track`)}>{t("letter.afterSending")} →</Link>
            </div>
          )}
        </>
      )}
      <Disclaimer />
    </div>
  );
}
