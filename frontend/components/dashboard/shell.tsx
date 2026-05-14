import { Sidebar } from "./sidebar";
import { TopBar } from "./topbar";

export function DashboardShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh">
      <Sidebar />
      <main className="flex-1 px-6 pb-16 lg:px-10">
        <TopBar />
        <div className="mx-auto w-full max-w-6xl">{children}</div>
      </main>
    </div>
  );
}
