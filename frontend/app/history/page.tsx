"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
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

      if (!data.items || data.items.length === 0) {
        setStatus({ type: "empty" });
      } else {
        setStatus({ type: "ready", items: data.items, total: data.total });
      }
    } catch {
      setStatus({ type: "error" });
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main className="min-h-screen py-12 px-4">
      <div className="mx-auto w-full max-w-[560px]">
        <h1 className="text-2xl font-semibold tracking-tight mb-1">
          Geçmiş Analizler
        </h1>

        {status.type === "loading" && (
          <p className="mt-8 text-muted-foreground text-sm">Yükleniyor…</p>
        )}

        {status.type === "no-profile" && (
          <div className="mt-8 flex flex-col gap-4">
            <p className="text-sm text-muted-foreground">
              Önce profilinizi oluşturmanız gerekiyor.
            </p>
            <Link
              href="/onboarding"
              className="inline-flex items-center justify-center rounded-lg bg-foreground text-background px-4 py-2 text-sm font-medium w-fit hover:opacity-90 transition-opacity"
            >
              Profil Oluştur
            </Link>
          </div>
        )}

        {status.type === "error" && (
          <div className="mt-8 flex flex-col gap-4">
            <p className="text-sm text-muted-foreground">
              Geçmiş yüklenirken hata oluştu.
            </p>
            <button
              onClick={load}
              className="inline-flex items-center justify-center rounded-lg bg-foreground text-background px-4 py-2 text-sm font-medium w-fit hover:opacity-90 transition-opacity"
            >
              Tekrar Dene
            </button>
          </div>
        )}

        {status.type === "empty" && (
          <div className="mt-8 flex flex-col gap-4">
            <p className="text-sm text-muted-foreground">
              Henüz analiz yapılmamış.
            </p>
            <Link
              href="/analyze"
              className="inline-flex items-center justify-center rounded-lg bg-foreground text-background px-4 py-2 text-sm font-medium w-fit hover:opacity-90 transition-opacity"
            >
              Yeni Analiz Başlat
            </Link>
          </div>
        )}

        {status.type === "ready" && (
          <>
            <p className="text-sm text-muted-foreground mb-6">
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
    </main>
  );
}
