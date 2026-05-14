"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, MessageSquare, ArrowRight, RefreshCw, AlertTriangle, ShieldCheck } from "lucide-react";
import { AnalysisProgress } from "@/components/analysis-progress";
import { AgentPipeline } from "@/components/dashboard/agent-pipeline";
import { BodyHeatmap, type HeatmapRegion } from "@/components/dashboard/body-heatmap";
import { apiFetch } from "@/lib/api";

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

interface AnalysisResult {
  recommended_size: string | null;
  confidence_score: number | null;
  confidence_pct: string | null;
  explanation_tr: string | null;
  detailed_explanation_tr: string | null;
  uncertainty_tr: string | null;
  risk_level: "low" | "medium" | "high" | null;
  risk_level_tr: string | null;
  risk_factors_tr: string[] | null;
  community_insights_tr: string[] | null;
  risk_heatmap: HeatmapRegion[] | null;
}

function phaseToStep(phase: Phase): number {
  const map: Record<Phase, number> = {
    idle: 0, uploading: 0, step_1: 1, step_2: 2, step_3: 3,
    step_4: 4, step_5: 5, step_6: 6, done: 6, error: 0,
  };
  return map[phase];
}

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function confidenceColor(score: number): string {
  const pct = score * 100;
  if (pct > 70) return "bg-success";
  if (pct >= 50) return "bg-warning";
  return "bg-danger";
}

const RISK_PILL: Record<string, string> = {
  low: "text-success bg-success/10 border-success/30",
  medium: "text-warning bg-warning/10 border-warning/30",
  high: "text-danger bg-danger/10 border-danger/30",
};

