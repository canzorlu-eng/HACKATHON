"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";

const titleMap: Record<string, string> = {
  "/": "Ana Sayfa",
  "/analyze": "Analiz",
  "/history": "Geçmiş",
  "/onboarding": "Profilim",
};

function resolveTitle(pathname: string): string {
  if (pathname.startsWith("/history/") && pathname !== "/history")
    return "Analiz Detayı";
  return titleMap[pathname] ?? "HIWALOY";
}

export function TopBar() {
  const pathname = usePathname() ?? "/";
  const title = resolveTitle(pathname);

  return (
    <header className="sticky top-0 z-20 -mx-6 mb-6 flex h-16 items-center gap-3 border-b border-border bg-background/70 px-6 backdrop-blur-xl lg:-mx-10 lg:px-10">
      {/* Mobile brand */}
      <Link href="/" className="lg:hidden">
        <span className="text-base font-semibold tracking-tight text-foreground">
          HIWALOY
        </span>
      </Link>

      <p className="hidden text-sm font-medium text-muted-foreground lg:block">
        {title}
      </p>

      <div className="flex-1" />

      {/* Mobile nav button (links land on the same dashboard pages) */}
      <Link
        href="/analyze"
        className="inline-flex items-center gap-2 rounded-pill bg-brand-gradient px-4 py-2 text-xs font-semibold text-white shadow-[0_8px_30px_-10px_hsl(var(--brand)/0.6)] transition hover:brightness-110"
      >
        Yeni Analiz
      </Link>
      <Link
        href="/onboarding"
        className="grid h-9 w-9 place-items-center rounded-full border border-border bg-panel text-muted-foreground transition hover:text-foreground lg:hidden"
        aria-label="Menü"
      >
        <Menu size={16} />
      </Link>
    </header>
  );
}
