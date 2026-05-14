"use client";

import { motion } from "framer-motion";

/**
 * Static SVG mannequin silhouette with subtle floating callouts.
 * Lightweight — no Three.js, no GPU usage. Decorative only:
 * the labels are illustrative (not user data).
 */
export function MannequinHero() {
  return (
    <div className="relative mx-auto aspect-square w-full max-w-[480px]">
      {/* Glow rings */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute inset-[8%] rounded-full border border-brand/30" />
        <div className="absolute inset-[16%] rounded-full border border-brand/15" />
        <div className="absolute inset-[28%] rounded-full border border-brand/10" />
        <div className="absolute left-1/2 top-1/2 h-[60%] w-[60%] -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand/20 blur-3xl" />
      </div>

      {/* Mannequin SVG */}
      <motion.svg
        viewBox="0 0 200 260"
        className="h-full w-full"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.7, ease: "easeOut" }}
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="mq-stroke" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="hsl(0 0% 98%)" stopOpacity="0.65" />
            <stop offset="100%" stopColor="hsl(0 0% 98%)" stopOpacity="0.25" />
          </linearGradient>
          <linearGradient id="mq-shirt" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="hsl(267 50% 30%)" stopOpacity="0.75" />
            <stop offset="100%" stopColor="hsl(240 30% 18%)" stopOpacity="0.9" />
          </linearGradient>
        </defs>

        {/* Head */}
        <circle
          cx="100"
          cy="36"
          r="20"
          fill="none"
          stroke="url(#mq-stroke)"
          strokeWidth="1"
        />
        {/* Wireframe meridians on head */}
        <ellipse cx="100" cy="36" rx="20" ry="7" fill="none" stroke="url(#mq-stroke)" strokeWidth="0.6" opacity="0.6" />
        <ellipse cx="100" cy="36" rx="7" ry="20" fill="none" stroke="url(#mq-stroke)" strokeWidth="0.6" opacity="0.6" />

        {/* Neck */}
        <path d="M93 55 L107 55 L108 65 L92 65 Z" fill="none" stroke="url(#mq-stroke)" strokeWidth="0.8" />

        {/* Torso outline with shirt */}
        <path
          d="M60 78 Q72 66 92 64 L108 64 Q128 66 140 78 L146 130 Q146 145 138 152 L62 152 Q54 145 54 130 Z"
          fill="url(#mq-shirt)"
          stroke="hsl(267 95% 75%)"
          strokeOpacity="0.55"
          strokeWidth="0.8"
        />

        {/* Shirt seam center */}
        <line x1="100" y1="64" x2="100" y2="152" stroke="hsl(267 95% 75%)" strokeOpacity="0.25" strokeWidth="0.5" />

        {/* Shirt grid (subtle wireframe) */}
        <g stroke="hsl(267 95% 75%)" strokeOpacity="0.18" strokeWidth="0.4" fill="none">
          <path d="M60 95 Q100 100 140 95" />
          <path d="M58 115 Q100 122 142 115" />
          <path d="M56 140 Q100 148 144 140" />
        </g>

        {/* Sleeves */}
        <path d="M60 78 L46 110 L52 145 L62 152" fill="none" stroke="url(#mq-stroke)" strokeWidth="0.9" />
        <path d="M140 78 L154 110 L148 145 L138 152" fill="none" stroke="url(#mq-stroke)" strokeWidth="0.9" />

        {/* Hips → legs */}
        <path d="M62 152 L75 235" fill="none" stroke="url(#mq-stroke)" strokeWidth="0.9" />
        <path d="M138 152 L125 235" fill="none" stroke="url(#mq-stroke)" strokeWidth="0.9" />
        <line x1="100" y1="152" x2="100" y2="235" stroke="url(#mq-stroke)" strokeWidth="0.5" opacity="0.5" />
      </motion.svg>

      {/* Floating callouts (decorative labels, not user data) */}
      <Callout className="left-2 top-[16%]" title="Omuz Genişliği" value="Orta" />
      <Callout className="right-2 top-[44%]" title="Uyum Tahmini" value="%87" accent />
      <Callout className="left-2 top-[58%]" title="Vücut Tipi" value="Dengeli" />
      <Callout className="right-2 top-[72%]" title="Risk Seviyesi" value="Düşük" />
    </div>
  );
}

function Callout({
  className,
  title,
  value,
  accent = false,
}: {
  className?: string;
  title: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, delay: 0.4 }}
      className={[
        "absolute rounded-pill border px-3 py-1.5 text-[11px] backdrop-blur",
        accent
          ? "border-brand/40 bg-brand-soft text-foreground"
          : "border-border bg-panel-elev/80 text-muted-foreground",
        className ?? "",
      ].join(" ")}
    >
      <p className="text-[10px] text-subtle-foreground">{title}</p>
      <p
        className={accent ? "font-semibold text-brand" : "font-medium text-foreground"}
      >
        {value}
      </p>
    </motion.div>
  );
}
