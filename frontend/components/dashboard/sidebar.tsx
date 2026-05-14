"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Sparkles, History, User2, Wand2, Home } from "lucide-react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const items = [
  { href: "/", label: "Ana Sayfa", icon: Home },
  { href: "/analyze", label: "Analiz", icon: Wand2 },
  { href: "/history", label: "Geçmiş", icon: History },
  { href: "/onboarding", label: "Profilim", icon: User2 },
];

function ModeBadge() {
  const [demoMode, setDemoMode] = useState<boolean | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/health`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && typeof data.demo_mode === "boolean") {
          setDemoMode(data.demo_mode);
        } else {
          setDemoMode(false);
        }
      })
      .catch(() => setDemoMode(false));
  }, []);

  // Until we know, render nothing — don't lie either way.
  if (demoMode === null) return null;

  if (demoMode) {
    return (
      <div className="mb-3 rounded-card border border-border bg-panel-elev p-4">
        <div className="flex items-center gap-2 text-xs font-medium text-brand">
          <Sparkles size={14} />
          DEMO Modu
        </div>
        <p className="mt-2 text-xs leading-relaxed text-subtle-foreground">
          Yerel kurulumda örnek veriyle çalışıyor — Gemini API anahtarı
          gerekmez.
        </p>
      </div>
    );
  }

  return (
    <div className="mb-3 rounded-card border border-brand/30 bg-brand-soft p-4">
      <div className="flex items-center gap-2 text-xs font-medium text-brand">
        <Sparkles size={14} />
        Canlı AI
      </div>
      <p className="mt-2 text-xs leading-relaxed text-subtle-foreground">
        Gemini multimodal analiz ve ChromaDB üzerinde gerçek topluluk
        yorumları ile çalışıyor.
      </p>
    </div>
  );
}

function ProfileChip() {
  const pathname = usePathname();
  const [profile, setProfile] = useState<
    { height?: number; weight?: number; fit?: string } | null
  >(null);

  useEffect(() => {
    if (typeof window === "undefined") return;

    function read() {
      const userId = localStorage.getItem("hiwaloy_user_id");
      const h = Number(localStorage.getItem("hiwaloy_height_cm"));
      const w = Number(localStorage.getItem("hiwaloy_weight_kg"));
      const fit = localStorage.getItem("hiwaloy_fit_preference") ?? undefined;
      setProfile(
        userId ? { height: h || undefined, weight: w || undefined, fit } : null
      );
    }

    read();
    // Same-tab signal fired by /onboarding after a successful save.
    window.addEventListener("hiwaloy:profile-changed", read);
    // Cross-tab signal for free.
    window.addEventListener("storage", read);
    return () => {
      window.removeEventListener("hiwaloy:profile-changed", read);
      window.removeEventListener("storage", read);
    };
  }, [pathname]);

  if (!profile) {
    return (
      <Link
        href="/onboarding"
        className="flex items-center gap-3 rounded-card border border-border bg-panel-elev px-3 py-2.5 transition hover:border-border-strong"
      >
        <span className="grid h-9 w-9 place-items-center rounded-full bg-brand-soft text-brand">
          <User2 size={16} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-foreground">
            Profil oluştur
          </p>
          <p className="truncate text-xs text-subtle-foreground">
            Ölçülerini ekle
          </p>
        </div>
      </Link>
    );
  }

  return (
    <Link
      href="/onboarding"
      className="flex items-center gap-3 rounded-card border border-border bg-panel-elev px-3 py-2.5 transition hover:border-border-strong"
    >
      <span className="grid h-9 w-9 place-items-center rounded-full bg-brand-soft text-brand">
        <User2 size={16} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-foreground">
          {profile.height ? `${profile.height} cm` : "Profil"}{" "}
          {profile.weight ? `· ${profile.weight} kg` : ""}
        </p>
        <p className="truncate text-xs text-subtle-foreground capitalize">
          {profile.fit ?? "—"}
        </p>
      </div>
    </Link>
  );
}

export function Sidebar() {
  const pathname = usePathname() ?? "/";

  return (
    <aside className="sticky top-0 hidden h-dvh w-[240px] shrink-0 flex-col border-r border-border bg-panel/60 px-4 py-6 backdrop-blur-xl lg:flex">
      {/* Brand */}
      <Link href="/" className="mb-8 px-2">
        <p className="text-xl font-semibold tracking-tight text-foreground">
          HIWALOY
        </p>
        <p className="mt-0.5 text-[11px] leading-tight text-subtle-foreground">
          How It Will ACTUALLY
          <br />
          Look On You
        </p>
      </Link>

      <div className="mb-2 h-px bg-border" />

      {/* Nav */}
      <nav className="flex flex-col gap-1">
        {items.map((item) => {
          const Icon = item.icon;
          const active =
            pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={[
                "group flex items-center gap-3 rounded-md px-3 py-2.5 text-sm transition",
                active
                  ? "bg-brand-soft text-foreground"
                  : "text-muted-foreground hover:bg-panel-elev hover:text-foreground",
              ].join(" ")}
            >
              <span
                className={[
                  "grid h-7 w-7 place-items-center rounded-md",
                  active
                    ? "bg-brand/20 text-brand"
                    : "bg-panel-elev text-muted-foreground group-hover:text-foreground",
                ].join(" ")}
              >
                <Icon size={14} />
              </span>
              <span className="font-medium">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Mode badge (DEMO / Canlı AI, driven by /api/v1/health) */}
      <ModeBadge />

      {/* Profile chip */}
      <ProfileChip />
    </aside>
  );
}
