/** Browser-side API calls.
 *
 * Default is same-origin (""), which Next.js rewrites to the internal
 * API service (see next.config.js). NEXT_PUBLIC_API_URL may still be
 * set for direct-API development, but compose deployments must NOT
 * rely on the browser reaching the internal `api` service.
 */
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export async function apiJson(path: string, init?: RequestInit) {
  const res = await fetch(`${API_URL}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  return res;
}

/** Authenticated mutation: fetch the session CSRF token first, then
 * send it as X-CSRF-Token (required by all phase-2 mutations). */
export async function apiMut(path: string, method: string, body?: unknown) {
  const csrf = await apiJson("/api/auth/csrf");
  if (!csrf.ok) return csrf;
  const { csrf_token } = await csrf.json();
  return apiJson(path, {
    method,
    headers: { "X-CSRF-Token": csrf_token },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}
