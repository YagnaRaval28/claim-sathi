"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { AuditBadge, Callout, CaseSteps, Disclaimer, PageTitle, ProblemNote, ProvenanceTag } from "@/components/ui";
import { api, ApiError, newKey } from "@/lib/api";
import { formatInr } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useRequireUser } from "@/lib/use-session";

type Citation = { id: string; chunk_id: string; quote: string; verified: boolean; source_title: string;
  clause_ref: string | null; version: string; synthetic: boolean };
type Point = { id: string; statement: string; provenance: "rule" | "ai"; target_id: string; citations: Citation[] };
type Analysis = {
  id: string; status: string; mode: string; stale: boolean;
  summary: { claimed_paise: number | null; paid_paise: number | null };
  wording: { title: string; version: string; synthetic: boolean } | null;
  line_items: { id: string; description: string; deducted_paise: number; audit_status: string;
    clause_cited_verbatim: string | null; counter_point_ids: string[] }[];
  counter_points: Point[]; dropped_count: number;
};
type Chunk = { text: string; clause_ref: string | null; source: { title: string; version: string; synthetic: boolean } };
type Progress = { jobs: { kind: string; steps: { key: string; status: string }[] }[] };

function SourceSheet({ caseId, citation, onClose }: { caseId: string; citation: Citation; onClose: () => void }) {
  const { t } = useI18n();
  const [chunk, setChunk] = useState<Chunk | null>(null);
  const ref = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    api<Chunk>(`/cases/${caseId}/sources/chunks/${citation.chunk_id}`).then(setChunk).catch(() => setChunk(null));
    ref.current?.focus();
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [caseId, citation.chunk_id, onClose]);
  const parts = chunk ? chunk.text.split(citation.quote) : [];
  return (
    <>
      <div className="sheet-backdrop" onClick={onClose} />
      <aside className="sheet" role="dialog" aria-modal="true" aria-labelledby="src-title">
        <h2 id="src-title" ref={ref} tabIndex={-1} style={{ marginTop: 0 }}>{t("findings.sourceTitle")}</h2>
        {chunk ? (
          <>
            <p><strong>{chunk.source.title}</strong> · {chunk.clause_ref} · v{chunk.source.version}</p>
            {chunk.source.synthetic && <Callout tone="warning">{t("findings.synthetic")}</Callout>}
            <p lang="en" className="quote">
              {parts[0]}<mark className="highlight">{citation.quote}</mark>{parts.slice(1).join(citation.quote)}
            </p>
            <ProvenanceTag kind="verified" />
          </>
        ) : <p>{t("common.loading")}</p>}
        <p><button className="btn btn-secondary" onClick={onClose}>{t("findings.close")}</button></p>
      </aside>
    </>
  );
}