export default function AnalyzePage() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [hasProfile, setHasProfile] = useState<boolean | null>(null);
  const [garmentFile, setGarmentFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>("");

  const resultRef = useRef<AnalysisResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Probe the auth-scoped profile endpoint to decide whether onboarding is
    // needed before letting the user run an analysis.
    apiFetch("/api/v1/profile/me")
      .then((r) => setHasProfile(r.ok))
      .catch(() => setHasProfile(false));
  }, []);

  useEffect(() => {
    return () => { if (previewUrl) URL.revokeObjectURL(previewUrl); };
  }, [previewUrl]);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setGarmentFile(file);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(URL.createObjectURL(file));
  }

  function handleDropZoneClick() {
    fileInputRef.current?.click();
  }

  function startStepTimers() {
    const order: Phase[] = [
      "uploading", "step_1", "step_2", "step_3", "step_4", "step_5", "step_6", "done", "error",
    ];
    const advance = (target: Phase, delay: number) => {
      setTimeout(() => {
        setPhase((prev) => {
          const prevIdx = order.indexOf(prev);
          const targetIdx = order.indexOf(target);
          if (prevIdx < targetIdx && prev !== "done" && prev !== "error") return target;
          return prev;
        });
      }, delay);
    };

    advance("step_1", 400);
    advance("step_2", 900);
    advance("step_3", 1600);
    advance("step_4", 2300);
    advance("step_5", 2900);
    advance("step_6", 3400);
    setTimeout(() => { if (resultRef.current) setPhase("done"); }, 3600);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!garmentFile || !hasProfile) return;

    resultRef.current = null;
    setResult(null);
    setErrorMsg("");
    setPhase("uploading");
    startStepTimers();

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 35000);

    try {
      const fd = new FormData();
      fd.append("garment_image", garmentFile);

      const res = await apiFetch("/api/v1/analyze", {
        method: "POST", body: fd, signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const detail = (body as { detail?: string }).detail;
        throw new Error(detail ?? `HTTP ${res.status}`);
      }

      const data: AnalysisResult = await res.json();
      resultRef.current = data;
      setResult(data);

      const DONE_ELIGIBLE: Phase[] = ["step_2", "step_3", "step_4", "step_5", "step_6"];
      setPhase((prev) => (DONE_ELIGIBLE.includes(prev) ? "done" : prev));
    } catch (err) {
      clearTimeout(timeoutId);
      const isAbort = err instanceof Error && err.name === "AbortError";
      setPhase("error");
      setErrorMsg(
        isAbort
          ? "Analiz zaman aşımına uğradı. Lütfen tekrar deneyin."
          : err instanceof Error && err.message && !err.message.startsWith("HTTP")
          ? err.message
          : "Analiz sırasında bir hata oluştu. Lütfen tekrar deneyin."
      );
    }
  }

  function handleReset() {
    setPhase("idle");
    setGarmentFile(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
    }
    setResult(null);
    setErrorMsg("");
    resultRef.current = null;
  }

  const isInProgress =
    phase === "uploading" || phase === "step_1" || phase === "step_2" ||
    phase === "step_3" || phase === "step_4" || phase === "step_5" || phase === "step_6";

  // -------- Renderers --------

  function renderNoProfile() {
    return (
      <motion.div
        key="no-profile"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -12 }}
        className="panel flex flex-col items-start gap-4 p-8"
      >
        <h2 className="text-lg font-semibold text-foreground">
          Önce profilini oluştur
        </h2>
        <p className="text-sm text-muted-foreground">
          Beden öneri sistemi için boy, kilo ve fit tercihin gerekli.
        </p>
        <Link
          href="/onboarding"
          className="inline-flex items-center gap-2 rounded-pill bg-brand-gradient px-4 py-2 text-sm font-semibold text-white transition hover:brightness-110"
        >
          Profil Oluştur <ArrowRight size={14} />
        </Link>
      </motion.div>
    );
  }

  function renderUploadForm() {
    return (
      <motion.form
        key="upload-form"
        onSubmit={handleSubmit}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -12 }}
        className="grid grid-cols-1 gap-6 lg:grid-cols-[1.1fr_1fr]"
      >
        {/* Drop zone */}
        <div className="panel p-6">
          <p className="text-sm font-medium text-foreground">Kıyafet Görseli</p>
          <p className="mt-1 text-xs text-subtle-foreground">
            Yüklediğin görsel yalnızca analizde kullanılır.
          </p>

          <button
            type="button"
            onClick={handleDropZoneClick}
            className="mt-4 flex min-h-[220px] w-full flex-col items-center justify-center gap-3 rounded-card border border-dashed border-border bg-panel-elev transition hover:border-brand/50 focus:outline-none focus-visible:ring-2 ring-brand"
          >
            {previewUrl ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img
                src={previewUrl}
                alt="Seçilen kıyafet görseli"
                className="max-h-[200px] rounded-md object-contain"
              />
            ) : (
              <>
                <span className="grid h-11 w-11 place-items-center rounded-full bg-brand-soft text-brand">
                  <Upload size={18} />
                </span>
                <span className="text-sm font-medium text-foreground">
                  Görsel seçmek için tıkla
                </span>
                <span className="text-xs text-subtle-foreground">
                  JPG, JPEG veya PNG · maks 8 MB
                </span>
              </>
            )}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,.jpg,.jpeg,.png"
            className="hidden"
            onChange={handleFileChange}
          />
          {garmentFile && (
            <p className="mt-2 truncate text-xs text-subtle-foreground">
              {garmentFile.name}
            </p>
          )}
        </div>

        {/* Right column: explanatory + submit */}
        <div className="panel flex flex-col gap-4 p-6">
          <p className="text-sm font-medium text-foreground">Analiz Hakkında</p>
          <ul className="flex flex-col gap-3 text-sm text-muted-foreground">
            <li className="flex gap-3">
              <span className="mt-1 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-brand-soft text-[10px] font-bold text-brand">
                1
              </span>
              Görseli analiz ederek kesim, kumaş ve marka kalıbı tahmin edilir.
            </li>
            <li className="flex gap-3">
              <span className="mt-1 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-brand-soft text-[10px] font-bold text-brand">
                2
              </span>
              Profilindeki ölçüler ve benzer kullanıcı yorumları ile karşılaştırılır.
            </li>
            <li className="flex gap-3">
              <span className="mt-1 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-brand-soft text-[10px] font-bold text-brand">
                3
              </span>
              Beden önerisi, güven skoru ve risk açıklaması üretilir.
            </li>
          </ul>

          <div className="flex-1" />

          <button
            type="submit"
            disabled={!garmentFile || !hasProfile}
            className="inline-flex items-center justify-center gap-2 rounded-pill bg-brand-gradient px-5 py-3 text-sm font-semibold text-white brand-glow transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-30"
          >
            Analizi Başlat <ArrowRight size={14} />
          </button>
        </div>
      </motion.form>
    );
  }

  function renderProgress() {
    const isFinalizingStep = phase === "step_6";
    return (
      <motion.div
        key="progress"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -12 }}
        className="flex flex-col gap-5"
      >
        <div className="panel flex flex-col gap-5 p-6">
          <div className="flex items-center gap-2">
            <span className="grid h-8 w-8 place-items-center rounded-full bg-brand-soft text-brand">
              <RefreshCw size={14} className="animate-spin" />
            </span>
            <p className="text-sm font-medium text-foreground">
              {isFinalizingStep
                ? "Sonuçlar hazırlanıyor…"
                : "Analiz çalışıyor…"}
            </p>
          </div>
          <AnalysisProgress currentStep={phaseToStep(phase)} />
        </div>
        {/* Live multi-agent breakdown — additive, shows judges the architecture */}
        <AgentPipeline phase={phase} />
      </motion.div>
    );
  }

  function renderResults() {
    if (!result) return null;
    const {
      recommended_size, confidence_score, confidence_pct, explanation_tr,
      detailed_explanation_tr, uncertainty_tr, risk_level, risk_level_tr,
      risk_factors_tr, community_insights_tr, risk_heatmap,
    } = result;

    const safeRiskFactors = risk_factors_tr ?? [];
    const safeInsights = community_insights_tr ?? [];
    const safeConfidence = confidence_score ?? 0;
    const riskPill = risk_level ? RISK_PILL[risk_level] : "";

    return (
      <motion.div
        key="results"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -12 }}
        transition={{ duration: 0.4 }}
        className="flex flex-col gap-5"
      >
        {/* Compact "what ran" confirmation strip above the result panels */}
        <AgentPipeline phase="done" variant="compact" />

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1.15fr_1fr]">
        {/* Big recommendation card */}
        <div className="panel flex flex-col gap-5 p-6">
          <div className="flex items-end justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-subtle-foreground">
                Beden Önerisi
              </p>
              <p className="mt-2 text-6xl font-bold text-foreground">
                {recommended_size ?? "—"}
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs font-semibold uppercase tracking-wider text-subtle-foreground">
                Güven Skoru
              </p>
              <p className="mt-2 text-3xl font-bold brand-text">
                {confidence_pct ?? "—"}
              </p>
            </div>
          </div>

          <div className="h-2 overflow-hidden rounded-full bg-panel-elev">
            <motion.div
              className={`h-full rounded-full ${confidenceColor(safeConfidence)}`}
              initial={{ width: 0 }}
              animate={{ width: `${Math.round(safeConfidence * 100)}%` }}
              transition={{ duration: 0.7, ease: "easeOut" }}
            />
          </div>

          {explanation_tr && (
            <p className="text-sm leading-relaxed text-muted-foreground">
              <span className="font-medium text-foreground">Açıklama: </span>
              {explanation_tr}
            </p>
          )}
          {detailed_explanation_tr && (
            <div className="rounded-card border border-brand/25 bg-brand-soft p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-brand">
                Detaylı Analiz
              </p>
              <p className="mt-2 text-sm leading-relaxed text-foreground">
                {detailed_explanation_tr}
              </p>
            </div>
          )}
          {uncertainty_tr && (
            <div className="rounded-md border border-warning/30 bg-warning/10 p-3 text-xs leading-relaxed text-warning">
              <span className="mr-1 inline-flex items-center gap-1 font-medium">
                <AlertTriangle size={12} /> Belirsizlik:
              </span>
              {uncertainty_tr}
            </div>
          )}

          <button
            type="button"
            onClick={handleReset}
            className="inline-flex w-fit items-center gap-2 rounded-pill border border-border bg-panel-elev px-4 py-2 text-xs font-medium text-muted-foreground transition hover:text-foreground"
          >
            <RefreshCw size={12} /> Yeni Analiz
          </button>
        </div>

        {/* Right column: Risk + Community */}
        <div className="flex flex-col gap-5">
          <div className="panel p-5">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wider text-subtle-foreground">
                Satın Alma Riski
              </p>
              <span className="grid h-8 w-8 place-items-center rounded-full bg-brand-soft text-brand">
                <ShieldCheck size={14} />
              </span>
            </div>
            <p className="mt-2 text-lg font-semibold text-foreground">
              {risk_level_tr ?? "—"}
            </p>
            {risk_level && (
              <span
                className={`mt-2 inline-flex w-fit rounded-pill border px-2.5 py-0.5 text-[11px] font-medium ${riskPill}`}
              >
                {risk_level_tr}
              </span>
            )}
            {safeRiskFactors.length > 0 && (
              <ul className="mt-4 flex flex-col gap-2">
                {safeRiskFactors.map((factor, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm text-muted-foreground"
                  >
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand/70" />
                    {factor}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="panel p-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-subtle-foreground">
              Topluluk İçgörüleri
            </p>
            {safeInsights.length === 0 ? (
              <p className="mt-3 text-sm text-muted-foreground">
                Henüz yeterli kullanıcı yorumu bulunmuyor.
              </p>
            ) : (
              <ul className="mt-3 flex flex-col gap-3">
                {safeInsights.map((insight, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm leading-relaxed text-muted-foreground"
                  >
                    <MessageSquare
                      className="mt-0.5 h-4 w-4 shrink-0 text-brand/70"
                    />
                    {insight}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
        </div>

        {risk_heatmap && risk_heatmap.length > 0 && (
          <BodyHeatmap regions={risk_heatmap} />
        )}
      </motion.div>
    );
  }

  function renderError() {
    return (
      <motion.div
        key="error"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -12 }}
        className="panel flex flex-col items-start gap-3 p-6"
      >
        <span className="grid h-9 w-9 place-items-center rounded-full bg-danger/15 text-danger">
          <AlertTriangle size={16} />
        </span>
        <p className="text-sm text-muted-foreground">
          {errorMsg || "Analiz sırasında bir hata oluştu."}
        </p>
        <button
          type="button"
          onClick={handleReset}
          className="inline-flex items-center gap-2 rounded-pill bg-brand-gradient px-4 py-2 text-sm font-semibold text-white transition hover:brightness-110"
        >
          Tekrar Dene <RefreshCw size={12} />
        </button>
      </motion.div>
    );
  }

  // -------- Main render --------

  return (
    <div className="flex flex-col gap-6 pt-2">
      <header>
        <span className="inline-flex rounded-pill border border-brand/30 bg-brand-soft px-3 py-1 text-[11px] font-medium text-brand">
          Analiz
        </span>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-foreground">
          Kıyafetin sende
          <br />
          <span className="brand-text">nasıl duracağını gör.</span>
        </h1>
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
          Bir kıyafet görseli yükle, AI sana özel beden önerisini hazırlasın.
        </p>
      </header>

      <AnimatePresence mode="wait">
        {phase === "idle" && hasProfile === false && renderNoProfile()}
        {phase === "idle" && hasProfile === true && renderUploadForm()}
        {isInProgress && renderProgress()}
        {phase === "done" && renderResults()}
        {phase === "error" && renderError()}
      </AnimatePresence>
    </div>
  );
}
