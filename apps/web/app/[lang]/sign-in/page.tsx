"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { PageTitle, ProblemNote } from "@/components/ui";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function SignIn() {
  const { t, href, lang } = useI18n();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [invalid, setInvalid] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const ok = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
    setInvalid(!ok);
    if (!ok) return;
    setBusy(true);
    setError(null);
    try {
      await api("/auth/email/request", { body: { email: email.trim(), language: lang } });
      sessionStorage.setItem("cs_signin_email", email.trim());
      router.push(href("/sign-in/verify"));
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page reading">
      <PageTitle>{t("signIn.title")}</PageTitle>
      <form onSubmit={submit} noValidate>
        <div className="field">
          <label htmlFor="email">{t("signIn.emailLabel")}</label>
          <input id="email" className="input" type="email" inputMode="email" autoComplete="email" value={email}
                 onChange={(e) => setEmail(e.target.value)} aria-invalid={invalid}
                 aria-describedby={invalid ? "email-err" : undefined} />
          {invalid && <span id="email-err" className="field-error">{t("signIn.invalidEmail")}</span>}
        </div>
        <ProblemNote error={error} map={{ rate_limited: t("signIn.rateLimited") }} />
        <button className="btn btn-primary btn-block" disabled={busy} aria-busy={busy}>
          {busy ? t("signIn.sending") : t("signIn.send")}
        </button>
        <p className="muted">{t("signIn.consentNote")}</p>
      </form>
    </div>
  );
}
