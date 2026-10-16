"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { PageTitle, ProblemNote } from "@/components/ui";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { useMe } from "@/lib/use-session";

export default function SignIn() {
  const { t, href, lang } = useI18n();
  const router = useRouter();
  const [invalid, setInvalid] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const me = useMe();
  useEffect(() => { if (me) router.replace(href("/cases")); }, [me, router, href]);

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    // Read the field at submit time (uncontrolled input): text typed before hydration is not lost.
    const email = String(new FormData(e.currentTarget).get("email") ?? "");
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
          <input id="email" name="email" className="input" type="email" inputMode="email" autoComplete="email"
                 aria-invalid={invalid}
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
