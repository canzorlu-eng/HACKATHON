"use client";

import { motion } from "framer-motion";

export interface HeatmapRegion {
  region: string;          // "omuz" | "kol" | "bel" | "kalca" | "bacak"
  label_tr: string;
  status: "low" | "medium" | "high";
  reason_tr: string;
}

const STATUS_TR: Record<HeatmapRegion["status"], string> = {
  low: "Düşük",
  medium: "Orta",
  high: "Yüksek",
};

const STATUS_FILL: Record<HeatmapRegion["status"], string> = {
  low: "hsl(152 70% 50% / 0.55)",
  medium: "hsl(38 92% 55% / 0.55)",
  high: "hsl(0 72% 56% / 0.55)",
};

const STATUS_DOT: Record<HeatmapRegion["status"], string> = {
  low: "bg-success",
  medium: "bg-warning",
  high: "bg-danger",
};

const STATUS_PILL: Record<HeatmapRegion["status"], string> = {
  low: "text-success bg-success/10 border-success/30",
  medium: "text-warning bg-warning/10 border-warning/30",
  high: "text-danger bg-danger/10 border-danger/30",
};

// Region key → SVG element(s). Returning a fragment lets a single region
// paint multiple paths (e.g. both arms for "kol", both legs for "bacak").
// The mannequin is the same full body regardless of garment category; only
// the highlighted regions change.
function renderRegion(
  region: HeatmapRegion["region"],
  status: HeatmapRegion["status"],
): React.ReactNode {
  const fill = STATUS_FILL[status];
  switch (region) {
    case "omuz":
      // Top of torso — under the neck, above the chest line
      return (
        <path
          d="M60 78 Q72 66 92 64 L108 64 Q128 66 140 78 L144 100 L56 100 Z"
          fill={fill}
          stroke="none"
        />
      );
    case "kol":
      // Both arms
      return (
        <>
          <path
            d="M60 78 L46 110 L52 145 L62 152 L62 100 Z"
            fill={fill}
            stroke="none"
          />
          <path
            d="M140 78 L154 110 L148 145 L138 152 L138 100 Z"
            fill={fill}
            stroke="none"
          />
        </>
      );
    case "bel":
      // Middle torso band — waistline area
      return (
        <path
          d="M56 110 L144 110 L146 140 Q146 145 138 152 L62 152 Q54 145 54 140 Z"
          fill={fill}
          stroke="none"
        />
      );
    case "kalca":
      // Hip block — below waist, just above legs
      return (
        <path
          d="M62 152 L138 152 L142 178 Q142 184 132 188 L68 188 Q58 184 58 178 Z"
          fill={fill}
          stroke="none"
        />
      );
    case "bacak":
      // Both legs — from hip to ankle
      return (
        <>
          <path
            d="M68 188 L62 260 L78 260 L84 188 Z"
            fill={fill}
            stroke="none"
          />
          <path
            d="M116 188 L122 260 L138 260 L132 188 Z"
            fill={fill}
            stroke="none"
          />
        </>
      );
    default:
      return null;
  }
}

export function BodyHeatmap({ regions }: { regions: HeatmapRegion[] }) {
  if (!regions || regions.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="panel p-5"
    >
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wider text-subtle-foreground">
          Risk Isı Haritası
        </p>
        <p className="text-[10px] text-subtle-foreground">
          Renkler analiz risk seviyesini gösterir
        </p>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-[1fr_1.1fr]">
        {/* Mannequin — always full body, regions colored only when present */}
        <div className="relative mx-auto aspect-[3/4] w-full max-w-[260px]">
          <svg viewBox="0 0 200 280" className="h-full w-full" aria-hidden>
            <defs>
              <linearGradient id="hm-stroke" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="hsl(0 0% 98%)" stopOpacity="0.55" />
                <stop offset="100%" stopColor="hsl(0 0% 98%)" stopOpacity="0.2" />
              </linearGradient>
            </defs>

            {/* Region fills first — outlines drawn on top */}
            {regions.map((r) => (
              <g key={`fill-${r.region}`}>{renderRegion(r.region, r.status)}</g>
            ))}

            {/* Head */}
            <circle cx="100" cy="32" r="20" fill="none"
                    stroke="url(#hm-stroke)" strokeWidth="1" />

            {/* Neck */}
            <path d="M93 50 L107 50 L108 62 L92 62 Z" fill="none"
                  stroke="url(#hm-stroke)" strokeWidth="0.8" />

            {/* Torso outline */}
            <path
              d="M60 78 Q72 66 92 64 L108 64 Q128 66 140 78 L146 130 Q146 145 138 152 L62 152 Q54 145 54 130 Z"
              fill="none" stroke="url(#hm-stroke)" strokeWidth="0.9"
            />

            {/* Arm outlines */}
            <path d="M60 78 L46 110 L52 145 L62 152" fill="none"
                  stroke="url(#hm-stroke)" strokeWidth="0.9" />
            <path d="M140 78 L154 110 L148 145 L138 152" fill="none"
                  stroke="url(#hm-stroke)" strokeWidth="0.9" />

            {/* Hip outline */}
            <path
              d="M62 152 L138 152 L142 178 Q142 184 132 188 L68 188 Q58 184 58 178 Z"
              fill="none" stroke="url(#hm-stroke)" strokeWidth="0.9"
            />

            {/* Leg outlines */}
            <path d="M68 188 L62 260 L78 260 L84 188 Z" fill="none"
                  stroke="url(#hm-stroke)" strokeWidth="0.9" />
            <path d="M116 188 L122 260 L138 260 L132 188 Z" fill="none"
                  stroke="url(#hm-stroke)" strokeWidth="0.9" />
          </svg>
        </div>

        {/* Side panel — region labels with status + reasons */}
        <ul className="flex flex-col gap-3">
          {regions.map((r) => (
            <li
              key={r.region}
              className="rounded-card border border-border bg-panel-elev p-3"
            >
              <div className="flex items-center gap-2">
                <span
                  className={`h-2.5 w-2.5 shrink-0 rounded-full ${STATUS_DOT[r.status]}`}
                  aria-hidden
                />
                <p className="text-sm font-semibold text-foreground">
                  {r.label_tr}
                </p>
                <span
                  className={`ml-auto inline-flex rounded-pill border px-2 py-0.5 text-[10px] font-medium ${STATUS_PILL[r.status]}`}
                >
                  {STATUS_TR[r.status]}
                </span>
              </div>
              <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
                {r.reason_tr}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </motion.div>
  );
}
