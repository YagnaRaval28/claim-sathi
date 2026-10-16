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
type Target = { id: string; audit_status: string | null; clause_cited_verbatim: string | null; counter_point_ids: string[] };
type Analysis = {
  id: string; status: string; mode: string; stale: boolean;
  summary: { claimed_paise: number | null; paid_paise: number | null; decision_type: string | null };
  wording: { title: string; version: string; synthetic: boolean } | null;
  line_items: (Target & { description: string; deducted_paise: number })[];
  reasons: (Target & { text: string })[];
  counter_points: Point[]; dropped_count: number;
};
type Chunk = { text: string; clause_ref: string | null; source: { title: string; version: string; synthetic: boolean } };
type Progress = { jobs: { kind: string; ref_id: string; steps: { key: string; status: string }[] }[] };

const ACTIVE = ["queued", "running"];
const CHALLENGEABLE = ["NO_CLAUSE_CITED", "CLAUSE_NOT_FOUND"];

function SourceSheet({ caseId, citation, onClose }: { caseId: string; citation: Citation; onClose: () => void }) {
  const { t } = useI18n();
  const [chunk, setChunk] = useState<Chunk | null>(null);
  const [failed, setFailed] = useState(false);
  const ref = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    api<Chunk>(`/cases/${caseId}/sources/chunks/${citation.chunk_id}`).then(setChunk).catch(() => setFailed(true));
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
        ) : failed ? <Callout tone="error">{t("findings.sourceError")}</Callout> : <p>{t("common.loading")}</p>}
        <p><button className="btn btn-secondary" onClick={onClose}>{t("findings.close")}</button></p>
      </aside>
    </>
  );
}

function Points({ ids, points, onOpen }: { ids: string[]; points: Map<string, Point>; onOpen: (c: Citation) => void }) {
  const { t } = useI18n();
  return (
    <>
      {ids.map((pid) => points.get(pid)).filter((p): p is Point => !!p).map((p) => (
        <div key={p.id} style={{ marginTop: 12 }}>
          <p>{p.statement} <ProvenanceTag kind={p.provenance} /></p>
          {p.citations.map((c, i) => (
            <p key={c.id} className="quote" lang="en">
              “{c.quote}”
              <button className="cite-tab" onClick={() => onOpen(c)}
                      aria-label={`${t("findings.sourceTitle")} ${i + 1}: ${c.source_title}, ${c.clause_ref ?? ""}`}>
                {i + 1}
              </button>{" "}
              <ProvenanceTag kind="verified" />
            </p>
          ))}
        </div>
      ))}
    </>
  );
}

