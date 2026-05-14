"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  ArrowRight,
  Loader2,
  AlertTriangle,
  Tag,
  ShieldCheck,
} from "lucide-react";
import { apiFetch } from "@/lib/api";

interface Suggestion {
  garment_id: string;
  name: string;
  brand: string;
  category: string;
  fit_type: string;
  fabric: string;
  price_tl: number;
  reason_tr: string;
  fit_warning_tr: string | null;
}

interface StylistResponse {
  suggestions: Suggestion[];
  stylist_note_tr: string;
  uncertainty_tr: string | null;
  query_echo: string;
  max_price_tl: number | null;
  off_topic: boolean;
}

type Phase =
  | { type: "idle" }
  | { type: "loading" }
  | { type: "ready"; data: StylistResponse }
  | { type: "error"; message: string };

const SUGGESTIONS = [
  "500 TL altında oversize tişört",
  "Hafta sonu için casual gömlek",
  "Yazlık ince keten gömlek",
  "Spor ceket önerisi",
];

const CATEGORY_LABEL: Record<string, string> = {
  shirt: "Gömlek",
  tshirt: "Tişört / Sweat",
  jeans: "Pantolon",
  dress: "Elbise",
  jacket: "Ceket",
};

const FIT_LABEL: Record<string, string> = {
  "slim-cut": "Dar kesim",
  regular: "Normal kesim",
  relaxed: "Rahat kesim",
  oversize: "Oversize",
};

export default function StilistPage() {
  const [query, setQuery] = useState("");
  const [phase, setPhase] = useState<Phase>({ type: "idle" });

  async function submit(text: string) {
    const trimmed = text.trim();
    if (!trimmed) return;
    setPhase({ type: "loading" });
    try {
      const fd = new FormData();
      fd.append("query", trimmed);
      const res = await apiFetch("/api/v1/stylist", { method: "POST", body: fd });
      if (res.status === 409) {
        const body = await res.json().catch(() => ({}));
        setPhase({
          type: "error",
          message:
            (body as { detail?: string }).detail ??
            "Önce profilini tamamlamalısın.",
        });
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: StylistResponse = await res.json();
      setPhase({ type: "ready", data });
    } catch (err) {
      setPhase({
        type: "error",
        message:
          err instanceof Error && err.message
            ? "Stilist şu an cevap vermedi."
            : "Bir hata oluştu.",
      });
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    submit(query);
  }

  function handleChip(text: string) {
    setQuery(text);
    submit(text);
  }

  return (
    <div className="flex flex-col gap-6 pt-2">
      <header>
        <span className="inline-flex items-center gap-2 rounded-pill border border-brand/30 bg-brand-soft px-3 py-1 text-[11px] font-medium text-brand">
          <Sparkles size={12} /> Stilist
        </span>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-foreground">
          AI&apos;dan kişisel
          <br />
          <span className="brand-text">alışveriş asistanı.</span>
        </h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Bütçeni, tarzını ya da bağlamı yaz — vücut profiline ve geçmiş
          analizlerine uygun 3 ürün, gerekçesiyle birlikte gelir.
        </p>
      </header>

      <form onSubmit={handleSubmit} className="panel p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="örn. 500 TL altında oversize tişört öner"
            className="h-12 flex-1 rounded-pill border border-border bg-panel-elev px-5 text-sm text-foreground placeholder:text-subtle-foreground focus:outline-none focus:ring-2 ring-brand"
            maxLength={280}
          />
          <button
            type="submit"
            disabled={phase.type === "loading" || !query.trim()}
            className="inline-flex items-center justify-center gap-2 rounded-pill bg-brand-gradient px-6 py-3 text-sm font-semibold text-white brand-glow transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {phase.type === "loading" ? (
              <>
                <Loader2 size={14} className="animate-spin" /> Düşünüyor…
              </>
            ) : (
              <>
                Öneri Al <ArrowRight size={14} />
              </>
            )}
          </button>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => handleChip(s)}
              className="rounded-pill border border-border bg-panel-elev px-3 py-1.5 text-xs text-muted-foreground transition hover:border-brand/40 hover:text-foreground"
            >
              {s}
            </button>
          ))}
        </div>
      </form>

      <AnimatePresence mode="wait">
        {phase.type === "loading" && (
          <motion.div
            key="loading"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="panel flex items-center gap-3 p-6 text-sm text-muted-foreground"
          >
            <Loader2 className="animate-spin text-brand" size={16} />
            Stilist, kataloğu profiline göre değerlendiriyor…
          </motion.div>
        )}

        {phase.type === "error" && (
          <motion.div
            key="error"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="panel flex items-start gap-3 p-5"
          >
            <AlertTriangle className="mt-0.5 text-danger" size={16} />
            <div>
              <p className="text-sm font-medium text-foreground">
                Bir şey ters gitti
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                {phase.message}
              </p>
            </div>
          </motion.div>
        )}

        {phase.type === "ready" && (
          <motion.section
            key="ready"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35 }}
            className="flex flex-col gap-5"
          >
            <div className="panel p-5">
              <div className="flex items-start gap-3">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-brand-soft text-brand">
                  <Sparkles size={16} />
                </span>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-subtle-foreground">
                    Stilist notu
                  </p>
                  <p className="mt-1 text-sm leading-relaxed text-foreground">
                    {phase.data.stylist_note_tr}
                  </p>
                  {phase.data.uncertainty_tr && (
                    <p className="mt-2 text-xs italic text-subtle-foreground">
                      {phase.data.uncertainty_tr}
                    </p>
                  )}
                </div>
              </div>
            </div>

            {phase.data.suggestions.length === 0 ? (
              phase.data.off_topic ? null : (
                <div className="panel p-6 text-sm text-muted-foreground">
                  Bu kriterlere uygun ürün bulunamadı. Bütçeyi veya
                  kategoriyi değiştirerek tekrar dener misin?
                </div>
              )
            ) : (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                {phase.data.suggestions.map((s, idx) => (
                  <SuggestionCard key={s.garment_id} item={s} index={idx} />
                ))}
              </div>
            )}
          </motion.section>
        )}
      </AnimatePresence>
    </div>
  );
}

