"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, MessageSquare } from "lucide-react";
import { AnalysisProgress } from "@/components/analysis-progress";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

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
  confidence_score: number | null;   // float 0-1 from backend
  confidence_pct: string | null;     // "%81" formatted string from backend
  explanation_tr: string | null;
  uncertainty_tr: string | null;
  risk_level: "low" | "medium" | "high" | null;
  risk_level_tr: string | null;
  risk_factors_tr: string[] | null;
  community_insights_tr: string[] | null;
}

// Map phase to a numeric step for the progress component (0 = uploading, 1-6)
function phaseToStep(phase: Phase): number {
  const map: Record<Phase, number> = {
    idle: 0,
    uploading: 0,
    step_1: 1,
    step_2: 2,
    step_3: 3,
    step_4: 4,
    step_5: 5,
    step_6: 6,
    done: 6,
    error: 0,
  };
  return map[phase];
}

const BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Confidence bar color
// ---------------------------------------------------------------------------

function confidenceColor(score: number): string {
  const pct = score * 100;
  if (pct > 70) return "bg-green-500";
  if (pct >= 50) return "bg-amber-400";
  return "bg-red-500";
}

// ---------------------------------------------------------------------------
// Risk badge — uses English risk_level enum, not the Turkish display string
// ---------------------------------------------------------------------------

const RISK_BADGE_MAP: Record<string, string> = {
  low:    "bg-green-100 text-green-700",
  medium: "bg-amber-100 text-amber-700",
  high:   "bg-red-100 text-red-700",
};

