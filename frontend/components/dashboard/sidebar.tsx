"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { signOut, useSession } from "next-auth/react";
import { Sparkles, History, User2, Wand2, Home, LogOut } from "lucide-react";
import { apiFetch } from "@/lib/api";

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
      .then((data) =>
        setDemoMode(data && typeof data.demo_mode === "boolean" ? data.demo_mode : false),
      )
      .catch(() => setDemoMode(false));
  }, []);

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
  const { data: session } = useSession();
  const [profile, setProfile] = useState<
    { height?: number; weight?: number; fit?: string } | null
  >(null);

  // Refresh whenever pathname changes (route navigation) OR the onboarding
  // page fires hiwaloy:profile-changed after a save.
  useEffect(() => {
    if (!session?.user) return;

    let cancelled = false;
    async function refresh() {
      try {
        const r = await apiFetch("/api/v1/profile/me");
        if (cancelled) return;
        if (!r.ok) {
          setProfile(null);
          return;
        }
        const data = await r.json();
        setProfile({
          height: data.height_cm,
          weight: data.weight_kg,
          fit: data.fit_preference,
        });
      } catch {
        if (!cancelled) setProfile(null);
      }
    }
    refresh();

    window.addEventListener("hiwaloy:profile-changed", refresh);
    return () => {
      cancelled = true;
      window.removeEventListener("hiwaloy:profile-changed", refresh);
    };
  }, [pathname, session]);

  if (!session?.user) return null;

  const displayName = session.user.name || session.user.email || "Hesabım";

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
          {displayName}
        </p>
        <p className="truncate text-xs text-subtle-foreground">
          {profile
            ? `${profile.height} cm · ${profile.weight} kg`
            : "Profil oluştur"}
        </p>
      </div>
    </Link>
  );
}

export function Sidebar() {
  const pathname = usePathname() ?? "/";

  return (
    <aside className="sticky top-0 hidden h-dvh w-[240px] shrink-0 flex-col border-r border-border bg-panel/60 px-4 py-6 backdrop-blur-xl lg:flex">
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

      <div className="flex-1" />

      <ModeBadge />
      <ProfileChip />

      <button
        type="button"
        onClick={() => signOut({ callbackUrl: "/login" })}
        className="mt-2 inline-flex items-center justify-center gap-2 rounded-md px-3 py-2 text-xs font-medium text-subtle-foreground transition hover:text-foreground"
      >
        <LogOut size={12} /> Çıkış Yap
      </button>
    </aside>
  );
}
