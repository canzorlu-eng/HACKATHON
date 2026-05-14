"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ArrowUpRight, Shirt, MessageSquare, ShieldCheck } from "lucide-react";
import { MannequinHero } from "@/components/dashboard/mannequin";
import { apiFetch } from "@/lib/api";

interface HistoryItem {
  analysis_id: string;
  created_at: string;
  garment_image_ref: string;
  recommended_size: string | null;
  risk_level: "low" | "medium" | "high" | null;
}

const RISK_PILL: Record<string, string> = {
  low: "text-success bg-success/10 border-success/30",
  medium: "text-warning bg-warning/10 border-warning/30",
  high: "text-danger bg-danger/10 border-danger/30",
};

const RISK_LABEL: Record<string, string> = {
  low: "Düşük Risk",
  medium: "Orta Risk",
  high: "Yüksek Risk",
};

export default function HomePage() {
  const [items, setItems] = useState<HistoryItem[] | null>(null);
  const [hasProfile, setHasProfile] = useState<boolean>(false);

  useEffect(() => {
    // Authenticated by middleware; probe /profile/me to learn if onboarding
    // is needed, then fetch the latest 4 analyses if a profile exists.
    apiFetch("/api/v1/profile/me")
      .then((r) => setHasProfile(r.ok))
      .catch(() => setHasProfile(false));

    apiFetch("/api/v1/history")
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((data) => setItems((data.items ?? []).slice(0, 4)))
      .catch(() => setItems([]));
  }, []);

  return (
    <div className="flex flex-col gap-12 pt-2">
      {/* Hero ----------------------------------------------------------- */}
      <section className="grid grid-cols-1 items-center gap-10 lg:grid-cols-[1.05fr_1fr]">
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <span className="inline-flex items-center gap-2 rounded-pill border border-brand/30 bg-brand-soft px-3 py-1 text-xs font-medium text-brand">
            <span className="h-1.5 w-1.5 rounded-full bg-brand" />
            AI destekli beden ve uyum analizi
          </span>

          <h1 className="mt-6 text-4xl font-semibold leading-[1.1] tracking-tight sm:text-5xl">
            AI ile sana özel
            <br />
            <span className="brand-text">beden &amp; uyum analizi.</span>
          </h1>

          <p className="mt-5 max-w-xl text-base leading-relaxed text-muted-foreground">
            Bir kıyafetin sana nasıl{" "}
            <span className="font-medium text-foreground">DURACAĞINI</span> değil,
            nasıl{" "}
            <span className="font-medium text-foreground">OTURACAĞINI</span>{" "}
            söylüyoruz.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link
              href={hasProfile ? "/analyze" : "/onboarding"}
              className="inline-flex items-center gap-2 rounded-pill bg-brand-gradient px-5 py-3 text-sm font-semibold text-white brand-glow transition hover:brightness-110"
            >
              <span className="grid h-6 w-6 place-items-center rounded-full bg-white/15">
                +
              </span>
              Yeni Analiz Başlat
            </Link>
          </div>
        </motion.div>

        <div className="relative">
          <MannequinHero />
        </div>
      </section>

      {/* Recent analyses ------------------------------------------------ */}
      <section>
        <div className="mb-4 flex items-end justify-between">
          <div>
            <h2 className="text-xl font-semibold text-foreground">
              Son Analiz Sonuçların
            </h2>
            <p className="mt-1 text-sm text-subtle-foreground">
              Yaptığın analizleri buradan tekrar görüntüleyebilirsin.
            </p>
          </div>
          <Link
            href="/history"
            className="inline-flex items-center gap-1 text-sm text-muted-foreground transition hover:text-foreground"
          >
            Tümünü Gör <ArrowUpRight size={14} />
          </Link>
        </div>

        {!hasProfile ? (
          <EmptyState
            title="Henüz profilin yok"
            body="Beden öneri sistemi için önce boy, kilo ve fit tercihini eklemen gerekiyor."
            cta="Profil Oluştur"
            href="/onboarding"
          />
        ) : items === null ? (
          <div className="panel p-6 text-sm text-subtle-foreground">
            Yükleniyor…
          </div>
        ) : items.length === 0 ? (
          <EmptyState
            title="Hiç analizin yok"
            body="İlk kıyafet analizini yaparak başlayabilirsin."
            cta="Yeni Analiz"
            href="/analyze"
          />
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {items.map((item) => (
              <AnalysisPreviewCard key={item.analysis_id} item={item} />
            ))}
          </div>
        )}
      </section>

      {/* How it works --------------------------------------------------- */}
      <section id="how-it-works">
        <h2 className="mb-4 text-xl font-semibold text-foreground">
          HIWALOY Nasıl Çalışır?
        </h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Feature
            icon={Shirt}
            title="Kıyafet ve vücut görselini analiz eder"
            body="Yüklediğin görselden kesim, kumaş ve marka kalıbını çıkarır; profilindeki ölçülerle birlikte değerlendirir."
          />
          <Feature
            icon={MessageSquare}
            title="Benzer kullanıcı yorumlarına bakar"
            body="Topluluk yorumlarından sizing ve fit sorunlarını çıkararak senin için bağlamlandırır."
          />
          <Feature
            icon={ShieldCheck}
            title="Açıklanabilir öneri ve risk"
            body="Beden önerisini, güven skorunu ve satın alma riskini gerekçeleriyle birlikte sunar."
          />
        </div>
      </section>
    </div>
  );
}

