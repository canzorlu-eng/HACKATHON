"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { MessageSquare, ArrowLeft, AlertTriangle, ShieldCheck } from "lucide-react";
import { apiFetch } from "@/lib/api";

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

const RISK_PILL: Record<string, string> = {
  low: "text-success bg-success/10 border-success/30",
  medium: "text-warning bg-warning/10 border-warning/30",
  high: "text-danger bg-danger/10 border-danger/30",
};

function confidenceColor(score: number): string {
  const pct = score * 100;
  if (pct > 70) return "bg-success";
  if (pct >= 50) return "bg-warning";
  return "bg-danger";
}

export default function HistoryDetailPage() {
  const params = useParams();
  const router = useRouter();
  const analysisId = params.id as string;

  const [detail, setDetail] = useState<AnalysisDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000);

    apiFetch(`/api/v1/history/${analysisId}`, { signal: controller.signal })
      .then((res) => {
        clearTimeout(timeoutId);
        if (res.status === 404) throw new Error("not_found");
        if (!res.ok) throw new Error("server_error");
        return res.json();
      })
      .then((data: AnalysisDetail) => setDetail(data))
      .catch((err) => {
        clearTimeout(timeoutId);
        if (err instanceof Error && err.name === "AbortError")
          setError("Bağlantı zaman aşımına uğradı.");
        else if (err instanceof Error && err.message === "not_found")
          setError("Bu analiz kaydı bulunamadı.");
        else setError("Analiz detayı yüklenemedi.");
      });

    return () => {
      clearTimeout(timeoutId);
      controller.abort();
    };
  }, [analysisId, router]);

  if (error) {
    return (
      <div className="panel flex flex-col items-start gap-3 p-6">
        <p className="text-sm text-muted-foreground">{error}</p>
        <button
          onClick={() => router.back()}
          className="inline-flex items-center gap-2 rounded-pill bg-brand-gradient px-4 py-2 text-xs font-semibold text-white transition hover:brightness-110"
        >
          <ArrowLeft size={12} /> Geri Dön
        </button>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="panel p-6 text-sm text-subtle-foreground">
        Yükleniyor…
      </div>
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
  const riskPill = detail.risk_level ? RISK_PILL[detail.risk_level] : "";

  return (
    <div className="flex flex-col gap-6 pt-2">
      <header>
        <button
          onClick={() => router.back()}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground transition hover:text-foreground"
        >
          <ArrowLeft size={12} /> Geçmişe Dön
        </button>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-foreground">
          Analiz Detayı
        </h1>
        <p className="mt-1 text-sm text-subtle-foreground">{formattedDate}</p>
      </header>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1.15fr_1fr]">
        {/* Recommendation */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="panel flex flex-col gap-5 p-6"
        >
          <div className="flex items-end justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-subtle-foreground">
                Beden Önerisi
              </p>
              <p className="mt-2 text-6xl font-bold text-foreground">
                {fr.recommended_size ?? detail.recommended_size ?? "—"}
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs font-semibold uppercase tracking-wider text-subtle-foreground">
                Güven Skoru
              </p>
              <p className="mt-2 text-3xl font-bold brand-text">
                {fr.confidence_pct ?? "—"}
              </p>
            </div>
          </div>

          <div className="h-2 overflow-hidden rounded-full bg-panel-elev">
            <motion.div
              className={`h-full rounded-full ${confidenceColor(score)}`}
              initial={{ width: 0 }}
              animate={{ width: `${Math.round(score * 100)}%` }}
              transition={{ duration: 0.7, ease: "easeOut" }}
            />
          </div>

          {fr.explanation_tr && (
            <p className="text-sm leading-relaxed text-muted-foreground">
              <span className="font-medium text-foreground">Açıklama: </span>
              {fr.explanation_tr}
            </p>
          )}
          {fr.uncertainty_tr && (
            <div className="rounded-md border border-warning/30 bg-warning/10 p-3 text-xs leading-relaxed text-warning">
              <span className="mr-1 inline-flex items-center gap-1 font-medium">
                <AlertTriangle size={12} /> Belirsizlik:
              </span>
              {fr.uncertainty_tr}
            </div>
          )}
        </motion.div>

        {/* Risk + insights */}
        <div className="flex flex-col gap-5">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.05 }}
            className="panel p-5"
          >
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wider text-subtle-foreground">
                Satın Alma Riski
              </p>
              <span className="grid h-8 w-8 place-items-center rounded-full bg-brand-soft text-brand">
                <ShieldCheck size={14} />
              </span>
            </div>
            <p className="mt-2 text-lg font-semibold text-foreground">
              {fr.risk_level_tr ?? detail.risk_level ?? "—"}
            </p>
            {detail.risk_level && (
              <span
                className={`mt-2 inline-flex w-fit rounded-pill border px-2.5 py-0.5 text-[11px] font-medium ${riskPill}`}
              >
                {fr.risk_level_tr ?? detail.risk_level}
              </span>
            )}
            {riskFactors.length > 0 && (
              <ul className="mt-4 flex flex-col gap-2">
                {riskFactors.map((factor, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm text-muted-foreground"
                  >
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand/70" />
                    {factor}
                  </li>
                ))}
              </ul>
            )}
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.1 }}
            className="panel p-5"
          >
            <p className="text-xs font-semibold uppercase tracking-wider text-subtle-foreground">
              Topluluk İçgörüleri
            </p>
            {insights.length === 0 ? (
              <p className="mt-3 text-sm text-muted-foreground">
                Yeterli kullanıcı yorumu bulunmuyor.
              </p>
            ) : (
              <ul className="mt-3 flex flex-col gap-3">
                {insights.map((insight, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm leading-relaxed text-muted-foreground"
                  >
                    <MessageSquare className="mt-0.5 h-4 w-4 shrink-0 text-brand/70" />
                    {insight}
                  </li>
                ))}
              </ul>
            )}
          </motion.div>
        </div>
      </div>
    </div>
  );
}
