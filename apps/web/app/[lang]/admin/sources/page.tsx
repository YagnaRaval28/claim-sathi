"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AdminNav } from "@/components/admin-nav";
import { api, ApiError } from "@/lib/api";

type Source = { id: string; type: string; issuer: string; title: string; identifier: string; version: string;
  effective_from: string; status: string; checked_by: string | null; chunks: number; chunks_missing_clause_ref: number;
  synthetic: boolean };
type Chunk = { id: string; ordinal: number; clause_ref: string | null; text: string; flags: string[] };

// FR-038 knowledge base: drafts, attested publishing, retiring (never deleting).
export default function AdminSources() {
  const router = useRouter();
  const [sources, setSources] = useState<Source[] | null>(null);
  const [chunks, setChunks] = useState<{ id: string; items: Chunk[] } | null>(null);
  const [attest, setAttest] = useState<Record<string, boolean>>({});
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(() => api<{ items: Source[] }>("/admin/sources").then((r) => setSources(r.items)), []);
  useEffect(() => {
    load().catch((e) => {
      if (e instanceof ApiError && e.problem.status === 401) router.replace("/en/admin/sign-in");
      else setMessage(e instanceof ApiError && e.problem.status === 403 ? "Admins only." : "Couldn't load sources.");
    });
  }, [load, router]);

  async function upload(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setMessage(null);
    try {
      await api("/admin/sources", { form: new FormData(e.currentTarget) });
      e.currentTarget.reset();
      await load();
      setMessage("Draft created. Check its chunks, then publish.");
    } catch (err) {
      setMessage(err instanceof ApiError ? err.problem.detail ?? "Upload failed." : "Upload failed.");
    }
  }

  async function act(id: string, action: "publish" | "retire") {
    setMessage(null);
    try {
      await api(`/admin/sources/${id}/${action}`, action === "publish"
        ? { body: { attest_checked: attest[id] === true } } : { body: {} });
      await load();
    } catch (err) {
      setMessage(err instanceof ApiError ? err.problem.detail ?? "Failed." : "Failed.");
    }
  }

  return (
    <div className="page">
      <AdminNav current="sources" />
      <h1>Knowledge base</h1>
      {message && <div className="callout callout-info" role="status">{message}</div>}
      <form className="card" onSubmit={upload}>
        <h2 style={{ marginTop: 0 }}>Upload a source</h2>
        <div className="field"><label htmlFor="file">Official PDF (text) or UTF-8 text file</label>
          <input id="file" name="file" type="file" accept="application/pdf,text/plain" required /></div>
        <div className="field"><label htmlFor="type">Type</label>
          <select id="type" name="type" className="input"><option value="regulation">Regulation</option>
            <option value="policy_wording">Policy wording</option></select></div>
        {([["issuer", "Issuer"], ["title", "Title"], ["identifier", "Identifier (circular no. or product UIN)"],
          ["version", "Version"], ["url", "Official URL (optional)"]] as const).map(([name, label]) => (
          <div className="field" key={name}><label htmlFor={name}>{label}</label>
            <input id={name} name={name} className="input" required={name !== "url"} /></div>
        ))}
        <div className="field"><label htmlFor="effective_from">Effective from</label>
          <input id="effective_from" name="effective_from" type="date" className="input" required /></div>
        <button className="btn btn-primary">Create draft</button>
      </form>
      {sources?.map((s) => (
        <div className="card" key={s.id}>
          <div className="ledger-row">
            <strong>{s.title} · v{s.version}</strong>
            <span className="pill pill-neutral">{s.status}{s.synthetic ? " · SYNTHETIC" : ""}</span>
          </div>
          <p className="muted">{s.type} · {s.issuer} · {s.identifier} · from {s.effective_from} · {s.chunks} chunks
            {s.chunks_missing_clause_ref > 0 && <> · <strong>{s.chunks_missing_clause_ref} without a clause ref</strong></>}</p>
          <button className="btn btn-ghost" onClick={async () =>
            setChunks({ id: s.id, items: (await api<{ items: Chunk[] }>(`/admin/sources/${s.id}/chunks`)).items })}>
            View chunks</button>
          {s.status === "draft" && (
            <>
              <label className="check"><input type="checkbox" checked={attest[s.id] === true}
                onChange={(e) => setAttest({ ...attest, [s.id]: e.target.checked })} />
                <span>I checked this text against the official document</span></label>
              <button className="btn btn-primary" disabled={!attest[s.id]} onClick={() => act(s.id, "publish")}>Publish</button>
            </>
          )}
          {s.status === "published" && (
            <button className="btn btn-secondary" onClick={() => act(s.id, "retire")}>Retire (keeps old citations)</button>
          )}
          {chunks?.id === s.id && (
            <ol>{chunks.items.map((c) => (
              <li key={c.id}><strong>{c.clause_ref ?? "⚠ no clause ref"}</strong>: {c.text.slice(0, 240)}
                {c.text.length > 240 ? "…" : ""}</li>
            ))}</ol>
          )}
        </div>
      ))}
    </div>
  );
}
