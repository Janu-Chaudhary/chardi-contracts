"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ChevronRight, LineChart } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { HorizontalBarChart } from "@/components/charts/horizontal-bar-chart";
import { ErrorState } from "@/components/states/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import type {
  PortalChartItem,
  PortalChartResponse,
  StateChartItem,
  StateChartResponse,
} from "@/lib/api-types";
import { normalizePortalChart, normalizeStateChart } from "@/lib/normalize-charts";

type ChartTab = "portal" | "state";

const TABS: { id: ChartTab; label: string }[] = [
  { id: "portal", label: "By portal" },
  { id: "state", label: "By state" },
];

export function DashboardCharts() {
  const [active, setActive] = useState<ChartTab>("portal");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [byPortal, setByPortal] = useState<PortalChartItem[]>([]);
  const [byState, setByState] = useState<StateChartItem[]>([]);

  const loadCharts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [portalRes, stateRes] = await Promise.all([
        fetch("/api/charts/by-portal", { cache: "no-store" }),
        fetch("/api/charts/by-state", { cache: "no-store" }),
      ]);

      if (!portalRes.ok || !stateRes.ok) {
        throw new Error(
          `Chart API error: portal=${portalRes.status} state=${stateRes.status}`
        );
      }

      const [portalJson, stateJson] = await Promise.all([
        portalRes.json() as Promise<PortalChartResponse>,
        stateRes.json() as Promise<StateChartResponse>,
      ]);

      setByPortal(normalizePortalChart(portalJson));
      setByState(normalizeStateChart(stateJson));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load charts");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCharts();
  }, [loadCharts]);

  const topStates = byState.filter((s) => s.state !== "Federal").slice(0, 8);
  const federal = byState.find((s) => s.state === "Federal");

  return (
    <section aria-labelledby="charts-section-heading" className="space-y-4">
      <div>
        <h2
          id="charts-section-heading"
          className="font-display text-2xl font-semibold tracking-tight"
        >
          Analytics
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Contracts by portal and state — monthly trends on the Trends page
        </p>
      </div>

      <div
        className="grid grid-cols-2 gap-1 rounded-lg bg-warm-200 p-1"
        role="tablist"
        aria-label="Chart type"
      >
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={active === tab.id}
            onClick={() => setActive(tab.id)}
            disabled={loading}
            className={cn(
              "interactive min-h-[44px] rounded-md px-2 py-2.5 text-xs font-medium sm:text-sm",
              active === tab.id
                ? "bg-card text-warm-black shadow-sm"
                : "text-muted-foreground hover:bg-warm-200/50 hover:text-warm-900",
              loading && "opacity-60"
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && <ErrorState message={error} onRetry={loadCharts} />}

      {loading && !error && (
        <Card>
          <CardContent className="space-y-4 p-6">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-32 w-full" />
          </CardContent>
        </Card>
      )}

      {!loading && !error && (
        <div role="tabpanel" aria-live="polite">
          {active === "portal" && (
            <Card>
              <CardHeader>
                <CardTitle className="font-display text-lg">
                  Contracts by source portal
                </CardTitle>
              </CardHeader>
              <CardContent>
                {byPortal.length > 0 ? (
                  <HorizontalBarChart
                    aria-label="Contracts by portal"
                    items={byPortal.map((p) => ({
                      label: p.label,
                      value: p.total,
                      color: p.color,
                      sublabel: `${p.open.toLocaleString()} open · ${p.closed.toLocaleString()} closed`,
                    }))}
                  />
                ) : (
                  <p className="text-sm text-muted-foreground">No portal data.</p>
                )}
              </CardContent>
            </Card>
          )}

          {active === "state" && (
            <Card>
              <CardHeader>
                <CardTitle className="font-display text-lg">
                  Contracts by state / region
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {federal != null && (
                  <div className="interactive rounded-lg border border-border bg-warm-50/80 px-4 py-3 hover:border-warm-300 hover:bg-warm-50">
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Federal (SAM.gov)
                    </p>
                    <p className="mt-1 font-stat-md">{federal.total.toLocaleString()}</p>
                    <p className="text-xs text-muted-foreground">
                      {federal.open.toLocaleString()} open
                    </p>
                  </div>
                )}
                {topStates.length > 0 ? (
                  <HorizontalBarChart
                    aria-label="Contracts by US state"
                    items={topStates.map((s) => ({
                      label: s.state,
                      value: s.total,
                      color: "var(--coral-500)",
                      sublabel: `${s.open.toLocaleString()} open`,
                    }))}
                    maxItems={8}
                  />
                ) : (
                  <p className="text-sm text-muted-foreground">No state data available.</p>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      <Link
        href="/trends"
        className="group block rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      >
        <Card className="interactive-card border-border bg-warm-50/50">
          <CardContent className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-coral-500/15 transition-colors group-hover:bg-coral-500/25">
                <LineChart className="h-5 w-5 text-coral-600" aria-hidden />
              </div>
              <div>
                <h3 className="font-display text-base font-semibold">Posting trends</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  Monthly volume, open vs closed breakdown, and upcoming deadlines
                </p>
              </div>
            </div>
            <span className="inline-flex shrink-0 items-center gap-1 text-sm font-medium text-coral-600 transition-transform duration-200 ease-out group-hover:translate-x-0.5">
              View trends
              <ChevronRight className="h-4 w-4" aria-hidden />
            </span>
          </CardContent>
        </Card>
      </Link>
    </section>
  );
}