function SuggestionCard({
  item,
  index,
}: {
  item: Suggestion;
  index: number;
}) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.08 }}
      className="panel flex h-full flex-col gap-3 p-5"
    >
      <div className="flex items-center justify-between">
        <span className="inline-flex items-center gap-1 rounded-pill border border-border bg-panel-elev px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-subtle-foreground">
          {CATEGORY_LABEL[item.category] ?? item.category}
        </span>
        <span className="inline-flex items-center gap-1 rounded-pill bg-brand-soft px-2.5 py-0.5 text-[11px] font-semibold text-brand">
          <Tag size={11} /> {item.price_tl.toLocaleString("tr-TR")} TL
        </span>
      </div>

      <div>
        <p className="text-sm font-semibold text-foreground">{item.name}</p>
        <p className="text-xs text-subtle-foreground">{item.brand}</p>
      </div>

      <div className="flex flex-wrap gap-1.5">
        <span className="rounded-pill border border-border bg-panel-elev px-2 py-0.5 text-[10px] text-muted-foreground">
          {FIT_LABEL[item.fit_type] ?? item.fit_type}
        </span>
        <span
          className="rounded-pill border border-border bg-panel-elev px-2 py-0.5 text-[10px] text-muted-foreground"
          title={item.fabric}
        >
          {item.fabric.split(",")[0]}
        </span>
      </div>

      <p className="text-sm leading-relaxed text-muted-foreground">
        <span className="font-medium text-foreground">Neden bu?</span>{" "}
        {item.reason_tr}
      </p>

      {item.fit_warning_tr && (
        <div className="mt-auto flex items-start gap-2 rounded-md border border-warning/30 bg-warning/10 p-2 text-[11px] leading-relaxed text-warning">
          <ShieldCheck size={12} className="mt-0.5 shrink-0" />
          {item.fit_warning_tr}
        </div>
      )}
    </motion.article>
  );
}
