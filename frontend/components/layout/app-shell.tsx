import { AppHeader } from "@/components/layout/app-header";
import { DesktopSidebar } from "@/components/layout/desktop-sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-svh flex-col">
      <AppHeader />
      <div className="flex min-h-0 flex-1">
        <DesktopSidebar />
        <main className="min-h-0 flex-1 overflow-x-hidden">
          <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
