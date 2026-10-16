import { NextResponse, type NextRequest } from "next/server";

const LANGS = ["en", "gu", "hi"];

// Redirect locale-less paths to /{lang}/..., choosing from Accept-Language (design §2.3).
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (LANGS.some((l) => pathname === `/${l}` || pathname.startsWith(`/${l}/`))) return;
  const lang = pickLang(request.headers.get("accept-language") ?? "");
  request.nextUrl.pathname = `/${lang}${pathname === "/" ? "" : pathname}`;
  return NextResponse.redirect(request.nextUrl);
}

/** Highest-q supported language from Accept-Language ("hi-IN,hi;q=0.9,en;q=0.8" → "hi"). */
export function pickLang(header: string): string {
  const ranked = header
    .split(",")
    .map((part, i) => {
      const [tag, ...params] = part.trim().toLowerCase().split(";");
      const q = Number(params.find((p) => p.trim().startsWith("q="))?.split("=")[1] ?? "1");
      return { base: tag.split("-")[0], q: Number.isFinite(q) ? q : 0, i };
    })
    .filter((x) => x.q > 0 && LANGS.includes(x.base))
    .sort((a, b) => b.q - a.q || a.i - b.i);
  return ranked[0]?.base ?? "en";
}

export const config = {
  matcher: ["/((?!api|_next|favicon.ico|.*\\..*).*)"],
};
