"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, RefreshCw } from "lucide-react";
import { HistoryCard, type HistoryItem } from "@/components/history-card";

interface HistoryListResponse {
  items: HistoryItem[];
  total: number;
}

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Status =
  | { type: "no-profile" }
  | { type: "loading" }
  | { type: "error" }
  | { type: "empty" }
  | { type: "ready"; items: HistoryItem[]; total: number };

export default function HistoryPage() {
  const [status, setStatus] = useState<Status>({ type: "loading" });

  async function load() {
    setStatus({ type: "loading" });

    const userId =
      typeof window !== "undefined"
        ? localStorage.getItem("hiwaloy_user_id")
        : null;

    if (!userId) {
      setStatus({ type: "no-profile" });
      return;
    }

    try {
      const res = await fetch(`${BASE}/api/v1/history/${userId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: HistoryListResponse = await res.json();

      if (!data.items || data.items.length === 0) setStatus({ type: "empty" });
      else setStatus({ type: "ready", items: data.items, total: data.total });
    } catch {
      setStatus({ type: "error" });
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex flex-col gap-6 pt-2">
      <header className="flex items-end justify-between">
        <div>
          <span className="inline-flex rounded-pill border border-brand/30 bg-brand-soft px-3 py-1 text-[11px] font-medium text-brand">
            Geçmiş
          </span>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-foreground">
            Geçmiş Analizler
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Tüm analizlerin burada saklanır.
          </p>
        </div>
        <Link
          href="/analyze"
          className="inline-flex items-center gap-2 rounded-pill bg-brand-gradient px-4 py-2 text-xs font-semibold text-white transition hover:brightness-110"
        >
          Yeni Analiz <ArrowRight size={12} />
        </Link>
      </header>

      {status.type === "loading" && (
        <div className="panel p-6 text-sm text-subtle-foreground">
          Yükleniyor…
        </div>
      )}

      {status.type === "no-profile" && (
        <div className="panel flex flex-col items-start gap-3 p-6">
          <p className="text-sm text-muted-foreground">
            Önce profilini oluştur.
          </p>
          <Link
            href="/onboarding"
            className="inline-flex items-center gap-2 rounded-pill bg-brand-gradient px-4 py-2 text-xs font-semibold text-white transition hover:brightness-110"
          >
            Profil Oluştur <ArrowRight size={12} />
          </Link>
        </div>
      )}

      {status.type === "error" && (
        <div className="panel flex flex-col items-start gap-3 p-6">
          <p className="text-sm text-muted-foreground">
            Geçmiş yüklenirken hata oluştu.
          </p>
          <button
            onClick={load}
            className="inline-flex items-center gap-2 rounded-pill border border-border bg-panel-elev px-4 py-2 text-xs font-medium text-foreground transition hover:border-border-strong"
          >
            <RefreshCw size={12} /> Tekrar Dene
          </button>
        </div>
      )}

      {status.type === "empty" && (
        <div className="panel flex flex-col items-start gap-3 p-6">
          <p className="text-sm text-muted-foreground">
            Henüz analiz yapılmamış.
          </p>
          <Link
            href="/analyze"
            className="inline-flex items-center gap-2 rounded-pill bg-brand-gradient px-4 py-2 text-xs font-semibold text-white transition hover:brightness-110"
          >
            Yeni Analiz <ArrowRight size={12} />
          </Link>
        </div>
      )}

      {status.type === "ready" && (
        <>
          <p className="text-sm text-subtle-foreground">
            Toplam {status.total} analiz
          </p>
          <div className="flex flex-col gap-3">
            {status.items.map((item, index) => (
              <HistoryCard key={item.analysis_id} item={item} index={index} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