export default function Findings() {
  const { t, href } = useI18n();
  const { id } = useParams<{ id: string }>();
  const { me, gate } = useRequireUser();
  const [a, setA] = useState<Analysis | null>(null);
  const [none, setNone] = useState(false);
  const [steps, setSteps] = useState<{ key: string; status: string }[]>([]);
  const [open, setOpen] = useState<Citation | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [starting, setStarting] = useState(false);
  const closeSheet = useCallback(() => setOpen(null), []);

  const load = useCallback(async (): Promise<Analysis | null> => {
    try {
      const r = await api<Analysis>(`/cases/${id}/analyses/latest`);
      setA(r);
      setNone(false);
      if (ACTIVE.includes(r.status)) {
        const p = await api<Progress>(`/cases/${id}/progress`);
        setSteps(p.jobs.find((j) => j.ref_id === r.id)?.steps ?? []);
      }
      return r;
    } catch (e) {
      if (e instanceof ApiError && e.problem.status === 404) setNone(true);
      else setError(e);
      return null;
    }
  }, [id]);

  // Load, and keep following a run that is still in progress (also after a page reload).
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!me) return;
    let alive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = () => {
      void load().then((r) => {
        if (alive && r && ACTIVE.includes(r.status)) timer = setTimeout(poll, 1500);
      });
    };
    poll();
    return () => { alive = false; clearTimeout(timer); };
  }, [me, load, tick]);

  async function run() {
    setStarting(true);
    setError(null);
    try {
      await api(`/cases/${id}/analyses`, { body: {}, idempotencyKey: newKey() });
      setTick((n) => n + 1);
    } catch (e) { setError(e); }
    setStarting(false);
  }

  if (!me) return gate;
  const points = new Map((a?.counter_points ?? []).map((p) => [p.id, p]));
  const running = !!a && ACTIVE.includes(a.status);
  const done = a?.status === "succeeded";
  const noClause = a?.line_items.filter((l) => l.audit_status === "NO_CLAUSE_CITED") ?? [];
  const reasonsNoClause = a?.reasons.filter((r) => r.audit_status === "NO_CLAUSE_CITED") ?? [];
  const canWrite = done && !a!.stale && (a!.line_items.some((l) => CHALLENGEABLE.includes(l.audit_status ?? ""))
    || a!.reasons.some((r) => CHALLENGEABLE.includes(r.audit_status ?? "")));
  const rejected = a?.summary.decision_type === "repudiation";

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
      {none && <button className="btn btn-primary" disabled={starting} onClick={run}>{t("findings.run")}</button>}
      {a?.status === "failed" && (
        <Callout tone="error">{t("findings.failed")}{" "}
          <button className="btn btn-secondary" disabled={starting} onClick={run}>{t("findings.runAgain")}</button>
        </Callout>
      )}
      {a && done && (
        <>
          {a.stale && (
            <Callout tone="warning">{t("findings.stale")}{" "}
              <button className="btn btn-secondary" disabled={starting} onClick={run}>{t("findings.update")}</button>
            </Callout>
          )}
          {a.mode === "limited" && <Callout tone="info">{t("findings.limited")}</Callout>}
          <div className="card">
            {rejected && a.summary.claimed_paise !== null && (
              <p style={{ fontSize: 18 }}>{t("findings.rejectionSummary", { claimed: formatInr(a.summary.claimed_paise) })}</p>
            )}
            {!rejected && a.summary.paid_paise !== null && a.summary.claimed_paise !== null && (
              <p style={{ fontSize: 18 }}>{t("findings.summary", { paid: formatInr(a.summary.paid_paise),
                claimed: formatInr(a.summary.claimed_paise) })}</p>
            )}
            {noClause.length > 0 && (
              <p>{t("findings.noClauseSummary", { count: noClause.length,
                amount: formatInr(noClause.reduce((s, l) => s + l.deducted_paise, 0)) })}</p>
            )}
            {reasonsNoClause.length > 0 && <p>{t("findings.reasonNoClauseSummary", { count: reasonsNoClause.length })}</p>}
            <ProvenanceTag kind="rule" /> <ProvenanceTag kind="document" />
            {a.wording && (
              <p className="muted">{t("findings.wording", { title: a.wording.title, version: a.wording.version })}
                {a.wording.synthetic && <> · <strong>{t("findings.synthetic")}</strong></>}</p>
            )}
          </div>
          {a.reasons.length > 0 && <h2>{t("findings.reasons")}</h2>}
          {a.reasons.map((r) => (
            <div className="card" key={r.id}>
              <p className="quote">“{r.text}”</p>
              <AuditBadge status={r.audit_status ?? "PENDING"} />
              <Points ids={r.counter_point_ids} points={points} onOpen={setOpen} />
            </div>
          ))}
          {a.line_items.length > 0 && a.reasons.length > 0 && <h2>{t("details.deductions")}</h2>}
          {a.line_items.map((l) => (
            <div className="card" key={l.id}>
              <div className="ledger-row">
                <strong>{l.description}</strong>
                <span className="amount">{formatInr(l.deducted_paise)}</span>
              </div>
              <AuditBadge status={l.audit_status ?? "PENDING"} />
              {l.audit_status === "CANNOT_ASSESS" && <p className="muted">{t("findings.cannotAssessHelp")}</p>}
              <Points ids={l.counter_point_ids} points={points} onOpen={setOpen} />
            </div>
          ))}
          {a.dropped_count > 0 && <p className="muted">{t("findings.dropped")}</p>}
          <div className="action-bar">
            {canWrite ? (
              <Link className="btn btn-primary btn-block" href={href(`/cases/${id}/letter`)}>{t("findings.writeLetter")} →</Link>
            ) : (
              <>
                <button className="btn btn-primary btn-block" disabled aria-disabled="true">{t("findings.writeLetter")}</button>
                {!a.stale && <p className="muted">{t("findings.nothingToChallenge")}</p>}
              </>
            )}
          </div>
        </>
      )}
      {open && <SourceSheet caseId={id} citation={open} onClose={closeSheet} />}
      <Disclaimer />
    </div>
  );
}
