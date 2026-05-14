"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { MessageSquare } from "lucide-react";

interface FormattedResponse {
  recommended_size?: string | null;
  confidence_score?: number | null;
  confidence_pct?: string | null;
  explanation_tr?: string | null;
  uncertainty_tr?: string | null;
  risk_level?: string | null;
  risk_level_tr?: string | null;
  risk_factors_tr?: string[] | null;
  community_insights_tr?: string[] | null;
}

interface AnalysisDetail {
  analysis_id: string;
  recommended_size: string | null;
  risk_level: "low" | "medium" | "high" | null;
  formatted_response: FormattedResponse | null;
  created_at: string;
}

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const RISK_CLASS: Record<string, string> = {
  low: "bg-green-100 text-green-700",
  medium: "bg-amber-100 text-amber-700",
  high: "bg-red-100 text-red-700",
};

function confidenceColor(score: number): string {
  const pct = score * 100;
  if (pct > 70) return "bg-green-500";
  if (pct >= 50) return "bg-amber-400";
  return "bg-red-500";
}

export default function HistoryDetailPage() {
  const params = useParams();
  const router = useRouter();
  const analysisId = params.id as string;

  const [detail, setDetail] = useState<AnalysisDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const userId = localStorage.getItem("hiwaloy_user_id");
    if (!userId) {
      router.replace("/onboarding");
      return;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000);

    fetch(`${BASE}/api/v1/history/${userId}/${analysisId}`, { signal: controller.signal })
      .then((res) => {
        clearTimeout(timeoutId);
        if (res.status === 404) throw new Error("not_found");
        if (!res.ok) throw new Error("server_error");
        return res.json();
      })
      .then((data: AnalysisDetail) => setDetail(data))
      .catch((err) => {
        clearTimeout(timeoutId);
        if (err instanceof Error && err.name === "AbortError") {
          setError("Bağlantı zaman aşımına uğradı.");
        } else if (err instanceof Error && err.message === "not_found") {
          setError("Bu analiz kaydı bulunamadı.");
        } else {
          setError("Analiz detayı yüklenemedi.");
        }
      });

    return () => { clearTimeout(timeoutId); controller.abort(); };
  }, [analysisId, router]);

  if (error) {
    return (
      <main className="min-h-dvh py-12 px-4">
        <div className="mx-auto w-full max-w-[600px] text-center">
          <p className="text-sm text-muted-foreground">{error}</p>
          <button
            onClick={() => router.back()}
            className="mt-4 rounded-lg bg-foreground px-4 py-2 text-sm font-medium text-background hover:opacity-80 transition-opacity"
          >
            Geri Dön
          </button>
        </div>
      </main>
    );
  }

  if (!detail) {
    return (
      <main className="min-h-dvh py-12 px-4">
        <div className="mx-auto w-full max-w-[600px]">
          <p className="text-sm text-muted-foreground">Yükleniyor…</p>
        </div>
      </main>
    );
  }

  const fr = detail.formatted_response ?? {};
  const score = fr.confidence_score ?? 0;
  const riskFactors = fr.risk_factors_tr ?? [];
  const insights = fr.community_insights_tr ?? [];
  const formattedDate = new Date(detail.created_at).toLocaleDateString("tr-TR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  return (
    <main className="min-h-dvh py-12 px-4">
      <div className="mx-auto w-full max-w-[600px] flex flex-col gap-6">
        {/* Header */}
        <div>
          <button
            onClick={() => router.back()}
            className="mb-4 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            ← Geçmişe Dön
          </button>
          <h1 className="text-2xl font-semibold tracking-tight">
            Analiz Detayı
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">{formattedDate}</p>
        </div>

        {/* Recommendation */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="rounded-xl border border-border bg-background p-5 shadow-sm"
        >
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Beden Önerisi
          </p>
          <div className="flex flex-col items-center gap-1 py-2">
            <span className="text-4xl font-bold text-foreground">
              {fr.recommended_size ?? detail.recommended_size ?? "—"}
            </span>
            <span className="text-sm text-muted-foreground">
              Güven: {fr.confidence_pct ?? "—"}
            </span>
          </div>
          {fr.explanation_tr && (
            <p className="mt-3 text-sm text-muted-foreground leading-relaxed">
              <span className="mr-1 font-medium text-foreground">Açıklama:</span>
              {fr.explanation_tr}
            </p>
          )}
          {fr.uncertainty_tr && (
            <p className="mt-2 text-xs text-muted-foreground/70 italic leading-relaxed">
              {fr.uncertainty_tr}
            </p>
          )}
        </motion.div>

        {/* Confidence bar */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.05 }}
          className="rounded-xl border border-border bg-background p-5 shadow-sm"
        >
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Güven Skoru
          </p>
          <div className="flex items-center gap-3">
            <div className="relative h-2.5 flex-1 overflow-hidden rounded-full bg-muted">
              <motion.div
                className={`h-full rounded-full ${confidenceColor(score)}`}
                initial={{ width: 0 }}
                animate={{ width: `${Math.round(score * 100)}%` }}
                transition={{ duration: 0.7, ease: "easeOut" }}
              />
            </div>
            <span className="w-10 text-right text-sm font-medium text-foreground">
              {fr.confidence_pct ?? "—"}
            </span>
          </div>
        </motion.div>

        {/* Risk panel */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
          className="rounded-xl border border-border bg-background p-5 shadow-sm"
        >
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Risk Değerlendirmesi
          </p>
          {detail.risk_level && (
            <span
              className={`inline-block rounded-full px-3 py-0.5 text-xs font-semibold ${
                RISK_CLASS[detail.risk_level] ?? "bg-muted text-muted-foreground"
              }`}
            >
              {fr.risk_level_tr ?? detail.risk_level}
            </span>
          )}
          {riskFactors.length > 0 && (
            <ul className="mt-4 flex flex-col gap-2">
              {riskFactors.map((factor, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-muted-foreground/50" />
                  {factor}
                </li>
              ))}
            </ul>
          )}
        </motion.div>

        {/* Community insights */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.15 }}
          className="rounded-xl border border-border bg-background p-5 shadow-sm"
        >
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Topluluk Yorumları
          </p>
          {insights.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Yeterli kullanıcı yorumu bulunmuyor.
            </p>
          ) : (
            <ul className="flex flex-col gap-3">
              {insights.map((insight, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                  <MessageSquare className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground/50" />
                  {insight}
                </li>
              ))}
            </ul>
          )}
        </motion.div>
      </div>
    </main>
  );
}