export default function Findings() {
  const { t, href } = useI18n();
  const { id } = useParams<{ id: string }>();
  const me = useRequireUser();
  const [a, setA] = useState<Analysis | null>(null);
  const [none, setNone] = useState(false);
  const [running, setRunning] = useState(false);
  const [steps, setSteps] = useState<{ key: string; status: string }[]>([]);
  const [open, setOpen] = useState<Citation | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    try {
      const r = await api<Analysis>(`/cases/${id}/analyses/latest`);
      setA(r);
      setNone(false);
      return r;
    } catch (e) {
      if (e instanceof ApiError && e.problem.status === 404) setNone(true);
      else setError(e);
      return null;
    }
  }, [id]);
  useEffect(() => {
    if (!me) return;
    let alive = true;
    api<Analysis>(`/cases/${id}/analyses/latest`)
      .then((r) => { if (alive) setA(r); })
      .catch((e) => {
        if (!alive) return;
        if (e instanceof ApiError && e.problem.status === 404) setNone(true);
        else setError(e);
      });
    return () => { alive = false; };
  }, [me, id]);

  async function run(k: string) {
    setRunning(true);
    setError(null);
    try {
      await api(`/cases/${id}/analyses`, { body: {}, idempotencyKey: k });
      for (let i = 0; i < 40; i++) {
        const p = await api<Progress>(`/cases/${id}/progress`);
        const job = p.jobs.filter((j) => j.kind === "analysis").at(-1);
        if (job) setSteps(job.steps);
        const r = await load();
        if (r && r.status !== "queued" && r.status !== "running") break;
        await new Promise((res) => setTimeout(res, 1500));
      }
    } catch (e) { setError(e); }
    setRunning(false);
  }

  const points = new Map((a?.counter_points ?? []).map((p) => [p.id, p]));
  const noClause = a?.line_items.filter((l) => l.audit_status === "NO_CLAUSE_CITED") ?? [];

  return (
    <div className="page">
      <CaseSteps caseId={id} current="findings" />
      <PageTitle>{t("findings.title")}</PageTitle>
      <ProblemNote error={error} />
      {running && (
        <div className="card" aria-live="polite">
          <p>{t("findings.running")}</p>
          <ul>{steps.map((s) => <li key={s.key}>{s.status === "done" ? "✓" : "…"} {t(`findings.steps.${s.key}`)}</li>)}</ul>
        </div>
      )}
      {none && !running && <button className="btn btn-primary" onClick={() => run(newKey())}>{t("findings.run")}</button>}
      {a && (
        <>
          {a.stale && (
            <Callout tone="warning">{t("findings.stale")}{" "}
              <button className="btn btn-secondary" onClick={() => run(newKey())}>{t("findings.update")}</button>
            </Callout>
          )}
          {a.mode === "limited" && <Callout tone="info">{t("findings.limited")}</Callout>}
          <div className="card">
            {a.summary.paid_paise !== null && a.summary.claimed_paise !== null && (
              <p style={{ fontSize: 18 }}>{t("findings.summary", { paid: formatInr(a.summary.paid_paise),
                claimed: formatInr(a.summary.claimed_paise) })}</p>
            )}
            {noClause.length > 0 && (
              <p>{t("findings.noClauseSummary", { count: noClause.length,
                amount: formatInr(noClause.reduce((s, l) => s + l.deducted_paise, 0)) })}</p>
            )}
            <ProvenanceTag kind="rule" /> <ProvenanceTag kind="document" />
            {a.wording && (
              <p className="muted">{t("findings.wording", { title: a.wording.title, version: a.wording.version })}
                {a.wording.synthetic && <> · <strong>{t("findings.synthetic")}</strong></>}</p>
            )}
          </div>
          {a.line_items.map((l) => (
            <div className="card" key={l.id}>
              <div className="ledger-row">
                <strong>{l.description}</strong>
                <span className="amount">{formatInr(l.deducted_paise)}</span>
              </div>
              <AuditBadge status={l.audit_status} />
              {l.audit_status === "CANNOT_ASSESS" && <p className="muted">{t("findings.cannotAssessHelp")}</p>}
              {l.counter_point_ids.map((pid) => points.get(pid)).filter(Boolean).map((p) => (
                <div key={p!.id} style={{ marginTop: 12 }}>
                  <p>{p!.statement} <ProvenanceTag kind={p!.provenance} /></p>
                  {p!.citations.map((c, i) => (
                    <p key={c.id} className="quote" lang="en">
                      “{c.quote}”
                      <button className="cite-tab" onClick={() => setOpen(c)}
                              aria-label={`${t("findings.sourceTitle")} ${i + 1}: ${c.source_title}, ${c.clause_ref ?? ""}`}>
                        {i + 1}
                      </button>{" "}
                      <ProvenanceTag kind="verified" />
                    </p>
                  ))}
                </div>
              ))}
            </div>
          ))}
          {a.dropped_count > 0 && <p className="muted">{t("findings.dropped")}</p>}
          <div className="action-bar">
            {a.stale ? (
              <button className="btn btn-primary btn-block" disabled aria-disabled="true">{t("findings.writeLetter")}</button>
            ) : (
              <Link className="btn btn-primary btn-block" href={href(`/cases/${id}/letter`)}>{t("findings.writeLetter")} →</Link>
            )}
          </div>
        </>
      )}
      {open && <SourceSheet caseId={id} citation={open} onClose={() => setOpen(null)} />}
      <Disclaimer />
    </div>
  );
}
