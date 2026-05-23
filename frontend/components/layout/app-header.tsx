import Link from "next/link";
import { MobileNav } from "@/components/layout/mobile-nav";

export function AppHeader() {
  return (
    <header className="sticky top-0 z-40 flex h-14 shrink-0 items-center gap-3 border-b border-border bg-background/95 px-4 backdrop-blur-sm sm:px-6">
      <MobileNav />
      <Link
        href="/"
        className="interactive flex min-w-0 items-center gap-2 rounded-md hover:opacity-80"
      >
        <span className="font-display text-xl font-semibold tracking-tight text-warm-black">
          Chardi
        </span>
        <span className="hidden truncate text-xs text-muted-foreground sm:inline">
          Contracts
        </span>
      </Link>
      <div className="ml-auto flex items-center gap-2">
        <span className="inline-flex items-center gap-1.5 rounded-md bg-warm-200 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-emerald-700">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-75" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
          </span>
          Live
        </span>
      </div>
    </header>
  );
}
