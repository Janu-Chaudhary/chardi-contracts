"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { NAV_ITEMS } from "@/components/layout/nav-items";
import { isNavActive } from "@/lib/nav-utils";
import { navItemClass } from "@/lib/interaction";
import { useSwipe } from "@/hooks/use-swipe";
import { cn } from "@/lib/utils";

export function MobileNav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const openSidebar = useCallback(() => setOpen(true), []);
  const closeSidebar = useCallback(() => setOpen(false), []);

  // Swipe left on the sheet content to close it
  const sheetSwipe = useSwipe({ onSwipeLeft: closeSidebar });

  // Swipe right on the main page to open the sidebar (edge swipe)
  const edgeSwipe = useSwipe({ onSwipeRight: openSidebar });

  return (
    <>
      {/* Invisible edge-swipe zone on the left side of the screen (mobile only) */}
      <div
        className="fixed left-0 top-0 z-30 h-full w-5 md:hidden"
        aria-hidden="true"
        {...edgeSwipe}
      />

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger asChild>
          <Button variant="ghost" size="icon" className="md:hidden" aria-label="Open menu">
            <Menu className="h-5 w-5" />
          </Button>
        </SheetTrigger>
        <SheetContent
          side="left"
          className="w-[min(100%,280px)] p-0"
          {...sheetSwipe}
        >
          <SheetHeader className="border-b border-border px-6 py-5 text-left">
            <SheetTitle className="font-display text-xl">Chardi</SheetTitle>
          </SheetHeader>
          <nav className="flex flex-col gap-1 p-4" aria-label="Mobile navigation">
            {NAV_ITEMS.map((item) => {
              const active = isNavActive(pathname, item.href);
              const Icon = item.icon;

              if (item.disabled) {
                return (
                  <span
                    key={item.href}
                    className="flex cursor-not-allowed items-center gap-3 rounded-lg px-3 py-3 text-base text-muted-foreground/60"
                  >
                    <Icon className="h-5 w-5" />
                    {item.label}
                  </span>
                );
              }

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={closeSidebar}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-3 text-base font-medium active:bg-warm-200",
                    navItemClass,
                    active
                      ? "bg-coral-500/15 text-warm-black"
                      : "text-warm-900 hover:bg-warm-200"
                  )}
                >
                  <Icon className={cn("h-5 w-5", active && "text-coral-600")} />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </SheetContent>
      </Sheet>
    </>
  );
}
