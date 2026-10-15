"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LANGS, useI18n } from "@/lib/i18n";

const NATIVE = { en: "EN", gu: "ગુ", hi: "हि" } as const;
const FULL = { en: "English", gu: "ગુજરાતી", hi: "हिन्दी" } as const;

export function Header() {
  const { lang, t, href } = useI18n();
  const pathname = usePathname() ?? `/${lang}`;
  const rest = pathname.split("/").slice(2).join("/");
  return (
    <header className="header">
      <Link href={href("")} className="wordmark" aria-label={`${t("common.appName")} home`}>
        {t("common.appName")}
      </Link>
      <nav className="lang-switch" aria-label={t("common.language")}>
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
