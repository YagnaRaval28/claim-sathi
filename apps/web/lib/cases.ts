export type CaseSummary = {
  id: string;
  nickname: string;
  status: string;
  insurer_name: string | null;
  flags: { fields_confirmed: boolean; line_items_confirmed: boolean; stale: boolean };
  documents: { id: string; type: string; status: string; status_reason: string | null }[];
  extraction: "running" | "done" | "failed" | "none";
  version: number;
};

export function nextStep(c: CaseSummary): string {
  const letterReady = c.documents.some((d) => d.type === "decision_letter" && d.status === "ready");
  if (!letterReady || c.extraction === "running") return "documents";
  if (!c.flags.fields_confirmed || !c.flags.line_items_confirmed) return "details";
  return "findings";
}
