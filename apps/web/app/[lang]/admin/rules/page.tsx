"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AdminNav } from "@/components/admin-nav";
import { api, ApiError } from "@/lib/api";

type Rule = { rule_key: string; version: number; kind: string; status: string; params: Record<string, unknown>;
  source_ref: string | null; verified_by: string | null };

// FR-039 rules table: every change is a new version; enabling needs a source and a verifier.
export default function AdminRules() {
  const router = useRouter();
  const [rules, setRules] = useState<Rule[] | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [verifier, setVerifier] = useState("");

  const load = useCallback(() => api<{ items: Rule[] }>("/admin/rules").then((r) => setRules(r.items)), []);
  useEffect(() => {
    load().catch((e) => {
      if (e instanceof ApiError && e.problem.status === 401) router.replace("/en/admin/sign-in");
      else setMessage(e instanceof ApiError && e.problem.status === 403 ? "Admins only." : "Couldn't load rules.");
    });
  }, [load, router]);

  async function newVersion(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setMessage(null);
    try {
      const params = JSON.parse(String(f.get("params") || "{}")) as Record<string, unknown>;
      await api(`/admin/rules/${String(f.get("key"))}/versions`, { body: { kind: String(f.get("kind")) || null, params,
        source_ref: String(f.get("source_ref")) || null } });
      e.currentTarget.reset();
      await load();
      setMessage("New version created (disabled until you enable it).");
    } catch (err) {
      setMessage(err instanceof SyntaxError ? "Parameters must be valid JSON."
        : err instanceof ApiError ? err.problem.detail ?? "Failed." : "Failed.");
    }
  }

  async function toggle(r: Rule, action: "enable" | "disable") {
    setMessage(null);
    try {
      await api(`/admin/rules/${r.rule_key}/versions/${r.version}/${action}`,
        { body: action === "enable" ? { verified_by: verifier } : {} });
      await load();
    } catch (err) {
      setMessage(err instanceof ApiError ? err.problem.detail ?? "Failed." : "Failed.");
    }
  }

  return (
    <div className="page">
      <AdminNav current="rules" />
      <h1>Rules</h1>
      {message && <div className="callout callout-info" role="status">{message}</div>}
      <div className="field"><label htmlFor="verifier">Verified by (your name, needed to enable)</label>
        <input id="verifier" className="input" value={verifier} onChange={(e) => setVerifier(e.target.value)} /></div>
      <form className="card" onSubmit={newVersion}>
        <h2 style={{ marginTop: 0 }}>New version</h2>
        <div className="field"><label htmlFor="key">Rule key</label><input id="key" name="key" className="input" required
          placeholder="RULE-MC-01" /></div>
        <div className="field"><label htmlFor="kind">Kind (only for a new rule)</label><input id="kind" name="kind" className="input" /></div>
        <div className="field"><label htmlFor="source_ref">Source citation</label><input id="source_ref" name="source_ref" className="input" /></div>
        <div className="field"><label htmlFor="params">Parameters (JSON)</label>
          <textarea id="params" name="params" className="input" rows={4} defaultValue="{}" /></div>
        <button className="btn btn-primary">Create version</button>
      </form>
      {rules?.map((r) => (
        <div className="card" key={`${r.rule_key}@${r.version}`}>
          <div className="ledger-row">
            <strong>{r.rule_key} · v{r.version}</strong>
            <span className="pill pill-neutral">{r.status}</span>
          </div>
          <p className="muted">{r.kind} · source: {r.source_ref ?? "—"} · verified by: {r.verified_by ?? "—"}</p>
          <pre style={{ whiteSpace: "pre-wrap", fontSize: 12 }}>{JSON.stringify(r.params, null, 2)}</pre>
          {r.status !== "enabled" ? (
            <button className="btn btn-secondary" disabled={!verifier.trim()} onClick={() => toggle(r, "enable")}>Enable</button>
          ) : (
            <button className="btn btn-ghost" onClick={() => toggle(r, "disable")}>Disable</button>
          )}
        </div>
      ))}
    </div>
  );
}
