"use client";

import { usePathname } from "next/navigation";
import { DashboardShell } from "./shell";

const FULL_SCREEN_ROUTES = ["/login"];

/**
 * Decides whether to wrap children in the dashboard shell.
 * Auth screens render bare (no sidebar / topbar) so they look like a
 * proper landing experience.
 */
export function LayoutShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() ?? "/";
  if (FULL_SCREEN_ROUTES.some((p) => pathname.startsWith(p))) {
    return <>{children}</>;
  }
  return <DashboardShell>{children}</DashboardShell>;
}
