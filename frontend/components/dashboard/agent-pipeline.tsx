"use client";

import { motion } from "framer-motion";
import {
  Check,
  Loader2,
  Circle,
  ShieldCheck,
  ShieldQuestion,
  User2,
  Shirt,
  MessageSquare,
  Calculator,
  Sparkles,
  Languages,
  GitMerge,
} from "lucide-react";

// Phase values mirror the analyze page state machine. Backend graph nodes
// map to phases as follows:
//
//   intent_validator        → step_1 (running) → step_2 (done)
//   analyzer (parallel)     → step_2          → step_3   ← Body + Garment in asyncio.gather
//     ├─ analyze_body       (Gemini vision)
//     └─ analyze_garment    (Gemini vision + is_garment gate)
//   review_retriever        → step_3          → step_4   ← Chroma cosine ≥0.30 + Jaccard
//                                                          + metadata where-filter
//   recommendation_generator→ step_4          → step_5   ← BMI + deltas (deterministic)
//   risk_evaluator          → step_5          → step_6   ← deterministic risk score
//   narrative_composer      → step_6          → done     ← Gemini text (Detaylı Analiz)
//   turkish_formatter       → step_6          → done     ← deterministic assembly + heatmap
type Phase =
  | "idle"
  | "uploading"
  | "step_1"
  | "step_2"
  | "step_3"
  | "step_4"
  | "step_5"
  | "step_6"
  | "done"
  | "error";

const PHASE_ORDER: Phase[] = [
  "idle",
  "uploading",
  "step_1",
  "step_2",
  "step_3",
  "step_4",
  "step_5",
  "step_6",
  "done",
];

function pi(p: Phase): number {
  const i = PHASE_ORDER.indexOf(p);
  return i < 0 ? 0 : i;
}

type Backend = "gemini" | "rag" | "deterministic";

interface AgentSpec {
  key: string;
  name: string;
  subtitle: string;
  icon: typeof Check;
  backend: Backend;
  startPhase: Phase;
  donePhase: Phase;
}

const BACKEND_BADGE: Record<Backend, { label: string; className: string }> = {
  gemini: {
    label: "Gemini",
    className: "border-brand/40 bg-brand-soft text-brand",
  },
  rag: {
    label: "RAG",
    className: "border-warning/40 bg-warning/10 text-warning",
  },
  deterministic: {
    label: "Deterministic",
    className: "border-border bg-panel-elev text-subtle-foreground",
  },
};

// Top-level nodes shown in vertical order. The analyzer parent is rendered
// separately so its two parallel children can sit beside each other.
const TOP_AGENTS: AgentSpec[] = [
  {
    key: "intent",
    name: "Intent Validator",
    subtitle: "Giriş doğrulama (boy / kilo / kıyafet ref)",
    icon: ShieldQuestion,
    backend: "deterministic",
    startPhase: "step_1",
    donePhase: "step_2",
  },
];

// Parallel children of `analyzer` — both run inside asyncio.gather().
const ANALYZER_PARENT: AgentSpec = {
  key: "analyzer",
  name: "Analyzer",
  subtitle: "asyncio.gather — paralel multimodal analiz",
  icon: GitMerge,
  backend: "gemini",
  startPhase: "step_2",
  donePhase: "step_3",
};

const ANALYZER_CHILDREN: AgentSpec[] = [
  {
    key: "body",
    name: "Body Agent",
    subtitle: "Vücut görsel analizi",
    icon: User2,
    backend: "gemini",
    startPhase: "step_2",
    donePhase: "step_3",
  },
  {
    key: "garment",
    name: "Garment Agent",
    subtitle: "Kıyafet görsel analizi + is_garment kapısı",
    icon: Shirt,
    backend: "gemini",
    startPhase: "step_2",
    donePhase: "step_3",
  },
];

