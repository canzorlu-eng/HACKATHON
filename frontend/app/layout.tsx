import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { tr } from "@/lib/i18n/tr";

export const metadata: Metadata = {
  title: "HIWALOY — Üzerinizde Nasıl Duracağını Görün",
  description:
    "HIWALOY, kıyafetlerin sizin vücudunuzda gerçekten nasıl duracağını anlamanıza yardımcı olan açıklanabilir AI tabanlı bir alışveriş asistanıdır.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr" suppressHydrationWarning>
      <body>
        <nav className="border-b bg-background">
          <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
            <Link href="/" className="font-semibold tracking-wide text-foreground">
              {tr.app.name}
            </Link>
            <div className="flex items-center gap-6">
              <Link
                href="/analyze"
                className="text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                {tr.nav.analyze}
              </Link>
              <Link
                href="/history"
                className="text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                {tr.nav.history}
              </Link>
            </div>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
