"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { Callout, PageTitle, ProblemNote } from "@/components/ui";
import { api, newKey } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { useRequireUser } from "@/lib/use-session";

type Answers = { health_india?: string; situation?: string; policy_type?: string; relation?: string;
  in_litigation?: string; complainant_name: string; nickname: string };

function Radios({ name, label, value, options, onChange, error }: {
  name: string; label: string; value?: string; options: [string, string][]; onChange: (v: string) => void;
  error?: string;
}) {
  return (
    <fieldset className="field" aria-invalid={!!error} style={{ border: 0, padding: 0 }}>
      <legend style={{ fontWeight: 600, marginBottom: 8 }}>{label}</legend>
      {options.map(([v, text]) => (
        <label key={v} className="check card" style={{ marginBottom: 8, cursor: "pointer",
          borderColor: value === v ? "var(--color-primary)" : undefined,
          background: value === v ? "var(--color-primary-subtle)" : undefined }}>
          <input type="radio" name={name} value={v} checked={value === v} onChange={() => onChange(v)} />
          <span>{text}</span>
        </label>
      ))}
      {error && <span className="field-error">{error}</span>}
    </fieldset>
  );
}

export default function NewCase() {
  const { t, href } = useI18n();
  const router = useRouter();
  const me = useRequireUser();
  const [a, setA] = useState<Answers>({ complainant_name: "", nickname: "" });
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const key = useRef<string | null>(null); // one key per form session, created on first submit
  const set = (k: keyof Answers) => (v: string) => setA((x) => ({ ...x, [k]: v }));
  const req = (v?: string) => (submitted && !v ? t("newCase.required") : undefined);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setSubmitted(true);
    const { health_india, situation, policy_type, relation, in_litigation, complainant_name } = a;
    if (!health_india || !situation || !policy_type || !relation || !in_litigation || !complainant_name.trim()) return;
    if (health_india === "no") return;
    setBusy(true);
    try {
      const c = await api<{ id: string }>("/cases", {
        idempotencyKey: (key.current ??= newKey()),
        body: { nickname: a.nickname.trim() || null, eligibility: { health_india, situation, policy_type, relation,
          in_litigation, complainant_name: complainant_name.trim() } },
      });
      router.replace(href(`/cases/${c.id}/documents`));
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  if (!me) return <div className="page">{t("common.loading")}</div>;
  const yn: [string, string][] = [["yes", t("newCase.yes")], ["no", t("newCase.no")], ["not_sure", t("newCase.notSure")]];
  return (
    <form className="page reading" onSubmit={create} noValidate>
      <PageTitle>{t("newCase.title")}</PageTitle>
      <Radios name="hi" label={t("newCase.q1")} value={a.health_india} options={yn} onChange={set("health_india")}
              error={req(a.health_india)} />
      {a.health_india === "no" && <Callout tone="info">{t("newCase.outOfScope")}</Callout>}
      <Radios name="sit" label={t("newCase.q2")} value={a.situation} onChange={set("situation")} error={req(a.situation)}
              options={[["rejected", t("newCase.rejected")], ["partly_paid", t("newCase.partlyPaid")],
                        ["delayed", t("newCase.delayed")], ["other", t("newCase.other")]]} />
      <Radios name="pt" label={t("newCase.q3")} value={a.policy_type} onChange={set("policy_type")}
              error={req(a.policy_type)}
              options={[["individual", t("newCase.individual")], ["floater", t("newCase.floater")],
                        ["group", t("newCase.group")], ["unknown", t("newCase.unknown")]]} />
      <div className="field">
        <label htmlFor="cn">{t("newCase.complainantName")}</label>
        <input id="cn" className="input" autoComplete="name" value={a.complainant_name} maxLength={120}
               onChange={(e) => set("complainant_name")(e.target.value)}
               aria-invalid={!!req(a.complainant_name.trim())} />
        {req(a.complainant_name.trim()) && <span className="field-error">{t("newCase.required")}</span>}
      </div>
      <Radios name="rel" label={t("newCase.relation")} value={a.relation} onChange={set("relation")}
              error={req(a.relation)}
              options={[["self", t("newCase.self")], ["spouse", t("newCase.spouse")], ["parent", t("newCase.parent")],
                        ["child", t("newCase.child")], ["other", t("newCase.otherRelation")]]} />
      <Radios name="lit" label={t("newCase.q5")} value={a.in_litigation} options={yn} onChange={set("in_litigation")}
              error={req(a.in_litigation)} />
      {a.in_litigation === "yes" && <Callout tone="info">{t("newCase.litigationNote")}</Callout>}
      <div className="field">
        <label htmlFor="nn">{t("newCase.nickname")}</label>
        <input id="nn" className="input" value={a.nickname} maxLength={80} onChange={(e) => set("nickname")(e.target.value)} />
      </div>
      <ProblemNote error={error} map={{ open_case_limit: t("cases.limit"), out_of_scope: t("newCase.outOfScope") }} />
      <div className="action-bar">
        <button className="btn btn-primary btn-block" disabled={busy || a.health_india === "no"}>{t("newCase.create")}</button>
      </div>
    </form>
  );
}
