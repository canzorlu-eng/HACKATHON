"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Upload } from "lucide-react";

type FitPreference = "slim" | "regular" | "relaxed" | "oversize";

const FIT_OPTIONS: { value: FitPreference; label: string }[] = [
  { value: "slim", label: "Dar Kesim" },
  { value: "regular", label: "Normal Kesim" },
  { value: "relaxed", label: "Rahat Kesim" },
  { value: "oversize", label: "Oversize" },
];

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function OnboardingPage() {
  const router = useRouter();

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

  function validate(): boolean {
    let valid = true;

    const h = Number(heightCm);
    if (!heightCm || isNaN(h) || h < 50 || h > 300) {
      setHeightError("Boy 50–300 cm arasında olmalıdır.");
      valid = false;
    } else {
      setHeightError("");
    }

    const w = Number(weightKg);
    if (!weightKg || isNaN(w) || w < 20 || w > 500) {
      setWeightError("Kilo 20–500 kg arasında olmalıdır.");
      valid = false;
    } else {
      setWeightError("");
    }

    return valid;
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setApiError("");
    setSuccessMessage("");

    if (!validate()) return;

    setIsSubmitting(true);

    try {
      const fd = new FormData();
      fd.append("height_cm", String(heightCm));
      fd.append("weight_kg", String(weightKg));
      fd.append("fit_preference", fitPreference);
      if (bodyImage) fd.append("body_image", bodyImage);

      const res = await fetch(`${API_BASE}/api/v1/profile`, {
        method: "POST",
        body: fd,
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const data = await res.json();
      const userId: string = data.user_id ?? data.id ?? "";

      if (userId) {
        localStorage.setItem("hiwaloy_user_id", userId);
      }

      setSuccessMessage("Profiliniz oluşturuldu! Yönlendiriliyor…");

      setTimeout(() => {
        router.push("/analyze");
      }, 800);
    } catch {
      setApiError("Bir hata oluştu. Lütfen tekrar deneyin.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    setBodyImage(file);
  }

  return (
    <main className="min-h-screen bg-background flex items-start justify-center px-4 py-16">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="w-full max-w-[480px]"
      >
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-foreground">
            Profil Oluştur
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Doğru beden önerisi için ölçülerinizi girin.
          </p>
        </div>

        {/* Form card */}
        <div className="rounded-lg border border-border bg-background p-6 shadow-sm">
          <form onSubmit={handleSubmit} noValidate>
            <div className="flex flex-col gap-y-5">

              {/* Height */}
              <div>
                <label
                  htmlFor="height_cm"
                  className="text-sm font-medium text-foreground"
                >
                  Boy (cm)
                </label>
                <input
                  id="height_cm"
                  type="number"
                  inputMode="numeric"
                  min={50}
                  max={300}
                  placeholder="örn. 175"
                  value={heightCm}
                  onChange={(e) => setHeightCm(e.target.value)}
                  className="mt-1.5 w-full h-9 rounded-md border border-border bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-foreground/30 transition"
                />
                {heightError && (
                  <p className="text-sm text-red-600 mt-1">{heightError}</p>
                )}
              </div>

              {/* Weight */}
              <div>
                <label
                  htmlFor="weight_kg"
                  className="text-sm font-medium text-foreground"
                >
                  Kilo (kg)
                </label>
                <input
                  id="weight_kg"
                  type="number"
                  inputMode="numeric"
                  min={20}
                  max={500}
                  placeholder="örn. 70"
                  value={weightKg}
                  onChange={(e) => setWeightKg(e.target.value)}
                  className="mt-1.5 w-full h-9 rounded-md border border-border bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-foreground/30 transition"
                />
                {weightError && (
                  <p className="text-sm text-red-600 mt-1">{weightError}</p>
                )}
              </div>

              {/* Fit preference */}
              <div>
                <label
                  htmlFor="fit_preference"
                  className="text-sm font-medium text-foreground"
                >
                  Tercih Ettiğiniz Kesim
                </label>
                <select
                  id="fit_preference"
                  value={fitPreference}
                  onChange={(e) =>
                    setFitPreference(e.target.value as FitPreference)
                  }
                  className="mt-1.5 w-full h-9 rounded-md border border-border bg-background px-3 text-sm outline-none focus:ring-1 focus:ring-foreground/30 transition cursor-pointer"
                >
                  {FIT_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Body image upload */}
              <div>
                <p className="text-sm font-medium text-foreground mb-1.5">
                  Vücut Fotoğrafı (isteğe bağlı)
                </p>
                <div
                  role="button"
                  tabIndex={0}
                  onClick={() => fileInputRef.current?.click()}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ")
                      fileInputRef.current?.click();
                  }}
                  className="flex flex-col items-center justify-center gap-2 rounded-md border border-dashed border-border bg-muted px-4 py-6 cursor-pointer hover:bg-accent transition select-none"
                >
                  <Upload className="w-5 h-5 text-muted-foreground" />
                  {bodyImage ? (
                    <span className="text-sm text-foreground font-medium truncate max-w-full">
                      {bodyImage.name}
                    </span>
                  ) : (
                    <span className="text-sm text-muted-foreground">
                      Fotoğraf seçmek için tıklayın
                    </span>
                  )}
                  <span className="text-xs text-muted-foreground text-center">
                    Fotoğraf eklemek öneri doğruluğunu artırır.
                  </span>
                </div>
                <input
                  ref={fileInputRef}
                  id="body_image"
                  type="file"
                  accept="image/*"
                  onChange={handleFileChange}
                  className="hidden"
                />
              </div>

              {/* API error */}
              {apiError && (
                <p className="text-sm text-red-600 -mt-1">{apiError}</p>
              )}

              {/* Success message */}
              {successMessage && (
                <p className="text-sm text-green-600 -mt-1">{successMessage}</p>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full h-10 rounded-md bg-foreground text-background text-sm font-medium hover:bg-foreground/90 transition disabled:opacity-50 mt-1"
              >
                {isSubmitting ? "Oluşturuluyor…" : "Profil Oluştur"}
              </button>
            </div>
          </form>
        </div>
      </motion.div>
    </main>
  );
}
