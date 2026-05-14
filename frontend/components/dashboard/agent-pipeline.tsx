"use client";

import { motion } from "framer-motion";
import {
  Check,
  Loader2,
  Circle,
  User2,
  Shirt,
  MessageSquare,
  ShieldCheck,
} from "lucide-react";

// Phase values mirror the analyze page state machine.
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

interface AgentSpec {
  key: string;
  name: string;
  subtitle: string;
  icon: typeof Check;
  startPhase: Phase; // phase at which this agent is "running"
  donePhase: Phase;  // phase at which this agent is "done"
}

// Agents map to the LangGraph nodes in backend/app/ai/graph.py:
//   analyzer (body + garment in parallel) → step_2
//   review_retriever                       → step_3
//   risk_evaluator                         → step_5
const AGENTS: AgentSpec[] = [
  {
    key: "body",
    name: "Body Agent",
    subtitle: "Vücut analizi",
    icon: User2,
    startPhase: "step_2",
    donePhase: "step_3",
  },
  {
    key: "garment",
    name: "Garment Agent",
    subtitle: "Kıyafet analizi",
    icon: Shirt,
    startPhase: "step_2",
    donePhase: "step_3",
  },
  {
    key: "review",
    name: "Review Agent",
    subtitle: "Topluluk içgörüleri",
    icon: MessageSquare,
    startPhase: "step_3",
    donePhase: "step_4",
  },
  {
    key: "risk",
    name: "Risk Agent",
    subtitle: "Satın alma riski",
    icon: ShieldCheck,
    startPhase: "step_5",
    donePhase: "step_6",
  },
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

/**
 * Live agent breakdown panel.
 *
 * `variant="full"` — large 2×2 grid used during the in-progress phase so the
 * user (and demo judges) can see the multi-agent pipeline firing.
 * `variant="compact"` — single row of 4 chips used in the results panel as a
 * "what ran" confirmation strip. All agents render as ✓.
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
        {AGENTS.map((a) => {
          const Icon = a.icon;
          return (
            <span
              key={a.key}
              className="inline-flex items-center gap-1.5 rounded-pill border border-success/30 bg-success/10 px-2.5 py-1 text-[11px] font-medium text-success"
              title={a.subtitle}
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

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
        {AGENTS.map((agent, idx) => {
          const status = agentStatus(phase, agent);
          const Icon = agent.icon;
          return (
            <motion.div
              key={agent.key}
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
                  "grid h-9 w-9 shrink-0 place-items-center rounded-md",
                  status === "done"
                    ? "bg-success/15 text-success"
                    : status === "running"
                    ? "bg-brand/20 text-brand"
                    : "bg-panel text-subtle-foreground",
                ].join(" ")}
              >
                <Icon size={16} />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-foreground">
                  {agent.name}
                </p>
                <p className="text-xs text-subtle-foreground">
                  {agent.subtitle}
                </p>
              </div>
              <span className="shrink-0">
                {status === "done" && (
                  <Check size={16} className="text-success" />
                )}
                {status === "running" && (
                  <Loader2
                    size={14}
                    className="animate-spin text-brand"
                  />
                )}
                {status === "pending" && (
                  <Circle
                    size={14}
                    className="text-subtle-foreground/60"
                  />
                )}
              </span>
            </motion.div>
          );
        })}
      </div>

      <p className="mt-4 text-[10px] leading-relaxed text-subtle-foreground">
        Body &amp; Garment ajanları paralel çalışır (asyncio.gather). Review
        ajanı ChromaDB üzerinde RAG yapar. Risk ajanı güven skoru, kumaş ve
        marka sinyallerini birleştirir.
      </p>
    </div>
  );
}
