import type { Metadata } from "next";
import "./globals.css";
import { DashboardShell } from "@/components/dashboard/shell";

export const metadata: Metadata = {
  title: "HIWALOY — Üzerinizde Nasıl Duracağını Görün",
  description:
    "HIWALOY, kıyafetlerin sizin vücudunuzda gerçekten nasıl duracağını anlamanıza yardımcı olan açıklanabilir AI tabanlı bir alışveriş asistanıdır.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr" suppressHydrationWarning>
      <body>
        <DashboardShell>{children}</DashboardShell>
      </body>
    </html>
  );
}
