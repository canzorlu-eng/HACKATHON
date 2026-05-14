"use client";

import { Suspense, useEffect, useState } from "react";
import { signIn, useSession } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { User2, Shirt, ShieldCheck, Check } from "lucide-react";

// ─────────────────────────────────────────────────────────────────────────────
// Login page — two-column marketing + auth card. signIn() flow unchanged.
// ─────────────────────────────────────────────────────────────────────────────

function LoginContent() {
  const router = useRouter();
  const params = useSearchParams();
  const { status } = useSession();
  const [busy, setBusy] = useState(false);

  const callbackUrl = params?.get("callbackUrl") ?? "/";

  useEffect(() => {
    if (status === "authenticated") router.replace(callbackUrl);
  }, [status, callbackUrl, router]);

  async function handleGoogle() {
    setBusy(true);
    await signIn("google", { callbackUrl });
  }

  return (
    <div className="grid min-h-dvh grid-cols-1 lg:grid-cols-2">
      <BrandPanel />
      <AuthPanel busy={busy} onGoogle={handleGoogle} />
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginContent />
    </Suspense>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Left column — marketing
// ─────────────────────────────────────────────────────────────────────────────

const FEATURES = [
  {
    icon: User2,
    title: "Vücut Analizi",
    body: "Fotoğraflarını analiz ederek vücut tipini ve ölçülerini doğru tahmin eder.",
  },
  {
    icon: Shirt,
    title: "Ürün & Kalıp Analizi",
    body: "Kalıp, esneklik, kumaş yapısı ve kesimi detaylı olarak değerlendirir.",
  },
  {
    icon: ShieldCheck,
    title: "Risk & Uyum Tahmini",
    body: "Satın alma riskini azaltır, sana en uygun bedeni güvenle önerir.",
  },
];

function BrandPanel() {
  return (
    <div className="relative flex flex-col justify-between overflow-hidden px-8 py-10 lg:px-16 lg:py-14">
      {/* subtle backdrop glows */}
      <div
        aria-hidden
        className="pointer-events-none absolute -left-32 top-10 h-72 w-72 rounded-full bg-brand/15 blur-3xl"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -bottom-32 left-1/3 h-96 w-96 rounded-full bg-brand2/15 blur-3xl"
      />

      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55 }}
        className="relative z-10"
      >
        {/* Wordmark + tagline */}
        <p className="text-2xl font-semibold tracking-[0.18em] text-foreground">
          HIWA<span className="brand-text">LOY</span>
        </p>
        <p className="mt-2 text-sm text-subtle-foreground">
          AI ile size özel beden &amp; uyum analizi.
        </p>

        {/* Hero headline */}
        <h1 className="mt-14 max-w-xl text-4xl font-semibold leading-[1.1] tracking-tight sm:text-5xl">
          Vücudunu anlar,
          <br />
          <span className="brand-text">sana en uygun</span>
          <br />
          <span className="brand-text">kombini önerir.</span>
        </h1>

        {/* Feature rows */}
        <ul className="mt-10 flex max-w-md flex-col gap-5">
          {FEATURES.map((f) => {
            const Icon = f.icon;
            return (
              <li key={f.title} className="flex items-start gap-4">
                <span className="grid h-11 w-11 shrink-0 place-items-center rounded-card border border-brand/30 bg-brand-soft text-brand">
                  <Icon size={18} />
                </span>
                <div>
                  <p className="text-sm font-semibold text-foreground">{f.title}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-subtle-foreground">
                    {f.body}
                  </p>
                </div>
              </li>
            );
          })}
        </ul>
      </motion.div>

      {/* Visual — mannequin on lit platform */}
      <MannequinStage />
    </div>
  );
}

