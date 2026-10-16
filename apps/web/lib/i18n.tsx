"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";
import type en from "../messages/en.json";

import type { Lang } from "./langs";

export { LANGS, isLang, type Lang } from "./langs";
export type Dict = typeof en;

const Ctx = createContext<{ lang: Lang; dict: Dict } | null>(null);

export function I18nProvider({ lang, dict, children }: { lang: Lang; dict: Dict; children: ReactNode }) {
  const value = useMemo(() => ({ lang, dict }), [lang, dict]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

/**
 * t("findings.summary", { paid: "₹1" }) — dotted keys, {var} interpolation. Missing keys show the key (CI catches them).
 * `t` and `href` are stable across renders: pages use them as effect dependencies, and a new function on every
 * render re-ran those effects (a redirect loop after sign-in and repeated /me calls).
 */
export function useI18n() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useI18n outside I18nProvider");
  return useMemo(() => {
    const t = (key: string, vars?: Record<string, string | number>): string => {
      let node: unknown = v.dict;
      for (const part of key.split(".")) node = (node as Record<string, unknown> | undefined)?.[part];
      let s = typeof node === "string" ? node : key;
      for (const [k, val] of Object.entries(vars ?? {})) s = s.replaceAll(`{${k}}`, String(val));
      return s;
    };
    return { lang: v.lang, t, href: (path: string) => `/${v.lang}${path}` };
  }, [v]);
}
