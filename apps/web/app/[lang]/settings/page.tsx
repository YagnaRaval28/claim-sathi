"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Saved, TypedConfirmDialog } from "@/components/dialogs";
import { ExportPanel } from "@/components/export-panel";
import { Callout, PageTitle, ProblemNote } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDateDmy } from "@/lib/format";
import { LANGS, useI18n } from "@/lib/i18n";
import { useRequireUser, type Me } from "@/lib/use-session";

const FULL = { en: "English", gu: "ગુજરાતી", hi: "हिन्दी" } as const;
type ConsentRow = { version: string; purposes: string[]; granted_at: string; withdrawn_at: string | null };

// ACC-01 and ACC-02 (FR-036, FR-032): each setting saves on its own and takes effect immediately.
export default function AccountSettings() {
  const { t, href, lang } = useI18n();
  const router = useRouter();
  const { me, gate } = useRequireUser();
  const [profile, setProfile] = useState<Me | null>(null);
  const [consents, setConsents] = useState<ConsentRow[]>([]);
  const [saved, setSaved] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [newEmail, setNewEmail] = useState("");
  const [code, setCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [emailDone, setEmailDone] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    setProfile(await api<Me>("/me"));
    setConsents((await api<{ items: ConsentRow[] }>("/me/consents")).items);
  }, []);
  useEffect(() => {
    if (!me) return;
    Promise.all([api<Me>("/me"), api<{ items: ConsentRow[] }>("/me/consents")])
      .then(([p, c]) => { setProfile(p); setConsents(c.items); })
      .catch(setError);
  }, [me]);

  const flash = (what: string) => { setSaved(what); setTimeout(() => setSaved(null), 2500); };
  const reminders = consents[0]?.purposes.includes("reminders") ?? false;

  async function setLanguage(l: string) {
    setError(null);
    try {
      await api("/me", { method: "PATCH", body: { display_language: l } });
      router.replace(`/${l}/settings`);
    } catch (e) { setError(e); }
  }

  async function setLargeText(on: boolean) {
    setError(null);
    setProfile((p) => (p ? { ...p, large_text: on } : p));  // optimistic: applies immediately (FR-036)
    document.documentElement.dataset.largeText = String(on);
    try {
      setProfile(await api<Me>("/me", { method: "PATCH", body: { large_text: on } }));
      flash("large");
    } catch (e) {
      setProfile((p) => (p ? { ...p, large_text: !on } : p));
      document.documentElement.dataset.largeText = String(!on);
      setError(e);
    }
  }

  async function setReminders(on: boolean) {
    setError(null);
    const before = consents;
    const purposes = on ? ["processing", "reminders"] : ["processing"];
    setConsents((rows) => [{ version: rows[0]?.version ?? "", purposes, granted_at: new Date().toISOString(),
      withdrawn_at: null }, ...rows]);  // optimistic: the toggle responds at once; rolled back on error
    try {
      const v = (await api<{ version: string }>("/consent/notice")).version;
      await api("/consents", { body: { version: v, purposes } });
      await load();
      flash("reminders");
    } catch (e) { setConsents(before); setError(e); }
  }

  async function sendCode(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api("/me/email", { body: { new_email: newEmail.trim() } });
      setCodeSent(true);
    } catch (err) { setError(err); }
  }

  async function verify(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api("/me/email/verify", { body: { code } });
      setCodeSent(false);
      setNewEmail("");
      setCode("");
      setEmailDone(true);
      await load();
    } catch (err) { setError(err); }
  }

  async function signOutAll() {
    if (!window.confirm(t("account.signOutAllConfirm"))) return;
    await api("/auth/logout-all", { body: {} }).catch(() => undefined);
    router.replace(href("/sign-in"));
  }

  if (!me) return gate;
  if (!profile) return <div className="page"><ProblemNote error={error} />{!error && t("common.loading")}</div>;

  return (
    <div className="page reading">
      <PageTitle>{t("account.title")}</PageTitle>
      <ProblemNote error={error} />

      <section className="card">
        <h2 style={{ marginTop: 0 }}>{t("account.language")}</h2>
        {LANGS.map((l) => (
          <label key={l} className="check" lang={l}>
            <input type="radio" name="lang" checked={l === lang} onChange={() => setLanguage(l)} />
            <span>{FULL[l]}</span>
          </label>
        ))}
      </section>

      <section className="card">
        <h2 style={{ marginTop: 0 }}>{t("account.email")}</h2>
        <p>{t("account.currentEmail", { email: profile.email_masked })}</p>
        {emailDone && <Callout tone="success">{t("account.emailChanged")}</Callout>}
        {!codeSent ? (
          <form onSubmit={sendCode}>
            <div className="field">
              <label htmlFor="new-email">{t("account.newEmail")}</label>
              <input id="new-email" className="input" type="email" autoComplete="email" value={newEmail}
                     onChange={(e) => setNewEmail(e.target.value)} />
            </div>
            <button className="btn btn-secondary" disabled={!newEmail.includes("@")}>{t("account.sendCode")}</button>
          </form>
        ) : (
          <form onSubmit={verify}>
            <p>{t("account.codeSent")}</p>
            <div className="field">
              <label htmlFor="email-code">{t("signIn.codeLabel")}</label>
              <input id="email-code" className="input" inputMode="numeric" autoComplete="one-time-code" maxLength={6}
                     value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} />
            </div>
            <button className="btn btn-primary" disabled={code.length !== 6}>{t("account.verify")}</button>
          </form>
        )}
      </section>

      <section className="card">
        <label className="check">
          <input type="checkbox" checked={reminders} onChange={(e) => setReminders(e.target.checked)} />
          <span>{t("account.reminders")}</span>
        </label>
        <Saved show={saved === "reminders"} />
        <label className="check" style={profile.large_text ? undefined : { fontSize: "1.125em" }}>
          <input type="checkbox" checked={profile.large_text} onChange={(e) => setLargeText(e.target.checked)} />
          <span>{t("account.largeText")}</span>
        </label>
        <Saved show={saved === "large"} />
      </section>

      <section className="card">
        <button className="btn btn-secondary" onClick={signOutAll}>{t("account.signOutAll")}</button>
      </section>

      <section className="card">
        <ExportPanel scope="account" label={t("caseSettings.downloadAll")} />
      </section>

      <section className="card">
        <h2 style={{ marginTop: 0 }}>{t("account.consents")}</h2>
        <ul>
          {consents.map((r) => (
            <li key={r.granted_at}>
              {t("account.consentRow", { date: formatDateDmy(r.granted_at.slice(0, 10)), version: r.version,
                purposes: r.purposes.map((p) => t(`account.purposes.${p}`)).join(", ") })}
              {r.withdrawn_at && <> · {t("account.withdrawn", { date: formatDateDmy(r.withdrawn_at.slice(0, 10)) })}</>}
            </li>
          ))}
        </ul>
      </section>

      <section className="danger-zone">
        <h2 style={{ marginTop: 0 }}>{t("caseSettings.danger")}</h2>
        <button className="btn btn-danger" onClick={() => setDeleting(true)}>{t("account.deleteAccount")}</button>
      </section>
      {deleting && (
        <TypedConfirmDialog
          title={t("account.deleteAccountTitle")}
          body={t("account.deleteAccountBody")}
          confirmLabel={t("account.deleteAccount")}
          challengePath="/me/delete-challenge"
          onClose={() => setDeleting(false)}
          run={async (c, challenge) => {
            await api("/me", { method: "DELETE", body: { confirm_code: c }, headers: { "X-Confirm-Challenge": challenge } });
            window.alert(t("account.accountDeleted"));
            router.replace(href(""));
          }}
        />
      )}
    </div>
  );
}