// Nodes after the analyzer.
const POST_ANALYZER_AGENTS: AgentSpec[] = [
  {
    key: "review",
    name: "Review Retriever",
    subtitle: "ChromaDB cosine + Jaccard + metadata filtre",
    icon: MessageSquare,
    backend: "rag",
    startPhase: "step_3",
    donePhase: "step_4",
  },
  {
    key: "recommend",
    name: "Recommendation Generator",
    subtitle: "BMI + fit / brand delta — beden seçimi",
    icon: Calculator,
    backend: "deterministic",
    startPhase: "step_4",
    donePhase: "step_5",
  },
  {
    key: "risk",
    name: "Risk Evaluator",
    subtitle: "Güven, kumaş, marka → risk seviyesi",
    icon: ShieldCheck,
    backend: "deterministic",
    startPhase: "step_5",
    donePhase: "step_6",
  },
  {
    key: "narrative",
    name: "Narrative Composer",
    subtitle: "Detaylı Türkçe açıklama (Detaylı Analiz kartı)",
    icon: Sparkles,
    backend: "gemini",
    startPhase: "step_6",
    donePhase: "done",
  },
  {
    key: "formatter",
    name: "Turkish Formatter",
    subtitle: "Son cevap + risk heatmap + garment_meta",
    icon: Languages,
    backend: "deterministic",
    startPhase: "step_6",
    donePhase: "done",
  },
];

// Compact strip — everything in one row of pills.
const ALL_AGENTS_FLAT: AgentSpec[] = [
  ...TOP_AGENTS,
  ANALYZER_PARENT,
  ...POST_ANALYZER_AGENTS,
];

type Status = "pending" | "running" | "done";

function agentStatus(phase: Phase, spec: AgentSpec): Status {
  if (phase === "done") return "done";
  if (phase === "error") return "pending";
  const cur = pi(phase);
  if (cur >= pi(spec.donePhase)) return "done";
  if (cur >= pi(spec.startPhase)) return "running";
  return "pending";
}

// ─────────────────────────────────────────────────────────────────────────
// Reusable agent card
// ─────────────────────────────────────────────────────────────────────────

function AgentCard({
  spec,
  status,
  idx,
  size = "md",
}: {
  spec: AgentSpec;
  status: Status;
  idx: number;
  size?: "md" | "sm";
}) {
  const Icon = spec.icon;
  const badge = BACKEND_BADGE[spec.backend];
  const iconBox = size === "sm" ? "h-7 w-7" : "h-9 w-9";
  const titleClass = size === "sm" ? "text-[13px]" : "text-sm";
  const subClass = size === "sm" ? "text-[10px]" : "text-xs";

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: idx * 0.04 }}
      className={[
        "flex items-center gap-3 rounded-card border p-3 transition-colors",
        status === "done"
          ? "border-success/40 bg-success/5"
          : status === "running"
          ? "border-brand/40 bg-brand-soft"
          : "border-border bg-panel-elev",
      ].join(" ")}
    >
      <span
        className={[
          "grid shrink-0 place-items-center rounded-md",
          iconBox,
          status === "done"
            ? "bg-success/15 text-success"
            : status === "running"
            ? "bg-brand/20 text-brand"
            : "bg-panel text-subtle-foreground",
        ].join(" ")}
      >
        <Icon size={size === "sm" ? 14 : 16} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className={`${titleClass} font-medium text-foreground`}>
            {spec.name}
          </p>
          <span
            className={`inline-flex shrink-0 rounded-pill border px-1.5 py-0 text-[9px] font-semibold uppercase tracking-wider ${badge.className}`}
          >
            {badge.label}
          </span>
        </div>
        <p className={`${subClass} text-subtle-foreground`}>{spec.subtitle}</p>
      </div>
      <span className="shrink-0">
        {status === "done" && <Check size={16} className="text-success" />}
        {status === "running" && (
          <Loader2 size={14} className="animate-spin text-brand" />
        )}
        {status === "pending" && (
          <Circle size={14} className="text-subtle-foreground/60" />
        )}
      </span>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────────────────