// ----- subcomponents -----

function AnalysisPreviewCard({ item }: { item: HistoryItem }) {
  const date = new Date(item.created_at).toLocaleDateString("tr-TR", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
  const riskClass = item.risk_level ? RISK_PILL[item.risk_level] : "";
  const riskLabel = item.risk_level ? RISK_LABEL[item.risk_level] : null;

  return (
    <Link
      href={`/history/${item.analysis_id}`}
      className="group panel flex flex-col gap-3 p-4 transition hover:border-border-strong"
    >
      <div className="flex items-center gap-3">
        <div className="grid h-12 w-12 place-items-center rounded-card bg-brand-soft text-lg font-bold text-brand">
          {item.recommended_size ?? "—"}
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-foreground">
            Analiz {item.analysis_id.slice(0, 8)}
          </p>
          <p className="text-xs text-subtle-foreground">{date}</p>
        </div>
      </div>
      <div className="flex items-center justify-between">
        {riskLabel ? (
          <span
            className={`inline-flex items-center rounded-pill border px-2.5 py-0.5 text-xs font-medium ${riskClass}`}
          >
            {riskLabel}
          </span>
        ) : (
          <span className="text-xs text-subtle-foreground">—</span>
        )}
        <ArrowUpRight
          size={14}
          className="text-subtle-foreground transition group-hover:text-foreground"
        />
      </div>
    </Link>
  );
}

function EmptyState({
  title,
  body,
  cta,
  href,
}: {
  title: string;
  body: string;
  cta: string;
  href: string;
}) {
  return (
    <div className="panel flex flex-col items-start gap-3 p-6">
      <h3 className="text-base font-semibold text-foreground">{title}</h3>
      <p className="max-w-prose text-sm text-muted-foreground">{body}</p>
      <Link
        href={href}
        className="mt-1 inline-flex items-center gap-2 rounded-pill bg-brand-gradient px-4 py-2 text-xs font-semibold text-white transition hover:brightness-110"
      >
        {cta} <ArrowUpRight size={12} />
      </Link>
    </div>
  );
}

function Feature({
  icon: Icon,
  title,
  body,
}: {
  icon: typeof Shirt;
  title: string;
  body: string;
}) {
  return (
    <div className="panel p-5">
      <span className="mb-3 grid h-9 w-9 place-items-center rounded-md bg-brand-soft text-brand">
        <Icon size={16} />
      </span>
      <p className="text-sm font-semibold text-foreground">{title}</p>
      <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
        {body}
      </p>
    </div>
  );
}
