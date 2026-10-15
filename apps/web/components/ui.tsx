"use client";

import Link from "next/link";
import { useEffect, useRef, type ReactNode } from "react";
import { ApiError } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export function Callout({ tone, children }: { tone: "info" | "warning" | "error" | "success"; children: ReactNode }) {
  return (
    <div className={`callout callout-${tone}`} role={tone === "error" ? "alert" : "status"}>
      {children}
    </div>
  );
}

/** Design §7.1: every fact/quote/AI sentence carries an icon-free text label (colour is never the only cue). */
export function ProvenanceTag({ kind }: { kind: "verified" | "document" | "user" | "rule" | "ai" }) {
  const { t } = useI18n();
  const cls = { verified: "pill-verified", document: "pill-document", user: "pill-document", rule: "pill-rule",
    ai: "pill-ai" }[kind];
  const mark = { verified: "✓", document: "▣", user: "✎", rule: "☰", ai: "✦" }[kind];
  return (
    <span className={`pill ${cls}`}>
      <span aria-hidden="true">{mark}</span> {t(`provenance.${kind}`)}
    </span>
  );
}

const AUDIT_STYLE: Record<string, [string, string]> = {
  NO_CLAUSE_CITED: ["pill-warning", "?"],
  CLAUSE_NOT_FOUND: ["pill-warning", "⌕"],
  CLAUSE_FOUND_QUESTIONABLE: ["pill-rule", "⚖"],
  CLAUSE_FOUND_APPEARS_VALID: ["pill-neutral", "○"],
  CANNOT_ASSESS: ["pill-dashed", "◌"],
};

export function AuditBadge({ status }: { status: string }) {
  const { t } = useI18n();
  const [cls, mark] = AUDIT_STYLE[status] ?? ["pill-neutral", "·"];
  return (
    <span className={`pill ${cls}`}>
      <span aria-hidden="true">{mark}</span> {t(`findings.statuses.${status}`)}
    </span>
  );
}

const STEPS = ["documents", "details", "findings", "letter"] as const;

export function CaseSteps({ caseId, current }: { caseId: string; current: (typeof STEPS)[number] }) {
  const { t, href } = useI18n();
  return (
    <ol className="steps" aria-label="Case steps">
      {STEPS.map((s, i) => (
        <li key={s} aria-current={s === current ? "step" : undefined}>
          <Link href={href(`/cases/${caseId}/${s}`)} style={{ color: "inherit", textDecoration: "none" }}>
            {i + 1}. {t(`steps.${s}`)}
          </Link>
        </li>
      ))}
    </ol>
  );
}

/** Moves focus to the page heading on mount (design §8: focus management on route change). */
export function PageTitle({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLHeadingElement>(null);
  useEffect(() => ref.current?.focus(), []);
  return (
    <h1 ref={ref} tabIndex={-1}>
      {children}
    </h1>
  );
}

export function ProblemNote({ error, map }: { error: unknown; map?: Record<string, string> }) {
  const { t } = useI18n();
  if (!error) return null;
  const code = error instanceof ApiError ? error.problem.code : "internal_error";
  const msg = map?.[code] ?? (error instanceof ApiError && error.problem.detail) ?? t("common.error");
  return <Callout tone="error">{msg}</Callout>;
}

export function Disclaimer() {
  const { t } = useI18n();
  return <p className="disclaimer">ⓘ {t("common.disclaimer")}</p>;
}
