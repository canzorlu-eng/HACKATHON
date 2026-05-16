"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Users, AlertTriangle, Quote } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { tr } from "@/lib/i18n/tr";

interface ReasonStat {
  reason: string;
  reason_tr: string;
  raw_count: number;
  pct: number;
}

interface CohortResponse {
  scope_tr: string;
  total: number;
  returned_count: number;
  returned_pct: number | null;
  confidence_band: "low" | "medium" | "high";
  top_reasons: ReasonStat[];
  sample_quotes_tr: string[];
}

interface Props {
  analysisId: string;
}

const BAR_COLOR = (pct: number): string => {
  if (pct >= 40) return "bg-danger";
  if (pct >= 20) return "bg-warning";
  return "bg-brand";
};

export function SimilarUsersPanel({ analysisId }: Props) {
  const [data, setData] = useState<CohortResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);
    apiFetch(`/api/v1/analyses/${analysisId}/cohort`)
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return (await r.json()) as CohortResponse;
      })
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [analysisId]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="panel p-5"
    >
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wider text-subtle-foreground">
          {tr.cohort.panel_title}
        </p>
        <span className="grid h-8 w-8 place-items-center rounded-full bg-brand-soft text-brand">
          <Users size={14} />
        </span>
      </div>

      <AnimatePresence mode="wait">
        {loading && (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="mt-4 flex flex-col gap-3"
          >
            <p className="text-sm text-muted-foreground">{tr.cohort.loading}</p>
            <div className="flex flex-col gap-2">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="h-3 w-full overflow-hidden rounded-full bg-panel-elev"
                >
                  <div
                    className="h-full animate-pulse rounded-full bg-border"
                    style={{ width: `${60 - i * 15}%` }}
                  />
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {!loading && error && (
          <motion.div
            key="error"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-4 flex items-start gap-2 text-sm text-warning"
          >
            <AlertTriangle size={14} className="mt-0.5" />
            <span>{tr.cohort.error}</span>
          </motion.div>
        )}

        {!loading && !error && data && (
          <motion.div
            key="data"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="mt-4 flex flex-col gap-4"
          >
            {/* Scope badge */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-pill border border-border bg-panel-elev px-3 py-1 text-[11px] font-medium text-muted-foreground">
                {tr.cohort.scope_prefix}: {data.scope_tr}
              </span>
              {data.confidence_band !== "low" && data.returned_pct !== null && (
                <span
                  className={`inline-flex items-center gap-1.5 rounded-pill border px-3 py-1 text-[11px] font-semibold ${
                    data.returned_pct >= 30
                      ? "border-danger/30 bg-danger/10 text-danger"
                      : data.returned_pct >= 15
                      ? "border-warning/30 bg-warning/10 text-warning"
                      : "border-success/30 bg-success/10 text-success"
                  }`}
                >
                  %{data.returned_pct} {tr.cohort.returned_pct_suffix}
                </span>
              )}
            </div>

            {/* Low-confidence path */}
            {data.confidence_band === "low" && (
              <p className="text-sm text-muted-foreground">
                {tr.cohort.not_enough_data}
              </p>
            )}

            {/* Reason bars */}
            {data.confidence_band !== "low" && data.top_reasons.length > 0 && (
              <div>
                <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-subtle-foreground">
                  {tr.cohort.top_reasons_title}
                </p>
                <ul className="flex flex-col gap-2.5">
                  {data.top_reasons.map((r) => (
                    <li key={r.reason} className="flex flex-col gap-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-medium text-foreground">
                          {r.reason_tr}
                        </span>
                        <span className="text-muted-foreground">
                          %{r.pct}{" "}
                          <span className="text-subtle-foreground">
                            ({r.raw_count} kişi)
                          </span>
                        </span>
                      </div>
                      <div className="h-2 w-full overflow-hidden rounded-full bg-panel-elev">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${r.pct}%` }}
                          transition={{ duration: 0.6, ease: "easeOut" }}
                          className={`h-full rounded-full ${BAR_COLOR(r.pct)}`}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Verbatim quotes — only when we have meaningful data */}
            {data.confidence_band !== "low" &&
              data.sample_quotes_tr.length > 0 && (
                <div>
                  <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-subtle-foreground">
                    {tr.cohort.sample_quotes_title}
                  </p>
                  <ul className="flex flex-col gap-2">
                    {data.sample_quotes_tr.slice(0, 2).map((q, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-2 rounded-card border border-border bg-panel-elev/60 p-3 text-xs italic leading-relaxed text-muted-foreground"
                      >
                        <Quote
                          size={12}
                          className="mt-0.5 shrink-0 text-brand/70"
                        />
                        <span>{q}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
