"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { LANGS, useI18n } from "@/lib/i18n";

const NATIVE = { en: "EN", gu: "ગુ", hi: "हि" } as const;
const FULL = { en: "English", gu: "ગુજરાતી", hi: "हिन्दी" } as const;

export function Header() {
  const { lang, t, href } = useI18n();
  const router = useRouter();
  const pathname = usePathname() ?? `/${lang}`;
  const rest = pathname.split("/").slice(2).join("/");
  const [signedIn, setSignedIn] = useState(false);

  // Re-check on navigation: the header stays mounted across sign-in and sign-out.
  useEffect(() => {
    let alive = true;
    api<{ large_text: boolean }>("/me")
      .then((m) => {
        if (!alive) return;
        setSignedIn(true);
        document.documentElement.dataset.largeText = String(m.large_text);  // FR-036: applies on every page
      })
      .catch(() => { if (alive) setSignedIn(false); });
    return () => { alive = false; };
  }, [pathname]);

  async function signOut() {
    try {
      await api("/auth/logout", { body: {} });
    } finally {
      setSignedIn(false);
      router.replace(href(""));
    }
  }

  return (
    <header className="header">
      <Link href={href("")} className="wordmark" aria-label={t("common.homeLabel")}>
        {t("common.appName")}
      </Link>
      <nav className="lang-switch" aria-label={t("common.language")}>
        {signedIn && (
          <>
            <Link href={href("/cases")}>{t("common.myCases")}</Link>
            <Link href={href("/settings")}>{t("common.settings")}</Link>
            <button type="button" className="btn btn-ghost" onClick={signOut}>{t("common.signOut")}</button>
          </>
        )}
        {LANGS.map((l) => (
          <Link key={l} href={`/${l}${rest ? `/${rest}` : ""}`} lang={l} aria-current={l === lang}
                aria-label={FULL[l]}>
            {NATIVE[l]}
          </Link>
        ))}
      </nav>
    </header>
  );
}
