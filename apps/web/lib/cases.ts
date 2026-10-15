export type CaseSummary = {
  id: string;
  nickname: string;
  status: string;
  insurer_name: string | null;
  flags: { fields_confirmed: boolean; line_items_confirmed: boolean; stale: boolean };
  documents: { id: string; type: string; status: string; status_reason: string | null }[];
  version: number;
};

export function nextStep(c: CaseSummary): string {
  if (!c.documents.some((d) => d.status === "ready")) return "documents";
  if (!c.flags.fields_confirmed || !c.flags.line_items_confirmed) return "details";
  return "findings";
}
