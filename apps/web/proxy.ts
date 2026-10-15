import { NextResponse, type NextRequest } from "next/server";

const LANGS = ["en", "gu", "hi"];

// Redirect locale-less paths to /{lang}/..., choosing from Accept-Language (design §2.3).
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (LANGS.some((l) => pathname === `/${l}` || pathname.startsWith(`/${l}/`))) return;
  const accept = request.headers.get("accept-language") ?? "";
  const lang = LANGS.find((l) => accept.toLowerCase().includes(l)) ?? "en";
  request.nextUrl.pathname = `/${lang}${pathname === "/" ? "" : pathname}`;
  return NextResponse.redirect(request.nextUrl);
}

export const config = {
  matcher: ["/((?!api|_next|favicon.ico|.*\\..*).*)"],
};
