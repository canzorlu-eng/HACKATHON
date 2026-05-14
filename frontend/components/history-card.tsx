"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowUpRight } from "lucide-react";

export interface HistoryItem {
  analysis_id: string;
  created_at: string;
  garment_image_ref: string;
  recommended_size: string | null;
  risk_level: "low" | "medium" | "high" | null;
}

interface HistoryCardProps {
  item: HistoryItem;
  index: number;
}

const riskConfig: Record<
  "low" | "medium" | "high",
  { label: string; className: string }
> = {
  low: {
    label: "Düşük Risk",
    className: "text-success bg-success/10 border-success/30",
  },
  medium: {
    label: "Orta Risk",
    className: "text-warning bg-warning/10 border-warning/30",
  },
  high: {
    label: "Yüksek Risk",
    className: "text-danger bg-danger/10 border-danger/30",
  },
};

export function HistoryCard({ item, index }: HistoryCardProps) {
  const formattedDate = new Date(item.created_at).toLocaleDateString("tr-TR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  const risk = item.risk_level ? riskConfig[item.risk_level] : null;

  return (
    <Link
      href={`/history/${item.analysis_id}`}
      className="block rounded-card focus:outline-none focus:ring-2 ring-brand"
    >
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, delay: index * 0.05, ease: "easeOut" }}
        className="panel flex items-center gap-4 p-4 transition hover:border-border-strong"
      >
        {/* Size circle */}
        <div className="grid h-12 w-12 shrink-0 select-none place-items-center rounded-card bg-brand-soft text-lg font-bold text-brand">
          {item.recommended_size ?? "—"}
        </div>

        {/* Info */}
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <p className="truncate text-sm font-medium text-foreground">
            Analiz {item.analysis_id.slice(0, 8)}
          </p>
          <span className="text-xs text-subtle-foreground">
            {formattedDate}
          </span>
        </div>

        {/* Risk pill */}
        {risk ? (
          <span
            className={`inline-flex w-fit items-center rounded-pill border px-2.5 py-0.5 text-xs font-medium ${risk.className}`}
          >
            {risk.label}
          </span>
        ) : (
          <span className="text-xs text-subtle-foreground">—</span>
        )}

        <ArrowUpRight size={14} className="text-subtle-foreground" />
      </motion.div>
    </Link>
  );
}
