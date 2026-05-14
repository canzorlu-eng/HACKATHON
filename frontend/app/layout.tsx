import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { LayoutShell } from "@/components/dashboard/layout-shell";

export const metadata: Metadata = {
  title: "HIWALOY — Üzerinizde Nasıl Duracağını Görün",
  description:
    "HIWALOY, kıyafetlerin sizin vücudunuzda gerçekten nasıl duracağını anlamanıza yardımcı olan açıklanabilir AI tabanlı bir alışveriş asistanıdır.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr" suppressHydrationWarning>
      <body>
        <Providers>
          <LayoutShell>{children}</LayoutShell>
        </Providers>
      </body>
    </html>
  );
}
