import { tr } from "@/lib/i18n/tr";

export default function HomePage() {
  return (
    <main className="min-h-dvh">
      <section className="container flex min-h-dvh flex-col items-center justify-center gap-8 py-16 text-center">
        <span className="rounded-full border border-border bg-muted px-3 py-1 text-xs font-medium text-muted-foreground">
          {tr.landing.badge}
        </span>
        <h1 className="max-w-2xl text-balance text-4xl font-semibold tracking-tight sm:text-5xl">
          {tr.landing.title}
        </h1>
        <p className="max-w-xl text-balance text-base text-muted-foreground sm:text-lg">
          {tr.landing.subtitle}
        </p>
        <p className="text-sm text-muted-foreground">{tr.landing.phaseNote}</p>
      </section>
    </main>
  );
}
