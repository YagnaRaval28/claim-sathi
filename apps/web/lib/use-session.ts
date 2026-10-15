"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, ApiError } from "./api";
import { useI18n } from "./i18n";

export type Me = { id: string; display_language: string; email_masked: string; onboarded: boolean;
  consent: { version: string; current: boolean } };

/** Client-side guard: 401 → sign-in; no current consent → consent screen. The API enforces both regardless. */
export function useRequireUser(opts: { needConsent?: boolean } = { needConsent: true }) {
  const router = useRouter();
  const { href } = useI18n();
  const [me, setMe] = useState<Me | null>(null);
  useEffect(() => {
    api<Me>("/me")
      .then((m) => {
        if (opts.needConsent !== false && !m.consent.current) router.replace(href("/welcome/consent"));
        else setMe(m);
      })
      .catch((e) => {
        if (e instanceof ApiError && e.problem.status === 401) router.replace(href("/sign-in"));
      });
  }, [router, href, opts.needConsent]);
  return me;
}