function MannequinStage() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, delay: 0.15 }}
      className="relative mt-10 hidden h-72 w-full max-w-xl items-end justify-center lg:flex"
      aria-hidden
    >
      {/* T-shirt off to the side */}
      <svg
        viewBox="0 0 140 130"
        className="absolute bottom-12 left-2 h-40 w-40 -rotate-6"
      >
        <defs>
          <linearGradient id="tee-grad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="hsl(240 12% 14%)" />
            <stop offset="100%" stopColor="hsl(240 14% 6%)" />
          </linearGradient>
        </defs>
        <path
          d="M30 25 L55 12 Q70 22 85 12 L110 25 L125 42 L108 50 L108 110 Q108 118 100 118 L40 118 Q32 118 32 110 L32 50 L15 42 Z"
          fill="url(#tee-grad)"
          stroke="hsl(240 8% 22%)"
          strokeWidth="0.8"
        />
      </svg>

      {/* Wireframe mannequin */}
      <svg viewBox="0 0 200 240" className="relative z-10 h-full">
        <defs>
          <linearGradient id="mq-stroke-login" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="hsl(0 0% 98%)" stopOpacity="0.65" />
            <stop offset="100%" stopColor="hsl(0 0% 98%)" stopOpacity="0.2" />
          </linearGradient>
        </defs>
        {/* head */}
        <circle cx="100" cy="36" r="22" fill="none" stroke="url(#mq-stroke-login)" strokeWidth="1" />
        <ellipse cx="100" cy="36" rx="22" ry="8" fill="none" stroke="url(#mq-stroke-login)" strokeWidth="0.6" opacity="0.6" />
        <ellipse cx="100" cy="36" rx="8" ry="22" fill="none" stroke="url(#mq-stroke-login)" strokeWidth="0.6" opacity="0.6" />
        {/* neck */}
        <path d="M91 56 L109 56 L110 68 L90 68 Z" fill="none" stroke="url(#mq-stroke-login)" strokeWidth="0.8" />
        {/* torso */}
        <path
          d="M58 80 Q72 66 92 66 L108 66 Q128 66 142 80 L148 138 Q148 150 138 158 L62 158 Q52 150 52 138 Z"
          fill="none"
          stroke="url(#mq-stroke-login)"
          strokeWidth="0.9"
        />
        {/* shirt grid */}
        <g stroke="hsl(267 95% 75%)" strokeOpacity="0.22" strokeWidth="0.4" fill="none">
          <path d="M58 95 Q100 100 142 95" />
          <path d="M55 118 Q100 125 145 118" />
          <path d="M53 145 Q100 152 147 145" />
        </g>
        <line x1="100" y1="66" x2="100" y2="158" stroke="hsl(267 95% 75%)" strokeOpacity="0.25" strokeWidth="0.5" />
        {/* arms */}
        <path d="M58 80 L44 118 L52 156 L62 158" fill="none" stroke="url(#mq-stroke-login)" strokeWidth="0.9" />
        <path d="M142 80 L156 118 L148 156 L138 158" fill="none" stroke="url(#mq-stroke-login)" strokeWidth="0.9" />
        {/* legs */}
        <path d="M62 158 L74 220" fill="none" stroke="url(#mq-stroke-login)" strokeWidth="0.9" />
        <path d="M138 158 L126 220" fill="none" stroke="url(#mq-stroke-login)" strokeWidth="0.9" />
      </svg>

      {/* Fit score card */}
      <div className="absolute right-2 bottom-20 rounded-card border border-border bg-panel/90 px-3 py-2 text-[10px] shadow-[0_10px_30px_-12px_rgba(0,0,0,0.6)] backdrop-blur">
        <p className="text-subtle-foreground">Uyum Skoru</p>
        <p className="text-lg font-bold brand-text">%87</p>
        <svg viewBox="0 0 60 18" className="mt-1 h-3 w-16">
          <polyline
            points="2,14 12,10 22,12 32,6 42,8 52,3 58,5"
            fill="none"
            stroke="hsl(152 70% 50%)"
            strokeWidth="1.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>

      {/* Lit platform */}
      <div className="absolute bottom-2 left-1/2 h-3 w-56 -translate-x-1/2 rounded-full bg-brand/90 shadow-[0_0_60px_18px_hsl(var(--brand)/0.55)]" />
      <div className="absolute bottom-0 left-1/2 h-5 w-72 -translate-x-1/2 rounded-full bg-gradient-to-r from-transparent via-brand/60 to-transparent blur-md" />
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Right column — auth card
// ─────────────────────────────────────────────────────────────────────────────