/**
 * Live agent breakdown panel.
 *
 * variant="full"    — full pipeline shown during in-progress, with Body +
 *                     Garment nested under Analyzer as parallel children
 *                     (matches asyncio.gather in backend/app/ai/graph.py).
 * variant="compact" — single row of pills used as a "what ran" confirmation
 *                     strip below the results.
 */
export function AgentPipeline({
  phase,
  variant = "full",
}: {
  phase: Phase;
  variant?: "full" | "compact";
}) {
  if (variant === "compact") {
    return (
      <div className="panel flex flex-wrap items-center gap-2 p-3">
        <span className="mr-1 text-[10px] font-semibold uppercase tracking-wider text-subtle-foreground">
          Ajan Hattı
        </span>
        {ALL_AGENTS_FLAT.map((a) => {
          const Icon = a.icon;
          const badge = BACKEND_BADGE[a.backend];
          return (
            <span
              key={a.key}
              className={`inline-flex items-center gap-1.5 rounded-pill border px-2.5 py-1 text-[11px] font-medium ${badge.className}`}
              title={`${a.subtitle} · ${badge.label}`}
            >
              <Icon size={11} />
              {a.name}
              <Check size={11} />
            </span>
          );
        })}
      </div>
    );
  }

  const intent = TOP_AGENTS[0];

  return (
    <div className="panel p-5">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wider text-subtle-foreground">
          Ajan Hattı
        </p>
        <p className="text-[10px] text-subtle-foreground">
          LangGraph multi-agent pipeline
        </p>
      </div>

      <div className="mt-4 flex flex-col gap-3">
        {/* 1. Intent validator */}
        <AgentCard
          spec={intent}
          status={agentStatus(phase, intent)}
          idx={0}
        />

        {/* 2. Analyzer parent + 2 parallel children */}
        <div className="rounded-card border border-border bg-panel-elev/40 p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span
                className={[
                  "grid h-7 w-7 place-items-center rounded-md",
                  agentStatus(phase, ANALYZER_PARENT) === "done"
                    ? "bg-success/15 text-success"
                    : agentStatus(phase, ANALYZER_PARENT) === "running"
                    ? "bg-brand/20 text-brand"
                    : "bg-panel text-subtle-foreground",
                ].join(" ")}
              >
                <GitMerge size={14} />
              </span>
              <div>
                <p className="text-sm font-medium text-foreground">
                  Analyzer
                </p>
                <p className="text-[10px] text-subtle-foreground">
                  asyncio.gather — body + garment paralel çalışır
                </p>
              </div>
            </div>
            <span className="inline-flex items-center gap-1 rounded-pill border border-brand/40 bg-brand-soft px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-brand">
              <Sparkles size={10} />
              Paralel
            </span>
          </div>

          <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
            {ANALYZER_CHILDREN.map((child, i) => (
              <AgentCard
                key={child.key}
                spec={child}
                status={agentStatus(phase, child)}
                idx={i + 1}
                size="sm"
              />
            ))}
          </div>
        </div>

        {/* 3+. Sequential nodes after analyzer */}
        {POST_ANALYZER_AGENTS.map((agent, idx) => (
          <AgentCard
            key={agent.key}
            spec={agent}
            status={agentStatus(phase, agent)}
            idx={idx + 3}
          />
        ))}
      </div>

      <p className="mt-4 text-[10px] leading-relaxed text-subtle-foreground">
        Body &amp; Garment ajanları paralel çalışır (asyncio.gather). Review
        ajanı ChromaDB üzerinde RAG yapar (cosine ≥ 0.30 + Jaccard dedup +
        metadata filtre). Beden önerisi ve risk skoru deterministik —
        sayılar uydurulmaz. Narrative ajanı sadece açıklama metnini
        Gemini ile yazar; kararları değiştirmez.
      </p>
    </div>
  );
}
