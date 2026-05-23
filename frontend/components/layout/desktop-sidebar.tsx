"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_ITEMS } from "@/components/layout/nav-items";
import { isNavActive } from "@/lib/nav-utils";
import { navItemClass } from "@/lib/interaction";
import { cn } from "@/lib/utils";

export function DesktopSidebar() {
  const pathname = usePathname();

  return (
    <aside className="sticky top-14 hidden h-[calc(100dvh-3.5rem)] w-56 shrink-0 flex-col border-r border-border bg-card/50 md:flex lg:w-60">
      <nav
        className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto p-4"
        aria-label="Main navigation"
      >
        {NAV_ITEMS.map((item) => {
          const active = isNavActive(pathname, item.href);
          const Icon = item.icon;

          if (item.disabled) {
            return (
              <span
                key={item.href}
                className="flex cursor-not-allowed items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-muted-foreground/60"
                aria-disabled
              >
                <Icon className="h-4 w-4" aria-hidden />
                {item.label}
                <span className="ml-auto text-[10px] uppercase tracking-wide">Soon</span>
              </span>
            );
          }

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium",
                navItemClass,
                active
                  ? "bg-coral-500/15 text-warm-black"
                  : "text-muted-foreground hover:bg-warm-200 hover:text-warm-black"
              )}
              aria-current={active ? "page" : undefined}
            >
              <Icon
                className={cn("h-4 w-4", active && "text-coral-600")}
                aria-hidden
              />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto shrink-0 border-t border-border p-4">
        <p className="text-xs text-muted-foreground">
          Chardi Contracts Intelligence
        </p>
        <p className="mt-1 text-[10px] text-muted-foreground/80">
          Live · Neon DB
        </p>
      </div>
    </aside>
  );
}
