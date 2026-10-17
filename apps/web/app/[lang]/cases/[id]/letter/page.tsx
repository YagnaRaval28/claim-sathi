"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { LetterEditor } from "@/components/letter-editor";
import { LetterActions, LetterPaper, type Letter } from "@/components/letter-paper";
import { Callout, CaseSteps, Disclaimer, PageTitle, ProblemNote } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { useRequireUser } from "@/lib/use-session";

export default function LetterPage() {
  const { t, href } = useI18n();
  const { id } = useParams<{ id: string }>();
  const { me, gate } = useRequireUser();
  const [letter, setLetter] = useState<Letter | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    if (!me) return;
    // One letter per analysis: the idempotency key replays the same letter on revisit.
    api<{ id: string }>(`/cases/${id}/analyses/latest`)
      .then((a) => api<Letter>(`/cases/${id}/letters`, { body: {}, idempotencyKey: `letter-${a.id}` }))
      .then(setLetter)
      .catch(setError);
  }, [me, id]);

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
