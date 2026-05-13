"use client";

import Link from "next/link";
import { motion } from "framer-motion";

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
    className:
      "text-green-700 bg-green-50 border border-green-200",
  },
  medium: {
    label: "Orta Risk",
    className:
      "text-amber-700 bg-amber-50 border border-amber-200",
  },
  high: {
    label: "Yüksek Risk",
    className:
      "text-red-700 bg-red-50 border border-red-200",
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
    <Link href={`/history/${item.analysis_id}`} className="block rounded-xl focus:outline-none focus:ring-2 focus:ring-foreground/20">
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: index * 0.06, ease: "easeOut" }}
      className="rounded-xl border border-border bg-background p-4 shadow-sm flex items-center gap-4 cursor-pointer hover:shadow-md transition-shadow"
    >
      {/* Size circle */}
      <div className="w-12 h-12 rounded-full bg-foreground text-background flex items-center justify-center shrink-0 text-lg font-bold select-none">
        {item.recommended_size ?? "–"}
      </div>

      {/* Info */}
      <div className="flex flex-col gap-1 min-w-0">
        <span className="text-sm text-muted-foreground leading-none">
          {formattedDate}
        </span>
        {risk ? (
          <span
            className={`inline-flex w-fit items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${risk.className}`}
          >
            {risk.label}
          </span>
        ) : (
          <span className="text-sm text-muted-foreground">—</span>
        )}
      </div>
    </motion.div>
    </Link>
  );
}
