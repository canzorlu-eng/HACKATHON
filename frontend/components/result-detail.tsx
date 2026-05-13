"use client";

import { motion } from "framer-motion";
import { MessageSquare, AlertTriangle, CheckCircle } from "lucide-react";

export interface AnalysisResult {
  recommended_size: string | null;
  confidence_score: number | null;
  confidence_pct: string | null;
  explanation_tr: string | null;
  risk_level: "low" | "medium" | "high" | null;
  risk_level_tr: string | null;
  risk_factors_tr: string[] | null;
  uncertainty_tr: string | null;
  community_insights_tr: string[] | null;
}

interface ResultDetailProps {
  result: AnalysisResult;
}

const riskBadgeClass: Record<string, string> = {
  low: "bg-green-100 text-green-700",
  medium: "bg-amber-100 text-amber-700",
  high: "bg-red-100 text-red-700",
};

const barColorClass = (score: number | null): string => {
  if (score === null) return "bg-muted";
  const pct = score * 100;
  if (pct >= 70) return "bg-green-500";
  if (pct >= 50) return "bg-amber-500";
  return "bg-red-500";
};

const sectionVariants = (index: number) => ({
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { delay: index * 0.08, duration: 0.4 },
});

export default function ResultDetail({ result }: ResultDetailProps) {
  const {
    recommended_size,
    confidence_score,
    confidence_pct,
    explanation_tr,
    risk_level,
    risk_level_tr,
    risk_factors_tr,
    uncertainty_tr,
    community_insights_tr,
  } = result;

  const barWidth = `${Math.round((confidence_score ?? 0) * 100)}%`;

  return (
    <div className="flex flex-col gap-5">
      {/* Section 1 — Recommendation card */}
      <motion.div
        {...sectionVariants(0)}
        className="rounded-xl border border-border bg-background p-6 shadow-sm text-center"
      >
        <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">
          Önerilen Beden
        </p>
        <p className="text-6xl font-bold tracking-tight">
          {recommended_size ?? "–"}
        </p>
        {confidence_pct && (
          <p className="text-sm text-muted-foreground mt-2">
            {confidence_pct} güven skoru
          </p>
        )}
        <div className="h-px bg-border my-4" />
        {explanation_tr && (
          <p className="text-sm text-foreground/80 text-left">{explanation_tr}</p>
        )}
      </motion.div>

      {/* Section 2 — Confidence bar */}
      <motion.div
        {...sectionVariants(1)}
        className="rounded-xl border border-border bg-background p-4 shadow-sm"
      >
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">Güven Skoru</span>
          {confidence_pct && (
            <span className="text-sm text-muted-foreground">{confidence_pct}</span>
          )}
        </div>
        <div className="h-2 w-full rounded-full bg-muted mt-2 overflow-hidden">
          <motion.div
            className={`h-full rounded-full transition-all duration-700 ${barColorClass(confidence_score)}`}
            initial={{ width: "0%" }}
            animate={{ width: barWidth }}
            transition={{ duration: 0.7, ease: "easeOut" }}
          />
        </div>
      </motion.div>

      {/* Section 3 — Risk panel */}
      <motion.div
        {...sectionVariants(2)}
        className="rounded-xl border border-border bg-background p-4 shadow-sm"
      >
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium">Risk Değerlendirmesi</span>
          {risk_level && risk_level_tr && (
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${riskBadgeClass[risk_level] ?? "bg-muted text-muted-foreground"}`}
            >
              {risk_level_tr}
            </span>
          )}
        </div>

        {risk_factors_tr && risk_factors_tr.length > 0 ? (
          <ul className="space-y-0.5">
            {risk_factors_tr.map((factor, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-foreground/80 py-1">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-foreground/40" />
                {factor}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">
            Belirgin bir risk faktörü tespit edilmedi.
          </p>
        )}

        {uncertainty_tr && (
          <p className="mt-3 text-xs italic text-muted-foreground">
            {uncertainty_tr}
          </p>
        )}
      </motion.div>

      {/* Section 4 — Community insights */}
      <motion.div
        {...sectionVariants(3)}
        className="rounded-xl border border-border bg-background p-4 shadow-sm"
      >
        <div className="flex items-center gap-1.5 mb-3">
          <MessageSquare size={14} className="text-foreground/60" />
          <span className="text-sm font-medium">Topluluk Yorumları</span>
        </div>

        {community_insights_tr && community_insights_tr.length > 0 ? (
          <ul className="space-y-0.5">
            {community_insights_tr.map((insight, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-foreground/80 py-1">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-foreground/40" />
                {insight}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">
            Henüz yeterli kullanıcı yorumu bulunmuyor.
          </p>
        )}
      </motion.div>
    </div>
  );
}
