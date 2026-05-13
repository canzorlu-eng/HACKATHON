"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { User, Shirt, MessageSquare } from "lucide-react";

const features = [
  {
    icon: <User size={18} className="text-foreground/70" />,
    title: "Vücut Analizi",
    description:
      "Boy, kilo ve vücut fotoğrafınızdan fit eğiliminizi analiz ediyoruz.",
  },
  {
    icon: <Shirt size={18} className="text-foreground/70" />,
    title: "Kıyafet Analizi",
    description:
      "Kıyafetin kesimini, kumaşını ve marka kalıbını AI ile değerlendiriyoruz.",
  },
  {
    icon: <MessageSquare size={18} className="text-foreground/70" />,
    title: "Topluluk Yorumları",
    description:
      "Gerçek kullanıcı yorumlarından sizing sorunlarını tespit ediyoruz.",
  },
];

export default function HomePage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4 py-20">
      {/* Hero */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex flex-col items-center gap-6 text-center"
      >
        <span className="border border-border bg-muted text-muted-foreground text-xs px-3 py-1 rounded-full">
          AI destekli beden ve uyum analizi
        </span>

        <h1 className="text-3xl sm:text-5xl font-semibold text-center max-w-2xl tracking-tight leading-tight">
          Kıyafetin sizde gerçekten nasıl duracağını alışveriş öncesi anlayın.
        </h1>

        <p className="text-base text-muted-foreground text-center max-w-xl">
          Vücut ölçülerinizi, kıyafet görselini ve kullanıcı yorumlarını
          birleştirerek açıklanabilir beden önerileri ve satın alma riski
          analizi.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-3 mt-2">
          <Link
            href="/onboarding"
            className="bg-foreground text-background rounded-md px-5 py-2.5 text-sm font-medium hover:bg-foreground/90 transition"
          >
            Ücretsiz Başla
          </Link>
          <Link
            href="/analyze"
            className="border border-border rounded-md px-5 py-2.5 text-sm font-medium hover:bg-muted transition"
          >
            Analiz Yap
          </Link>
        </div>
      </motion.div>

      {/* Features */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-3xl w-full mt-16"
      >
        {features.map((f) => (
          <div
            key={f.title}
            className="rounded-xl border border-border p-5 text-left bg-background"
          >
            <div className="mb-3">{f.icon}</div>
            <p className="text-sm font-medium text-foreground mb-1">{f.title}</p>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {f.description}
            </p>
          </div>
        ))}
      </motion.div>
    </main>
  );
}
