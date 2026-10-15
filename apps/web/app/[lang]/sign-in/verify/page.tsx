"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, useSyncExternalStore } from "react";
import { Callout, PageTitle } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type VerifyOut = { next: "onboarding_language" | "consent" | "cases" };

export default function Verify() {
  const { t, href } = useI18n();
  const router = useRouter();
  const email = useSyncExternalStore(() => () => {}, () => sessionStorage.getItem("cs_signin_email") ?? "",
                                     () => "");
  const [code, setCode] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!sessionStorage.getItem("cs_signin_email")) router.replace(href("/sign-in"));
  }, [router, href]);

  async function submit(value: string) {
    if (!/^\d{6}$/.test(value) || busy) return;
    setBusy(true);
    setMsg(null);
    try {
      const out = await api<VerifyOut>("/auth/email/verify", { body: { email, code: value, trust_device: false } });
      sessionStorage.removeItem("cs_signin_email");
      router.replace(href(out.next === "cases" ? "/cases" : "/welcome/consent"));
    } catch (err) {
      const p = err instanceof ApiError ? err.problem : null;
      if (p?.code === "email_code_invalid") setMsg(t("signIn.wrongCode", { left: p.attempts_left ?? 0 }));
      else if (p?.code === "email_code_expired") setMsg(t("signIn.expired"));
      else if (p?.code === "rate_limited") setMsg(t("signIn.rateLimited"));
      else setMsg(t("common.error"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page reading">
      <PageTitle>{t("signIn.codeTitle")}</PageTitle>
      <p>{t("signIn.codeSent", { email })}</p>
      <p className="muted">{t("signIn.spam")}</p>
      <form onSubmit={(e) => { e.preventDefault(); void submit(code); }}>
        <div className="field">
          <label htmlFor="code">{t("signIn.codeLabel")}</label>
          <input id="code" className="input" inputMode="numeric" autoComplete="one-time-code" maxLength={6}
                 value={code} aria-invalid={!!msg}
                 onChange={(e) => {
                   const v = e.target.value.replace(/\D/g, "").slice(0, 6);
                   setCode(v);
                   if (v.length === 6) void submit(v);
                 }} />
        </div>
        {msg && <Callout tone="error">{msg}</Callout>}
        <button className="btn btn-primary btn-block" disabled={busy || code.length !== 6} aria-busy={busy}>
          {t("signIn.verify")}
        </button>
      </form>
      <p><Link href={href("/sign-in")}>{t("signIn.changeEmail")}</Link></p>
    </div>
  );
}
