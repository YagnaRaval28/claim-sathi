export type CaseSummary = {
  id: string;
  nickname: string;
  status: string;
  stage: "S0_PREPARE" | "S1_INSURER_GRIEVANCE" | "S3_OMBUDSMAN" | "CLOSED";
  insurer_name: string | null;
  next_deadline: { kind: string; due_date: string; days_left: number } | null;
  flags: { fields_confirmed: boolean; line_items_confirmed: boolean; stale: boolean };
  documents: { id: string; type: string; status: string; status_reason: string | null }[];
  extraction: "running" | "done" | "failed" | "none";
  version: number;
};

export function nextStep(c: CaseSummary): string {
  if (c.stage !== "S0_PREPARE") return "track";
  const letterReady = c.documents.some((d) => d.type === "decision_letter" && d.status === "ready");
  if (!letterReady || c.extraction === "running") return "documents";
  if (!c.flags.fields_confirmed || !c.flags.line_items_confirmed) return "details";
  return "findings";
}
