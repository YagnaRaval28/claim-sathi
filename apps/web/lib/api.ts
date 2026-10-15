// Same-origin API client. /api/* is rewritten by Next.js to the FastAPI service (system-design ADR-010).
// Unsafe methods carry the double-submit CSRF header; errors are RFC 9457 problem+json.

export type Problem = {
  code: string;
  status: number;
  title?: string;
  detail?: string;
  errors?: { field: string; code: string; message: string }[];
  attempts_left?: number;
  retry_after_s?: number;
};

export class ApiError extends Error {
  constructor(public problem: Problem) {
    super(problem.code);
  }
}

function readCookie(name: string): string | null {
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}

async function csrfToken(): Promise<string> {
  const existing = readCookie("cs_csrf");
  if (existing) return existing;
  const r = await fetch("/api/v1/auth/csrf", { credentials: "same-origin" });
  return ((await r.json()) as { csrf_token: string }).csrf_token;
}

type Opts = { method?: string; body?: unknown; form?: FormData; idempotencyKey?: string };

export async function api<T>(path: string, opts: Opts = {}): Promise<T> {
  const method = opts.method ?? (opts.body !== undefined || opts.form ? "POST" : "GET");
  const headers: Record<string, string> = {};
  if (method !== "GET") headers["X-CSRF-Token"] = await csrfToken();
  if (opts.idempotencyKey) headers["Idempotency-Key"] = opts.idempotencyKey;
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }
  const r = await fetch(`/api/v1${path}`, { method, headers, body, credentials: "same-origin" });
  if (r.status === 204) return undefined as T;
  const data = await r.json().catch(() => ({ code: "internal_error", status: r.status }));
  if (!r.ok) throw new ApiError({ ...(data as Problem), status: r.status });
  return data as T;
}

export function newKey(): string {
  return crypto.randomUUID();
}
