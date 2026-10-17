"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AdminNav } from "@/components/admin-nav";
import { api, ApiError } from "@/lib/api";

type Item = {
  id: string; source: string; target_type: string; reason: string; comment: string | null; language: string | null;
  status: string; decision_category: string | null; created_at: string; payload: Record<string, unknown>;
  case_access_until: string | null;
};
type Me = { role: string; email_masked: string };
const STATUSES = ["open", "correct", "incorrect", "kb_fix", "skipped", "all"] as const;

// FR-040 review queue (English-only admin console). Case content opens only under the user's grant (FR-042).
export default function AdminHome() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [status, setStatus] = useState<(typeof STATUSES)[number]>("open");
  const [items, setItems] = useState<Item[] | null>(null);
  const [content, setContent] = useState<Record<string, unknown> | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    api<Me>("/admin/me").then(setMe).catch(() => router.replace("/en/admin/sign-in"));
  }, [router]);
  const load = useCallback(
    () => api<{ items: Item[] }>(`/admin/review-items?status=${status}`).then((r) => setItems(r.items)),
    [status],
  );
  useEffect(() => { if (me) void load(); }, [me, load]);

  async function decide(id: string, decision: string) {
    await api(`/admin/review-items/${id}`, { method: "PATCH", body: { status: decision } });
    await load();
  }

  async function openCase(id: string) {
    setMessage(null);
    try {
      setContent(await api<Record<string, unknown>>(`/admin/review-items/${id}/case-content`));
    } catch (e) {
      setContent(null);
      setMessage(e instanceof ApiError && e.problem.status === 403
        ? "The user hasn't given access to this case. The attempt was logged." : "Couldn't open the case.");
    }
  }

  async function signOut() {
    await api("/admin/auth/logout", { body: {} }).catch(() => undefined);
    router.replace("/en/admin/sign-in");
  }

  if (!me) return <div className="page">Loading…</div>;
  return (
    <div className="page">
      <AdminNav current="queue" />
      <div className="ledger-row">
        <h1>Review queue</h1>
        <span className="muted">{me.email_masked} · {me.role} <button className="btn btn-ghost" onClick={signOut}>Sign out</button></span>
      </div>
      <label htmlFor="status">Status </label>
      <select id="status" className="input" style={{ width: "auto" }} value={status}
              onChange={(e) => setStatus(e.target.value as (typeof STATUSES)[number])}>
        {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
      </select>
      {message && <div className="callout callout-warning" role="status">{message}</div>}
      {items?.length === 0 && <p>Nothing here.</p>}
      {items?.map((i) => (
        <div className="card" key={i.id}>
          <div className="ledger-row">
            <strong>{i.source} · {i.target_type} · {i.reason}</strong>
            <span className="pill pill-neutral">{i.status}</span>
          </div>
          <p className="muted">{new Date(i.created_at).toLocaleString("en-IN")} · language {i.language ?? "—"}</p>
          {i.comment && <p>“{i.comment}”</p>}
          <pre style={{ whiteSpace: "pre-wrap", fontSize: 13 }}>{JSON.stringify(i.payload, null, 2)}</pre>
          {i.status === "open" && (["correct", "incorrect", "kb_fix", "skipped"] as const).map((d) => (
            <button key={d} className="btn btn-secondary" style={{ marginRight: 8 }} onClick={() => decide(i.id, d)}>{d}</button>
          ))}
          <button className="btn btn-ghost" onClick={() => openCase(i.id)}>
            View case {i.case_access_until ? `(access until ${new Date(i.case_access_until).toLocaleDateString("en-IN")})` : "(needs user's grant)"}
          </button>
        </div>
      ))}
      {content && (
        <div className="card">
          <h2>Case content (user-granted access)</h2>
          <pre style={{ whiteSpace: "pre-wrap", fontSize: 13 }}>{JSON.stringify(content, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
