"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AdminNav } from "@/components/admin-nav";
import { api, ApiError } from "@/lib/api";

type Period = { period: string; sampled: number; by_language: Record<string, number>; open: number; correct: number;
  incorrect: number; kb_fix: number; skipped: number;
  published: { sample_size: number; correct: number; published_at: string } | null };

// FR-040 AC1 monthly citation audit and FR-043 publishing (English-only admin console). Sampled citations are
// decided in the review queue; publishing needs every one decided.
export default function AdminAccuracy() {
  const router = useRouter();
  const [items, setItems] = useState<Period[] | null>(null);
  const [size, setSize] = useState(100);
  const [period, setPeriod] = useState("");
  const [current, setCurrent] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(() => api<{ items: Period[]; sample_size: number; current_period: string }>(
    "/admin/accuracy-audits").then((r) => {
    setItems(r.items);
    setSize(r.sample_size);
    setCurrent(r.current_period);
    setPeriod((p) => p || r.current_period);
  }), []);
  useEffect(() => {
    load().catch((e) => {
      if (e instanceof ApiError && e.problem.status === 401) router.replace("/en/admin/sign-in");
      else setMessage("Couldn't load audits.");
    });
  }, [load, router]);

  async function act(p: string, action: "sample" | "publish") {
    setMessage(null);
    try {
      await api(`/admin/accuracy-audits/${p}/${action}`, { body: {} });
      await load();
      setMessage(action === "sample" ? "Sample drawn. Decide each item in the review queue (status: open)."
        : "Published. The accuracy page now shows this result.");
    } catch (e) {
      setMessage(e instanceof ApiError ? e.problem.detail ?? "Failed." : "Failed.");
    }
  }

  return (
    <div className="page">
      <AdminNav current="accuracy" />
      <h1>Accuracy audits</h1>
      <p className="muted">Each month, draw a random sample of {size} citations shown to users (spread across English,
        Gujarati and Hindi), decide each in the review queue, then publish the result.</p>
      {message && <div className="callout callout-info" role="status">{message}</div>}
      <div className="card">
        <div className="field"><label htmlFor="period">Month</label>
          <input id="period" type="month" className="input" style={{ width: "auto" }} value={period}
                 max={current} onChange={(e) => setPeriod(e.target.value)} /></div>
        <button className="btn btn-primary" disabled={!period} onClick={() => act(period, "sample")}>Draw sample</button>
      </div>
      {items?.length === 0 && <p>No audits yet.</p>}
      {items?.map((p) => (
        <div className="card" key={p.period}>
          <div className="ledger-row">
            <strong>{p.period}</strong>
            <span className="pill pill-neutral">{p.published ? "published" : p.open ? "in review" : "ready"}</span>
          </div>
          <p className="muted">{p.sampled} sampled (en {p.by_language.en}, gu {p.by_language.gu}, hi {p.by_language.hi})
            · {p.open} open · {p.correct} correct · {p.incorrect + p.kb_fix} incorrect · {p.skipped} skipped</p>
          {p.published && <p>Published: {p.published.correct} of {p.published.sample_size} correct.</p>}
          <button className="btn btn-secondary" disabled={p.open > 0 || p.sampled === 0}
                  onClick={() => act(p.period, "publish")}>{p.published ? "Publish again" : "Publish"}</button>
        </div>
      ))}
    </div>
  );
}
