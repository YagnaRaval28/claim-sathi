"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";

type Setup = { enrolled: boolean; secret?: string; otpauth_uri?: string };

// FR-037: TOTP on every admin sign-in. First time: add the key to an authenticator app, then enter a code.
export default function AdminMfa() {
  const router = useRouter();
  const [setup, setSetup] = useState<Setup | null>(null);
  const [code, setCode] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    api<Setup>("/admin/auth/mfa").then(setSetup).catch(() => router.replace("/en/admin/sign-in"));
  }, [router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);
    try {
      await api("/admin/auth/totp", { body: { code } });
      router.replace("/en/admin");
    } catch (err) {
      const c = err instanceof ApiError ? err.problem.code : "";
      setMessage(c === "rate_limited" ? "Too many wrong codes. Try again in 15 minutes." : "That code isn't right.");
    }
  }

  if (!setup) return <div className="page">Loading…</div>;
  return (
    <div className="page reading">
      <h1>Authenticator code</h1>
      {!setup.enrolled && (
        <div className="card">
          <p>Add this key to your authenticator app (Google Authenticator, Microsoft Authenticator, and others):</p>
          <p><code style={{ fontSize: 18, letterSpacing: 2 }}>{setup.secret}</code></p>
          <p><a href={setup.otpauth_uri}>Open in authenticator app</a></p>
        </div>
      )}
      <form onSubmit={submit}>
        <div className="field">
          <label htmlFor="totp">6-digit code</label>
          <input id="totp" className="input" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={code}
                 onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} />
        </div>
        {message && <div className="callout callout-error" role="alert">{message}</div>}
        <button className="btn btn-primary" disabled={code.length !== 6}>Continue</button>
      </form>
    </div>
  );
}
