"use client";

import { useSyncExternalStore } from "react";

// Admin console is English-only (product decision). Google allowlist first, then a mandatory TOTP code.
export default function AdminSignIn() {
  const denied = useSyncExternalStore(() => () => {}, () => new URLSearchParams(window.location.search).has("denied"),
                                      () => false);
  return (
    <div className="page reading">
      <h1>ClaimSathi admin</h1>
      {denied && <div className="callout callout-error" role="alert">This Google account is not on the admin list.</div>}
      <p>Sign in with your allowlisted Google account. You will then need your authenticator code.</p>
      {/* A plain GET form: a full-page navigation, because the API redirects to Google and back. */}
      <form method="get" action="/api/v1/admin/auth/google/start">
        <button className="btn btn-primary">Sign in with Google</button>
      </form>
    </div>
  );
}
