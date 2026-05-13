"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Circle, Loader2 } from "lucide-react";

interface AnalysisProgressProps {
  currentStep: number; // 0 = uploading, 1-6 = steps
}

const STEPS = [
  "Giriş doğrulanıyor…",
  "Beden ve kıyafet analiz ediliyor…",
  "Kullanıcı yorumları inceleniyor…",
  "Beden önerisi hazırlanıyor…",
  "Risk değerlendirmesi yapılıyor…",
  "Sonuçlar hazırlanıyor…",
];

const containerVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.15,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, x: -12 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.35 } },
};

export function AnalysisProgress({ currentStep }: AnalysisProgressProps) {
  return (
    <motion.ul
      className="flex flex-col gap-4"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {STEPS.map((label, index) => {
        const stepNumber = index + 1; // steps are 1-indexed
        const isDone = stepNumber < currentStep;
        const isActive = stepNumber === currentStep;
        const isPending = stepNumber > currentStep;

        return (
          <motion.li
            key={stepNumber}
            className="flex items-center gap-3"
            variants={itemVariants}
          >
            {/* Icon */}
            <span className="shrink-0">
              {isDone && (
                <CheckCircle2
                  className="h-5 w-5 text-green-500"
                  strokeWidth={2}
                />
              )}
              {isActive && (
                <Loader2
                  className="h-5 w-5 animate-spin text-foreground"
                  strokeWidth={2}
                />
              )}
              {isPending && (
                <Circle
                  className="h-5 w-5 text-muted-foreground/40"
                  strokeWidth={2}
                />
              )}
            </span>

            {/* Label */}
            <span
              className={
                isPending
                  ? "text-sm text-muted-foreground/40"
                  : "text-sm text-foreground"
              }
            >
              {label}
            </span>
          </motion.li>
        );
      })}
    </motion.ul>
  );
}
