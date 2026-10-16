"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { ProblemNote } from "@/components/ui";
import { api, ApiError } from "./api";
import { useI18n } from "./i18n";

export type Me = { id: string; display_language: string; email_masked: string; onboarded: boolean;
  consent: { version: string; current: boolean } };

/** Signed-in user or null; never redirects (header, home page). `undefined` while loading. */
export function useMe(): Me | null | undefined {
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  useEffect(() => {
    let alive = true;
    api<Me>("/me")
      .then((m) => { if (alive) setMe(m); })
      .catch(() => { if (alive) setMe(null); });
    return () => { alive = false; };
  }, []);
  return me;
}

/**
 * Client-side guard: 401 → sign-in; no current consent → consent screen. The API enforces both regardless.
 * `me` is stable state (safe as an effect dependency). Until it is set, render `gate`: "Loading…", or the error
 * with a retry button when /me fails for any other reason (so a page never loads forever).
 */
export function useRequireUser(opts: { needConsent?: boolean } = {}): { me: Me | null; gate: ReactNode } {
  const router = useRouter();
  const { t, href } = useI18n();
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const needConsent = opts.needConsent !== false;
  useEffect(() => {
    let alive = true;
    api<Me>("/me")
      .then((m) => {
        if (!alive) return;
        if (needConsent && !m.consent.current) router.replace(href("/welcome/consent"));
        else setMe(m);
      })
      .catch((e) => {
        if (!alive) return;
        if (e instanceof ApiError && e.problem.status === 401) router.replace(href("/sign-in"));
        else setError(e);
      });
    return () => { alive = false; };
  }, [router, href, needConsent, attempt]);
  const gate = error ? (
    <div className="page">
      <ProblemNote error={error} />
      <button className="btn btn-secondary" onClick={() => { setError(null); setAttempt((n) => n + 1); }}>
        {t("common.retry")}
      </button>
    </div>
  ) : (
    <div className="page" aria-busy="true">{t("common.loading")}</div>
  );
  return { me, gate };
}
