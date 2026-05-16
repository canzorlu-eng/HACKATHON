"use client";

import { useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageCircleQuestion,
  Send,
  ChevronDown,
  ChevronUp,
  Sparkles,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import { tr } from "@/lib/i18n/tr";

type Intent =
  | "is_big"
  | "fabric_sweat"
  | "cut_wide"
  | "similar_users"
  | "return_reasons"
  | "unsupported";

interface QAAnswerResponse {
  intent: Intent;
  answer_tr: string;
  confidence_band: "low" | "medium" | "high";
  evidence_tr: string[];
  cohort_scope_tr: string | null;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "error";
  text: string;
  intent?: Intent;
  confidence_band?: "low" | "medium" | "high";
  evidence_tr?: string[];
  cohort_scope_tr?: string | null;
}

const CHIP_INTENTS: Array<{ intent: Intent; label: string }> = [
  { intent: "is_big", label: tr.qa.chips.is_big },
  { intent: "fabric_sweat", label: tr.qa.chips.fabric_sweat },
  { intent: "cut_wide", label: tr.qa.chips.cut_wide },
  { intent: "similar_users", label: tr.qa.chips.similar_users },
  { intent: "return_reasons", label: tr.qa.chips.return_reasons },
];

const BAND_PILL: Record<"low" | "medium" | "high", string> = {
  high: "text-success bg-success/10 border-success/30",
  medium: "text-warning bg-warning/10 border-warning/30",
  low: "text-muted-foreground bg-panel-elev border-border",
};

const BAND_LABEL: Record<"low" | "medium" | "high", string> = {
  high: "Yüksek güven",
  medium: "Orta güven",
  low: "Düşük güven",
};

function intentLabel(intent: Intent): string {
  return tr.qa.intent_labels[intent] ?? intent;
}

interface Props {
  analysisId: string;
}

export function ProductQAChat({ analysisId }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const listEndRef = useRef<HTMLDivElement | null>(null);

  function genId(): string {
    return `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
  }

  async function submitQuestion(text: string) {
    const trimmed = text.trim();
    if (!trimmed || sending) return;

    const userMsg: ChatMessage = {
      id: genId(),
      role: "user",
      text: trimmed,
    };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setSending(true);

    try {
      const fd = new FormData();
      fd.append("analysis_id", analysisId);
      fd.append("text", trimmed);

      const res = await apiFetch("/api/v1/qa", {
        method: "POST",
        body: fd,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: QAAnswerResponse = await res.json();

      const assistantMsg: ChatMessage = {
        id: genId(),
        role: "assistant",
        text: data.answer_tr,
        intent: data.intent,
        confidence_band: data.confidence_band,
        evidence_tr: data.evidence_tr,
        cohort_scope_tr: data.cohort_scope_tr,
      };
      setMessages((m) => [...m, assistantMsg]);
    } catch {
      setMessages((m) => [
        ...m,
        { id: genId(), role: "error", text: tr.qa.error },
      ]);
    } finally {
      setSending(false);
      // Smooth-scroll to the latest bubble after the next paint.
      setTimeout(() => {
        listEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
      }, 50);
    }
  }

  function toggleEvidence(id: string) {
    setExpanded((e) => ({ ...e, [id]: !e[id] }));
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="panel p-5"
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-subtle-foreground">
            {tr.qa.section_title}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {tr.qa.section_subtitle}
          </p>
        </div>
        <span className="grid h-8 w-8 place-items-center rounded-full bg-brand-soft text-brand">
          <MessageCircleQuestion size={14} />
        </span>
      </div>

      {/* Suggestion chips */}
      <div className="mt-4 flex flex-wrap gap-2">
        {CHIP_INTENTS.map((c) => (
          <button
            key={c.intent}
            type="button"
            disabled={sending}
            onClick={() => submitQuestion(c.label)}
            className="inline-flex items-center gap-1.5 rounded-pill border border-brand/30 bg-brand-soft px-3 py-1.5 text-xs font-medium text-brand transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Sparkles size={11} />
            {c.label}
          </button>
        ))}
      </div>

      {/* Messages */}
      {messages.length > 0 && (
        <div className="mt-5 flex max-h-[420px] flex-col gap-3 overflow-y-auto pr-1">
          <AnimatePresence initial={false}>
            {messages.map((m) => (
              <motion.div
                key={m.id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className={
                  m.role === "user"
                    ? "flex justify-end"
                    : "flex justify-start"
                }
              >
                {m.role === "user" ? (
                  <div className="max-w-[80%] rounded-card bg-brand-gradient px-4 py-2 text-sm text-white">
                    {m.text}
                  </div>
                ) : m.role === "error" ? (
                  <div className="max-w-[80%] rounded-card border border-danger/30 bg-danger/10 px-4 py-2 text-sm text-danger">
                    {m.text}
                  </div>
                ) : (
                  <div className="max-w-[88%] rounded-card border border-border bg-panel-elev/60 px-4 py-3">
                    <div className="mb-1.5 flex items-center gap-2">
                      {m.intent && (
                        <span className="inline-flex rounded-pill border border-brand/30 bg-brand-soft px-2 py-0.5 text-[10px] font-semibold text-brand">
                          {intentLabel(m.intent)}
                        </span>
                      )}
                      {m.confidence_band && (
                        <span
                          className={`inline-flex rounded-pill border px-2 py-0.5 text-[10px] font-medium ${
                            BAND_PILL[m.confidence_band]
                          }`}
                        >
                          {BAND_LABEL[m.confidence_band]}
                        </span>
                      )}
                    </div>
                    <p className="text-sm leading-relaxed text-foreground">
                      {m.text}
                    </p>

                    {m.evidence_tr && m.evidence_tr.length > 0 && (
                      <div className="mt-2">
                        <button
                          type="button"
                          onClick={() => toggleEvidence(m.id)}
                          className="inline-flex items-center gap-1 rounded-pill border border-border bg-panel-elev px-2 py-0.5 text-[10px] font-medium text-muted-foreground transition hover:text-foreground"
                        >
                          {tr.qa.evidence_toggle}
                          {expanded[m.id] ? (
                            <ChevronUp size={10} />
                          ) : (
                            <ChevronDown size={10} />
                          )}
                        </button>
                        {expanded[m.id] && (
                          <ul className="mt-2 flex flex-col gap-1 border-l border-border pl-3">
                            {m.evidence_tr.map((ev, i) => (
                              <li
                                key={i}
                                className="text-[11px] leading-relaxed text-muted-foreground"
                              >
                                • {ev}
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
          <div ref={listEndRef} />
        </div>
      )}

      {/* Input */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submitQuestion(input);
        }}
        className="mt-4 flex items-center gap-2"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={tr.qa.placeholder}
          maxLength={200}
          disabled={sending}
          className="flex-1 rounded-pill border border-border bg-panel-elev px-4 py-2 text-sm text-foreground placeholder:text-subtle-foreground focus:border-brand/50 focus:outline-none focus:ring-2 focus:ring-brand/20 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className="inline-flex items-center gap-1.5 rounded-pill bg-brand-gradient px-4 py-2 text-sm font-semibold text-white brand-glow transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {sending ? tr.qa.sending : tr.qa.send}
          {!sending && <Send size={12} />}
        </button>
      </form>
    </motion.div>
  );
}
