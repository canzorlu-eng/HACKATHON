/**
 * NextAuth (Auth.js v4) configuration — Google provider.
 *
 * Cookie storage uses NextAuth's default JWE (HKDF-derived encryption).
 * We do NOT override jwt.encode / jwt.decode, because middleware runs in
 * the Edge runtime where the `jsonwebtoken` package (Node crypto) can't
 * load — overriding would make every middleware request fail to decode
 * and silently log the user out.
 *
 * For backend authentication we sign a *separate* HS256 JWS using
 * `jsonwebtoken` in the session() callback and attach it as
 * `session.accessToken`. The frontend forwards this token as
 * `Authorization: Bearer …` and FastAPI verifies it via python-jose.
 *
 * Token claims:
 *   sub      — Google user id (stable across sessions)
 *   email    — Google email
 *   name     — display name
 *   picture  — avatar url
 *   iat/exp  — automatic
 */

import type { NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import jwt from "jsonwebtoken";

const SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30; // 30 days

export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID ?? "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET ?? "",
    }),
  ],
  session: {
    strategy: "jwt",
    maxAge: SESSION_MAX_AGE_SECONDS,
  },
  pages: {
    signIn: "/login",
  },
  callbacks: {
    // Capture Google's stable sub on first sign-in and persist into the JWT.
    async jwt({ token, account, profile }) {
      if (account && profile) {
        token.sub = (profile as { sub?: string }).sub ?? token.sub;
        token.email = profile.email ?? token.email;
        token.name = profile.name ?? token.name;
        token.picture = (profile as { picture?: string }).picture ?? token.picture;
      }
      return token;
    },
    // Expose the raw access JWT on the session so we can attach it as a
    // Bearer header on every backend call from the client.
    async session({ session, token }) {
      if (session.user) {
        (session.user as { id?: string }).id = token.sub;
        (session.user as { email?: string }).email = (token.email as string) ?? session.user.email;
      }
      // Re-sign the same claims so the client gets a serializable token string.
      (session as { accessToken?: string }).accessToken = jwt.sign(
        {
          sub: token.sub,
          email: token.email,
          name: token.name,
          picture: token.picture,
        },
        process.env.NEXTAUTH_SECRET ?? "",
        { algorithm: "HS256", expiresIn: SESSION_MAX_AGE_SECONDS },
      );
      return session;
    },
  },
};
