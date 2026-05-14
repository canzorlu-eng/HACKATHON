"use client";

import Link from "next/link";
import { useState } from "react";
import { motion } from "framer-motion";
import { ArrowUpRight, Trash2, Loader2 } from "lucide-react";

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
  onDelete?: (analysisId: string) => Promise<void> | void;
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

export function HistoryCard({ item, index, onDelete }: HistoryCardProps) {
  const [deleting, setDeleting] = useState(false);

  const formattedDate = new Date(item.created_at).toLocaleDateString("tr-TR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  const risk = item.risk_level ? riskConfig[item.risk_level] : null;

  async function handleDelete(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (deleting || !onDelete) return;
    const ok = window.confirm("Bu analiz kaydını silmek istediğine emin misin?");
    if (!ok) return;
    setDeleting(true);
    try {
      await onDelete(item.analysis_id);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: 30 }}
      transition={{ duration: 0.25, delay: index * 0.05, ease: "easeOut" }}
      className="panel flex items-center gap-4 p-4 transition hover:border-border-strong"
    >
      {/* Navigable region — wraps everything except the delete button */}
      <Link
        href={`/history/${item.analysis_id}`}
        className="flex min-w-0 flex-1 items-center gap-4 rounded-md focus:outline-none focus:ring-2 ring-brand"
      >
        <div className="grid h-12 w-12 shrink-0 select-none place-items-center rounded-card bg-brand-soft text-lg font-bold text-brand">
          {item.recommended_size ?? "—"}
        </div>

        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <p className="truncate text-sm font-medium text-foreground">
            Analiz {item.analysis_id.slice(0, 8)}
          </p>
          <span className="text-xs text-subtle-foreground">{formattedDate}</span>
        </div>

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
      </Link>

      {/* Delete button — outside the Link so it doesn't navigate. */}
      <button
        type="button"
        onClick={handleDelete}
        disabled={deleting}
        aria-label="Analizi sil"
        className="grid h-9 w-9 shrink-0 place-items-center rounded-full border border-border bg-panel-elev text-subtle-foreground transition hover:border-danger/40 hover:bg-danger/10 hover:text-danger disabled:cursor-not-allowed disabled:opacity-50"
      >
        {deleting ? (
          <Loader2 size={14} className="animate-spin" />
        ) : (
          <Trash2 size={14} />
        )}
      </button>
    </motion.div>
  );
}
