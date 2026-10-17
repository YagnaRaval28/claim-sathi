// Types for /cases/{id}/escalation (system-design §5). All decisions are made by the API's deterministic rules.

export type CheckResult = "pass" | "block" | "warn" | "inform" | "unavailable";

export type Escalation = {
  stage: "S0_PREPARE" | "S1_INSURER_GRIEVANCE" | "S3_OMBUDSMAN" | "CLOSED";
  status: "open" | "closed";
  s2_filed_at: string | null;
  deadlines: {
    kind: string;
    due_date: string;
    days_left: number;
    status: "active" | "passed" | "cancelled";
    rule: { key: string; version: number; source_ref: string | null };
    computed_from: Record<string, string>;
  }[];
  ombudsman_checks: {
    rule_key: string;
    version: number | null;
    result: CheckResult;
    message_key: string;
    params: Record<string, string>;
    fix_action: string | null;
    source_ref: string | null;
    acknowledged: boolean;
  }[];
  blocked: boolean;
  events: CaseEventView[];
  next_action: { key: string; date?: string | null };
};

export type CaseEventView = {
  id: string;
  kind: EventKind;
  event_date: string;
  metadata: Record<string, string | number | boolean>;
  document_id: string | null;
};

export const EVENT_KINDS = [
  "s1_sent",
  "insurer_reply",
  "s2_filed",
  "s3_filed",
  "ombudsman_outcome",
  "payment_received",
  "closed",
] as const;
export type EventKind = (typeof EVENT_KINDS)[number];

/** Design §5.2.4: urgency from days remaining (always shown with text and an icon, never colour alone). */
export function urgency(daysLeft: number): { tone: "neutral" | "info" | "warning" | "error"; icon: string } {
  if (daysLeft < 0) return { tone: "error", icon: "✕" };
  if (daysLeft <= 3) return { tone: "error", icon: "!" };
  if (daysLeft <= 14) return { tone: "warning", icon: "⚠" };
  if (daysLeft <= 30) return { tone: "info", icon: "ⓘ" };
  return { tone: "neutral", icon: "○" };
}

/** IST calendar date "today" as YYYY-MM-DD (the API validates event dates in IST). */
export function todayIst(now: Date = new Date()): string {
  return new Date(now.getTime() + 330 * 60_000).toISOString().slice(0, 10);
}