function riskBadgeClass(level: string): string {
  return RISK_BADGE_MAP[level] ?? "bg-muted text-muted-foreground";
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function AnalyzePage() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [userId, setUserId] = useState<string | null>(null);
  const [garmentFile, setGarmentFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>("");

  // Refs to track async state without stale closures
  const resultRef = useRef<AnalysisResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Read user id from localStorage on mount
  useEffect(() => {
    const id = localStorage.getItem("hiwaloy_user_id");
    setUserId(id);
  }, []);

  // Cleanup preview URL on unmount
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  // --------------------------------------------------------------------------
  // File selection
  // --------------------------------------------------------------------------

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

  // --------------------------------------------------------------------------
  // Step timer progression
  // --------------------------------------------------------------------------

  function startStepTimers() {
    const advance = (target: Phase, delay: number) => {
      setTimeout(() => {
        // Only advance if we haven't already moved past this step
        setPhase((prev) => {
          const order: Phase[] = [
            "uploading",
            "step_1",
            "step_2",
            "step_3",
            "step_4",
            "step_5",
            "step_6",
            "done",
            "error",
          ];
          const prevIdx = order.indexOf(prev);
          const targetIdx = order.indexOf(target);
          // Only advance, never go back; also don't overwrite done/error
          if (
            prevIdx < targetIdx &&
            prev !== "done" &&
            prev !== "error"
          ) {
            return target;
          }
          return prev;
        });
      }, delay);
    };

    // Steps compressed to ~3.5 s so DEMO_MODE (~1 s pipeline) flows naturally.
    // Real Gemini (~5–10 s) will arrive after all timers and the API callback
    // flips to "done" directly; the 35 s AbortController handles actual hangs.
    advance("step_1",  400);
    advance("step_2",  900);
    advance("step_3", 1600);
    advance("step_4", 2300);
    advance("step_5", 2900);
    advance("step_6", 3400);

    // After step_6 fires, flip to done if the API has already returned.
    setTimeout(() => {
      if (resultRef.current) {
        setPhase("done");
      }
    }, 3600);
  }

  // --------------------------------------------------------------------------
  // Submit
  // --------------------------------------------------------------------------

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!garmentFile || !userId) return;

    resultRef.current = null;
    setResult(null);
    setErrorMsg("");
    setPhase("uploading");
    startStepTimers();

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 35000);

    try {
      const fd = new FormData();
      fd.append("user_id", userId);
      fd.append("garment_image", garmentFile);

      const res = await fetch(`${BASE}/api/v1/analyze`, {
        method: "POST",
        body: fd,
        signal: controller.signal,
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

      // Flip to done as soon as we're past step_1; the 3.6s timer handles the
      // case where the API beats the timers entirely.
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

  // --------------------------------------------------------------------------
  // Reset
  // --------------------------------------------------------------------------

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

  // --------------------------------------------------------------------------
  // Derived booleans
  // --------------------------------------------------------------------------

  const isInProgress =
    phase === "uploading" ||
    phase === "step_1" ||
    phase === "step_2" ||
    phase === "step_3" ||
    phase === "step_4" ||
    phase === "step_5" ||
    phase === "step_6";

  // --------------------------------------------------------------------------
  // Render helpers
  // --------------------------------------------------------------------------

  function renderNoProfile() {
    return (
      <motion.div
        key="no-profile"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -12 }}
        className="flex flex-col items-center gap-4 rounded-xl border border-border bg-background p-8 text-center shadow-sm"
      >
        <p className="text-sm text-muted-foreground">
          Önce profilinizi oluşturmanız gerekiyor.
        </p>
        <Link
          href="/onboarding"
          className="inline-flex items-center gap-2 rounded-lg bg-foreground px-4 py-2 text-sm font-medium text-background transition-opacity hover:opacity-80"
        >
          Profil Oluştur
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
        className="flex flex-col gap-6"
      >
        {/* Drop zone */}
        <div className="flex flex-col gap-2">
          <span className="text-sm font-medium text-foreground">
            Kıyafet Görseli
          </span>
          <button
            type="button"
            onClick={handleDropZoneClick}
            className="flex min-h-[180px] w-full flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-border bg-muted/40 transition-colors hover:border-foreground/30 hover:bg-muted/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-foreground/20"
          >
            {previewUrl ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img
                src={previewUrl}
                alt="Seçilen kıyafet görseli"
                className="max-h-[160px] rounded-lg object-contain"
              />
            ) : (
              <>
                <Upload className="h-8 w-8 text-muted-foreground/50" />
                <span className="text-sm text-muted-foreground">
                  Görsel seçmek için tıklayın
                </span>
                <span className="text-xs text-muted-foreground/60">
                  JPEG veya PNG, maks 8 MB
                </span>
              </>
            )}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png"
            className="hidden"
            onChange={handleFileChange}
          />
          {garmentFile && (
            <p className="text-xs text-muted-foreground">{garmentFile.name}</p>
          )}
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={!garmentFile || !userId}
          className="w-full rounded-lg bg-foreground px-4 py-3 text-sm font-semibold text-background transition-opacity hover:opacity-80 disabled:cursor-not-allowed disabled:opacity-30"
        >
          Analizi Başlat
        </button>
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
        className="flex flex-col gap-6 rounded-xl border border-border bg-background p-6 shadow-sm"
      >
        <p className="text-sm font-medium text-foreground">
          {isFinalizingStep
            ? "Sonuçlar hazırlanıyor, lütfen bekleyin…"
            : "Analiziniz hazırlanıyor…"}
        </p>
        <AnalysisProgress currentStep={phaseToStep(phase)} />
      </motion.div>
    );
  }

  function renderResults() {
    if (!result) return null;
    const {
      recommended_size,
      confidence_score,
      confidence_pct,
      explanation_tr,
      uncertainty_tr,
      risk_level,
      risk_level_tr,
      risk_factors_tr,
      community_insights_tr,
    } = result;

    const safeRiskFactors = risk_factors_tr ?? [];
    const safeInsights = community_insights_tr ?? [];
    const safeConfidence = confidence_score ?? 0;

    return (
      <motion.div
        key="results"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -12 }}
        transition={{ duration: 0.4 }}
        className="flex flex-col gap-6"
      >
        {/* Recommendation card */}
        <div className="rounded-xl border border-border bg-background p-5 shadow-sm">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Beden Önerisi
          </p>
          <div className="flex flex-col items-center gap-1 py-2">
            <span className="text-4xl font-bold text-foreground">
              {recommended_size ?? "—"}
            </span>
            <span className="text-sm text-muted-foreground">
              Güven: {confidence_pct ?? "—"}
            </span>
          </div>
          {explanation_tr && (
            <p className="mt-3 text-sm text-muted-foreground leading-relaxed">
              <span className="mr-1 font-medium text-foreground">Açıklama:</span>
              {explanation_tr}
            </p>
          )}
          {uncertainty_tr && (
            <p className="mt-2 text-xs text-muted-foreground/70 leading-relaxed italic">
              {uncertainty_tr}
            </p>
          )}
        </div>

        {/* Confidence bar */}
        <div className="rounded-xl border border-border bg-background p-5 shadow-sm">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Güven Skoru
          </p>
          <div className="flex items-center gap-3">
            <div className="relative h-2.5 flex-1 overflow-hidden rounded-full bg-muted">
              <motion.div
                className={`h-full rounded-full ${confidenceColor(safeConfidence)}`}
                initial={{ width: 0 }}
                animate={{ width: `${Math.round(safeConfidence * 100)}%` }}
                transition={{ duration: 0.7, ease: "easeOut" }}
              />
            </div>
            <span className="w-10 text-right text-sm font-medium text-foreground">
              {confidence_pct ?? "—"}
            </span>
          </div>
        </div>

        {/* Risk panel */}
        <div className="rounded-xl border border-border bg-background p-5 shadow-sm">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Risk Değerlendirmesi
          </p>
          <span
            className={`inline-block rounded-full px-3 py-0.5 text-xs font-semibold ${riskBadgeClass(risk_level ?? "")}`}
          >
            {risk_level_tr ?? "—"}
          </span>
          {safeRiskFactors.length > 0 && (
            <ul className="mt-4 flex flex-col gap-2">
              {safeRiskFactors.map((factor, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-muted-foreground/50" />
                  {factor}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Community insights */}
        <div className="rounded-xl border border-border bg-background p-5 shadow-sm">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Topluluk Yorumları
          </p>
          {safeInsights.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Henüz yeterli kullanıcı yorumu bulunmuyor.
            </p>
          ) : (
            <ul className="flex flex-col gap-3">
              {safeInsights.map((insight, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                  <MessageSquare className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground/50" />
                  {insight}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Reset button */}
        <button
          type="button"
          onClick={handleReset}
          className="w-full rounded-lg border border-border bg-background px-4 py-3 text-sm font-medium text-foreground transition-colors hover:bg-muted"
        >
          Yeni Analiz
        </button>
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
        className="flex flex-col items-center gap-4 rounded-xl border border-border bg-background p-8 text-center shadow-sm"
      >
        <p className="text-sm text-muted-foreground">
          {errorMsg || "Analiz sırasında bir hata oluştu."}
        </p>
        <button
          type="button"
          onClick={handleReset}
          className="inline-flex items-center gap-2 rounded-lg bg-foreground px-4 py-2 text-sm font-medium text-background transition-opacity hover:opacity-80"
        >
          Tekrar Dene
        </button>
      </motion.div>
    );
  }

  // --------------------------------------------------------------------------
  // Main render
  // --------------------------------------------------------------------------

  return (
    <main className="min-h-dvh py-12">
      <div className="mx-auto w-full max-w-[600px] px-4">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Kıyafet Analizi
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Kıyafet görselini yükle, yapay zeka sizin için analiz etsin.
          </p>
        </div>

        <AnimatePresence mode="wait">
          {/* No profile */}
          {phase === "idle" && !userId && renderNoProfile()}

          {/* Upload form */}
          {phase === "idle" && userId && renderUploadForm()}

          {/* In progress */}
          {isInProgress && renderProgress()}

          {/* Results */}
          {phase === "done" && renderResults()}

          {/* Error */}
          {phase === "error" && renderError()}
        </AnimatePresence>
      </div>
    </main>
  );
}
