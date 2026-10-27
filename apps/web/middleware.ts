import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * UX-only redirect: if the session cookie is absent, send the visitor to
 * /gate. This is NOT the security boundary — the API re-validates the
 * session (and revocation) on every authenticated call, and the dashboard
 * page also checks /api/auth/me client-side. A forged cookie name alone
 * authenticates nothing.
 */
export function middleware(req: NextRequest) {
  const hasSession = Boolean(req.cookies.get("harlearn_session")?.value);
  const isGate = req.nextUrl.pathname.startsWith("/gate");
  if (!hasSession && !isGate) {
    return NextResponse.redirect(new URL("/gate", req.url));
  }
  if (hasSession && isGate) {
    return NextResponse.redirect(new URL("/", req.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/", "/gate"],
};
