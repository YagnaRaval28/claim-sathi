import { formatInr } from "./format";

/** Confirmed figures and rule results the explanation may use. Nothing here comes from a model. */
export type ExplainInput = {
  decisionType: string | null;
  claimedPaise: number | null;
  paidPaise: number | null;
  noClause: { count: number; paise: number };
  reasonsNoClause: number;
  categories: string[];
  canWrite: boolean;
};

type T = (key: string, vars?: Record<string, string | number>) => string;

/** Phrases that predict an outcome. FR-017 bans them; the unit test checks every language. */
export const BANNED_PHRASES = ["you will win", "you will get", "guaranteed", "definitely", "100%", "sure to"];

/**
 * FR-017 plain-language explanation (≤150 words): what was decided, the amounts, the reasons in plain words, how
 * many items cite no clause, and the next step. Numbers are only confirmed facts or sums of confirmed deductions.
 */
export function explanation(x: ExplainInput, t: T): string[] {
  const out: string[] = [];
  const rejected = x.decisionType === "repudiation";
  if (rejected && x.claimedPaise !== null) {
    out.push(t("findings.rejectionSummary", { claimed: formatInr(x.claimedPaise) }));
  } else if (!rejected && x.paidPaise !== null && x.claimedPaise !== null) {
    out.push(t("findings.summary", { paid: formatInr(x.paidPaise), claimed: formatInr(x.claimedPaise) }));
  }
  const reasons = [...new Set(x.categories.filter((c) => c !== "other_unknown"))];
  if (reasons.length) {
    out.push(t("findings.explain.reasons", { reasons: reasons.map((c) => t(`categories.items.${c}`)).join("; ") }));
  }
  if (x.noClause.count > 0) {
    out.push(t("findings.noClauseSummary", { count: x.noClause.count, amount: formatInr(x.noClause.paise) }));
  }
  if (x.reasonsNoClause > 0) out.push(t("findings.reasonNoClauseSummary", { count: x.reasonsNoClause }));
  if (x.noClause.count > 0 || x.reasonsNoClause > 0) out.push(t("findings.explain.whyClause"));
  out.push(t(x.canWrite ? "findings.explain.nextLetter" : "findings.explain.nextAsk"));
  return out;
}

/** Glossary entries (PUB-06) linked under the explanation. */
export function explanationTerms(x: Pick<ExplainInput, "decisionType">): string[] {
  return ["grievance-officer", "policy-clause", x.decisionType === "repudiation" ? "repudiation" : "deduction",
    "ombudsman"];
}
