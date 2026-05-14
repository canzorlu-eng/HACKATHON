"use client";

import { getSession } from "next-auth/react";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/**
 * `fetch` wrapper that automatically attaches the NextAuth-issued HS256 JWT
 * as `Authorization: Bearer <token>`. The backend verifies the same secret
 * (NEXTAUTH_SECRET) and resolves the user via google_sub.
 *
 * Use this for every authenticated backend call. The Content-Type is left
 * to the caller so FormData (multipart) works without manual headers.
 */
export async function apiFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const session = await getSession();
  const token = (session as { accessToken?: string } | null)?.accessToken;

  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);

  return fetch(`${API_BASE}${path}`, { ...init, headers });
}
