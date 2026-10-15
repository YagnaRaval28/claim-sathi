// Shared by server and client code (no "use client" here).
export const LANGS = ["en", "gu", "hi"] as const;
export type Lang = (typeof LANGS)[number];

export function isLang(v: string): v is Lang {
  return (LANGS as readonly string[]).includes(v);
}
