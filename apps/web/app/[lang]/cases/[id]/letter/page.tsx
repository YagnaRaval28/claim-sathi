"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Callout, CaseSteps, Disclaimer, PageTitle, ProblemNote } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { useRequireUser } from "@/lib/use-session";

type Block = { type: string; text?: string; items?: string[]; footnote?: number };
type Letter = { id: string; version: number; reviewed_version: number | null; stale: boolean;
  doc: { blocks: Block[]; footnotes: { n: number; source_title: string; clause_ref: string | null; version: string;
    synthetic: boolean }[]; disclaimer: string } };

export default function LetterPage() {
  const { t, href } = useI18n();
  const { id } = useParams<{ id: string }>();
  const { me, gate } = useRequireUser();
  const [letter, setLetter] = useState<Letter | null>(null);
  const [read, setRead] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (!me) return;
    // One letter per analysis: the idempotency key replays the same letter on revisit.
    api<{ id: string }>(`/cases/${id}/analyses/latest`)
      .then((a) => api<Letter>(`/cases/${id}/letters`, { body: {}, idempotencyKey: `letter-${a.id}` }))
      .then(setLetter)
      .catch(setError);
  }, [me, id]);

  async function download() {
    if (!letter || !read) return;
    setBusy(true);
    setError(null);
    try {
      if (letter.reviewed_version !== letter.version) {
        const reviewed = await api<Letter>(`/letters/${letter.id}/review`, { body: { version: letter.version } });
        setLetter(reviewed);
      }
      const exp = await api<{ download_path: string }>(`/letters/${letter.id}/exports`, { body: { format: "pdf" } });
      window.location.assign(exp.download_path);
    } catch (e) { setError(e); }
    setBusy(false);
  }

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
          <article className="paper" lang="en">
            {letter.doc.blocks.map((b, i) =>
              b.type === "list" ? (
                <ul key={i} style={{ listStyle: "none", paddingLeft: 16 }}>{b.items!.map((x) => <li key={x}>{x}</li>)}</ul>
              ) : b.type === "quote" ? (
                <blockquote key={i} className="quote">{b.text}<sup>[{b.footnote}]</sup></blockquote>
              ) : (
                <p key={i} style={b.type === "subject" ? { fontWeight: 600 } : undefined}>{b.text}</p>
              ))}
            <hr />
            {letter.doc.footnotes.map((n) => (
              <p key={n.n} style={{ fontSize: 14 }}>[{n.n}] {n.source_title}, {n.clause_ref}, v{n.version}
                {n.synthetic && ` ${t("letter.syntheticSource")}`}</p>
            ))}
            <p className="muted">{letter.doc.disclaimer}</p>
          </article>
          {!stale && (
            <div className="action-bar">
              <label className="check">
                <input type="checkbox" checked={read} onChange={(e) => setRead(e.target.checked)} />
                <span>{t("letter.read")}</span>
              </label>
              <button className="btn btn-primary btn-block" onClick={download} disabled={!read || busy}
                      aria-disabled={!read || busy} aria-busy={busy}>
                {busy ? t("letter.downloading") : t("letter.download")}
              </button>
              {!read && <p className="muted">{t("letter.readFirst")}</p>}
              <p className="muted">{t("letter.sendNote")}</p>
            </div>
          )}
        </>
      )}
      <Disclaimer />
    </div>
  );
}
