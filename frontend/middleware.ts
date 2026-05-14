/**
 * Route protection.
 *
 * Any request to a non-public path without a valid NextAuth session is
 * redirected to /login. The login page itself, the NextAuth handler, and
 * static assets are always allowed through.
 *
 * We sit behind NextAuth's `withAuth` so the JWT (HS256 — see lib/auth.ts)
 * is validated using NEXTAUTH_SECRET on every navigation. Browsers without
 * the cookie just bounce to /login.
 */

import { withAuth } from "next-auth/middleware";

export default withAuth({
  pages: {
    signIn: "/login",
  },
});

export const config = {
  // Match everything except: the login page itself, NextAuth's own routes,
  // Next.js internals, the favicon, and any static asset under /_next/.
  matcher: ["/((?!login|api/auth|_next/static|_next/image|favicon.ico).*)"],
};
