"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Upload,
  ArrowRight,
  Pencil,
  CheckCircle2,
  ImageIcon,
  ImageOff,
} from "lucide-react";

type FitPreference = "slim" | "regular" | "relaxed" | "oversize";

const FIT_OPTIONS: { value: FitPreference; label: string }[] = [
  { value: "slim", label: "Dar Kesim" },
  { value: "regular", label: "Normal Kesim" },
  { value: "relaxed", label: "Rahat Kesim" },
  { value: "oversize", label: "Oversize" },
];

const FIT_LABEL: Record<FitPreference, string> = {
  slim: "Dar Kesim",
  regular: "Normal Kesim",
  relaxed: "Rahat Kesim",
  oversize: "Oversize",
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface SavedProfile {
  height: number;
  weight: number;
  fit: FitPreference;
  hasBodyImage: boolean;
}

type View = "loading" | "summary" | "form";

export default function OnboardingPage() {
  const router = useRouter();

  const [view, setView] = useState<View>("loading");
  const [saved, setSaved] = useState<SavedProfile | null>(null);

  const [heightCm, setHeightCm] = useState<string>("");
  const [weightKg, setWeightKg] = useState<string>("");
  const [fitPreference, setFitPreference] = useState<FitPreference>("regular");
  const [bodyImage, setBodyImage] = useState<File | null>(null);

  const [heightError, setHeightError] = useState<string>("");
  const [weightError, setWeightError] = useState<string>("");
  const [apiError, setApiError] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // ---------- Load saved profile on mount ----------
  useEffect(() => {
    if (typeof window === "undefined") return;
    const userId = localStorage.getItem("hiwaloy_user_id");
    if (!userId) {
      setView("form");
      return;
    }

    const lsHeight = Number(localStorage.getItem("hiwaloy_height_cm"));
    const lsWeight = Number(localStorage.getItem("hiwaloy_weight_kg"));
    const lsFit = (localStorage.getItem("hiwaloy_fit_preference") ||
      "regular") as FitPreference;

    // Fetch from API for the authoritative has_body_image flag (and as a
    // freshness check). If the API can't find the user, fall back to form.
    fetch(`${API_BASE}/api/v1/profile/${userId}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!data) {
          // Stale user_id — clear it and show the form
          localStorage.removeItem("hiwaloy_user_id");
          localStorage.removeItem("hiwaloy_height_cm");
          localStorage.removeItem("hiwaloy_weight_kg");
          localStorage.removeItem("hiwaloy_fit_preference");
          setView("form");
          return;
        }
        setSaved({
          height: data.height_cm ?? lsHeight,
          weight: data.weight_kg ?? lsWeight,
          fit: (data.fit_preference ?? lsFit) as FitPreference,
          hasBodyImage: Boolean(data.has_body_image),
        });
        setView("summary");
      })
      .catch(() => {
        // Network error — render from localStorage so the page is still useful
        if (lsHeight && lsWeight) {
          setSaved({
            height: lsHeight,
            weight: lsWeight,
            fit: lsFit,
            hasBodyImage: false,
          });
          setView("summary");
        } else {
          setView("form");
        }
      });
  }, []);

  function validate(): boolean {
    let valid = true;
    const h = Number(heightCm);
    if (!heightCm || isNaN(h) || h < 50 || h > 300) {
      setHeightError("Boy 50–300 cm arasında olmalıdır.");
      valid = false;
    } else setHeightError("");
    const w = Number(weightKg);
    if (!weightKg || isNaN(w) || w < 20 || w > 500) {
      setWeightError("Kilo 20–500 kg arasında olmalıdır.");
      valid = false;
    } else setWeightError("");
    return valid;
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setApiError("");
    setSuccessMessage("");
    if (!validate()) return;

    setIsSubmitting(true);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000);

    try {
      const fd = new FormData();
      fd.append("height_cm", String(heightCm));
      fd.append("weight_kg", String(weightKg));
      fd.append("fit_preference", fitPreference);
      if (bodyImage) fd.append("body_image", bodyImage);

      const res = await fetch(`${API_BASE}/api/v1/profile`, {
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

      const data = await res.json();
      const userId: string = data.user_id ?? data.id ?? "";
      if (!userId) {
        setApiError("Profil oluşturulamadı. Lütfen tekrar deneyin.");
        return;
      }

      localStorage.setItem("hiwaloy_user_id", userId);
      localStorage.setItem("hiwaloy_height_cm", String(heightCm));
      localStorage.setItem("hiwaloy_weight_kg", String(weightKg));
      localStorage.setItem("hiwaloy_fit_preference", fitPreference);
      // Notify the sidebar (same tab) so the profile chip refreshes immediately.
      window.dispatchEvent(new Event("hiwaloy:profile-changed"));

      setSuccessMessage("Profiliniz oluşturuldu! Yönlendiriliyor…");
      setSaved({
        height: Number(heightCm),
        weight: Number(weightKg),
        fit: fitPreference,
        hasBodyImage: Boolean(bodyImage),
      });
      setTimeout(() => router.push("/analyze"), 800);
    } catch (err) {
      clearTimeout(timeoutId);
      const isAbort = err instanceof Error && err.name === "AbortError";
      setApiError(
        isAbort
          ? "Bağlantı zaman aşımına uğradı. Lütfen tekrar deneyin."
          : err instanceof Error &&
            err.message &&
            !err.message.startsWith("HTTP")
          ? err.message
          : "Bir hata oluştu. Lütfen tekrar deneyin."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    setBodyImage(e.target.files?.[0] ?? null);
  }

  function openEditor() {
    // Pre-fill the form with current values so the user can adjust them.
    if (saved) {
      setHeightCm(String(saved.height));
      setWeightKg(String(saved.weight));
      setFitPreference(saved.fit);
    }
    setView("form");
  }

  // ---------- Render ----------

  if (view === "loading") {
    return (
      <div className="panel mx-auto w-full max-w-[560px] p-6 text-sm text-subtle-foreground">
        Yükleniyor…
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="mx-auto w-full max-w-[560px] pt-2"
    >
      <header className="mb-8">
        <span className="inline-flex rounded-pill border border-brand/30 bg-brand-soft px-3 py-1 text-[11px] font-medium text-brand">
          Profilim
        </span>
        <h1 className="mt-4 text-3xl font-semibold tracking-tight text-foreground">
          {view === "summary" ? (
            <>
              Kayıtlı profilin
              <br />
              <span className="brand-text">aşağıdaki gibi.</span>
            </>
          ) : (
            <>
              Sana özel beden önerisi için
              <br />
              <span className="brand-text">ölçülerini ekle.</span>
            </>
          )}
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          {view === "summary"
            ? "Her analizde bu bilgiler kullanılır. Güncellemek istersen aşağıdan profili yenileyebilirsin."
            : "Tek seferlik — sonraki her analizde otomatik olarak kullanılacak."}
        </p>
      </header>

      {view === "summary" && saved && (
        <SummaryView profile={saved} onEdit={openEditor} />
      )}

      {view === "form" && (
        <form onSubmit={handleSubmit} noValidate className="panel p-6">
          <div className="flex flex-col gap-5">
            <Field
              id="height_cm"
              label="Boy (cm)"
              placeholder="örn. 175"
              value={heightCm}
              onChange={setHeightCm}
              error={heightError}
              min={50}
              max={300}
            />
            <Field
              id="weight_kg"
              label="Kilo (kg)"
              placeholder="örn. 70"
              value={weightKg}
              onChange={setWeightKg}
              error={weightError}
              min={20}
              max={500}
            />

            <div>
              <p className="mb-2 text-sm font-medium text-foreground">
                Tercih Ettiğin Kesim
              </p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {FIT_OPTIONS.map((opt) => {
                  const active = opt.value === fitPreference;
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => setFitPreference(opt.value)}
                      className={[
                        "rounded-md border px-3 py-2 text-xs font-medium transition",
                        active
                          ? "border-brand/60 bg-brand-soft text-foreground"
                          : "border-border bg-panel-elev text-muted-foreground hover:text-foreground",
                      ].join(" ")}
                    >
                      {opt.label}
                    </button>
                  );
                })}
              </div>
            </div>

            <div>
              <p className="mb-2 text-sm font-medium text-foreground">
                Vücut Fotoğrafı{" "}
                <span className="text-subtle-foreground">(isteğe bağlı)</span>
              </p>
              <div
                role="button"
                tabIndex={0}
                onClick={() => fileInputRef.current?.click()}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ")
                    fileInputRef.current?.click();
                }}
                className="flex cursor-pointer select-none flex-col items-center justify-center gap-2 rounded-card border border-dashed border-border bg-panel-elev px-4 py-6 transition hover:border-brand/50"
              >
                <span className="grid h-9 w-9 place-items-center rounded-full bg-brand-soft text-brand">
                  <Upload size={16} />
                </span>
                <span className="text-sm font-medium text-foreground">
                  {bodyImage ? bodyImage.name : "Fotoğraf seçmek için tıkla"}
                </span>
                <span className="text-xs text-subtle-foreground">
                  JPG, JPEG veya PNG · Eklemen önerinin güven skorunu artırır.
                </span>
              </div>
              <input
                ref={fileInputRef}
                id="body_image"
                type="file"
                accept="image/jpeg,image/png,.jpg,.jpeg,.png"
                onChange={handleFileChange}
                className="hidden"
              />
            </div>

            {apiError && <p className="text-sm text-danger">{apiError}</p>}
            {successMessage && (
              <p className="text-sm text-success">{successMessage}</p>
            )}

            <div className="flex flex-wrap items-center gap-3">
              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex items-center justify-center gap-2 rounded-pill bg-brand-gradient px-5 py-3 text-sm font-semibold text-white brand-glow transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isSubmitting ? "Oluşturuluyor…" : "Profili Kaydet"}
                <ArrowRight size={14} />
              </button>
              {saved && (
                <button
                  type="button"
                  onClick={() => setView("summary")}
                  className="inline-flex items-center gap-2 rounded-pill border border-border bg-panel-elev px-4 py-3 text-xs font-medium text-muted-foreground transition hover:text-foreground"
                >
                  Vazgeç
                </button>
              )}
            </div>
            {saved && (
              <p className="text-xs text-subtle-foreground">
                Profili güncellersen yeni bir profil kaydı oluşturulur; önceki analizlerin
                geçmişten erişilemeyebilir.
              </p>
            )}
          </div>
        </form>
      )}
    </motion.div>
  );
}

// ----- subcomponents -----

function SummaryView({
  profile,
  onEdit,
}: {
  profile: SavedProfile;
  onEdit: () => void;
}) {
  return (
    <div className="panel p-6">
      <div className="flex items-center gap-2 text-success">
        <CheckCircle2 size={16} />
        <p className="text-sm font-medium">Profilin kayıtlı</p>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-4">
        <SummaryCell label="Boy" value={`${profile.height} cm`} />
        <SummaryCell label="Kilo" value={`${profile.weight} kg`} />
        <SummaryCell label="Tercih Edilen Kesim" value={FIT_LABEL[profile.fit]} />
        <SummaryCell
          label="Vücut Fotoğrafı"
          value={profile.hasBodyImage ? "Yüklendi" : "Yüklenmedi"}
          icon={profile.hasBodyImage ? ImageIcon : ImageOff}
        />
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <Link
          href="/analyze"
          className="inline-flex items-center gap-2 rounded-pill bg-brand-gradient px-5 py-3 text-sm font-semibold text-white brand-glow transition hover:brightness-110"
        >
          Analiz Yap <ArrowRight size={14} />
        </Link>
        <button
          type="button"
          onClick={onEdit}
          className="inline-flex items-center gap-2 rounded-pill border border-border bg-panel-elev px-4 py-3 text-xs font-medium text-muted-foreground transition hover:text-foreground"
        >
          <Pencil size={12} /> Profili Güncelle
        </button>
      </div>
    </div>
  );
}

function SummaryCell({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon?: typeof ImageIcon;
}) {
  return (
    <div className="rounded-card border border-border bg-panel-elev p-4">
      <p className="text-[11px] font-medium uppercase tracking-wider text-subtle-foreground">
        {label}
      </p>
      <div className="mt-1 flex items-center gap-2">
        {Icon && <Icon size={14} className="text-brand" />}
        <p className="text-base font-semibold text-foreground">{value}</p>
      </div>
    </div>
  );
}

function Field({
  id,
  label,
  placeholder,
  value,
  onChange,
  error,
  min,
  max,
}: {
  id: string;
  label: string;
  placeholder?: string;
  value: string;
  onChange: (v: string) => void;
  error?: string;
  min?: number;
  max?: number;
}) {
  return (
    <div>
      <label htmlFor={id} className="text-sm font-medium text-foreground">
        {label}
      </label>
      <input
        id={id}
        type="number"
        inputMode="numeric"
        min={min}
        max={max}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1.5 h-10 w-full rounded-md border border-border bg-panel-elev px-3 text-sm text-foreground placeholder:text-subtle-foreground focus:outline-none focus:ring-2 ring-brand"
      />
      {error && <p className="mt-1 text-xs text-danger">{error}</p>}
    </div>
  );
}