function AuthPanel({
  busy,
  onGoogle,
}: {
  busy: boolean;
  onGoogle: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-between px-6 py-10 lg:py-14">
      <div className="flex-1" />

      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="panel relative w-full max-w-md rounded-card border-border/60 p-8 sm:p-10"
      >
        {/* H logo tile */}
        <div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl border border-brand/40 bg-brand-soft text-3xl font-bold brand-text brand-glow">
          H
        </div>

        <h2 className="mt-7 text-center text-3xl font-semibold tracking-tight text-foreground">
          Tekrar hoş geldin!
        </h2>
        <p className="mt-2 text-center text-sm text-muted-foreground">
          Devam etmek için hesabınla giriş yap.
        </p>

        <button
          type="button"
          onClick={onGoogle}
          disabled={busy}
          className="mt-8 flex w-full items-center justify-center gap-3 rounded-pill border border-border bg-white px-5 py-3.5 text-sm font-semibold text-slate-900 shadow-[0_10px_40px_-12px_hsl(var(--brand)/0.55)] transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <GoogleMark />
          {busy ? "Yönlendiriliyor…" : "Google ile devam et"}
        </button>

        {/* veya divider */}
        <div className="my-7 flex items-center gap-3 text-xs text-subtle-foreground">
          <span className="h-px flex-1 bg-border" />
          veya
          <span className="h-px flex-1 bg-border" />
        </div>

        {/* Benefits */}
        <ul className="flex flex-col gap-3">
          {[
            "Giriş yapmak ücretsizdir.",
            "Bilgilerin güvenle korunur.",
            "Dilediğin zaman çıkış yapabilirsin.",
          ].map((line) => (
            <li
              key={line}
              className="flex items-center gap-3 text-sm text-foreground/90"
            >
              <span className="grid h-5 w-5 place-items-center rounded-full border border-brand/40 text-brand">
                <Check size={12} />
              </span>
              {line}
            </li>
          ))}
        </ul>

        {/* Terms */}
        <p className="mt-8 text-center text-xs leading-relaxed text-subtle-foreground">
          Devam ederek{" "}
          <span className="text-brand">Kullanım Koşulları</span> ve{" "}
          <span className="text-brand">Gizlilik Politikası</span>&apos;nı
          kabul etmiş olursun.
        </p>
      </motion.div>

      <div className="flex-1" />

      <p className="mt-8 text-center text-xs text-subtle-foreground">
        © 2026 HIWALOY. Tüm hakları saklıdır.
      </p>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Google brand mark
// ─────────────────────────────────────────────────────────────────────────────

function GoogleMark() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden>
      <path fill="#EA4335" d="M12 10.2v3.9h5.5c-.2 1.3-1.7 3.8-5.5 3.8-3.3 0-6-2.7-6-6s2.7-6 6-6c1.9 0 3.1.8 3.8 1.5l2.6-2.5C16.7 3.2 14.5 2.2 12 2.2 6.5 2.2 2 6.7 2 12.2s4.5 10 10 10c5.8 0 9.6-4.1 9.6-9.8 0-.7-.1-1.2-.2-1.8H12z" />
      <path fill="#34A853" d="M3.6 7.5l3.2 2.4c.9-1.7 2.7-3 4.8-3 1.3 0 2.4.5 3.2 1.2l2.4-2.4C15.5 4 13.9 3.3 12 3.3 8.4 3.3 5.3 5 3.6 7.5z" />
      <path fill="#FBBC05" d="M12 21.8c2.4 0 4.5-.8 6-2.2l-2.9-2.4c-.8.6-1.9 1-3.1 1-2.4 0-4.5-1.6-5.2-3.8l-3.1 2.4C5.1 19.6 8.2 21.8 12 21.8z" />
      <path fill="#4285F4" d="M21.6 12.2c0-.7-.1-1.4-.2-2H12v4h5.4c-.2 1.2-1 2.2-2.1 2.9l3 2.4c1.7-1.6 2.7-3.9 2.7-7.3z" />
    </svg>
  );
}
