"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatChartMonth } from "@/lib/chart-utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { TrendVolumeChart } from "@/components/charts/trend-volume-chart";
import { DeadlineTrendChart } from "@/components/charts/deadline-trend-chart";
import { ErrorState } from "@/components/states/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { normalizeTrend } from "@/lib/normalize-charts";
import type { TrendResponse } from "@/lib/api-types";

const MONTH_OPTIONS = [6, 12, 24] as const;
type MonthRange = (typeof MONTH_OPTIONS)[number];

interface TrendsDashboardProps {
  initialTrend: TrendResponse;
  initialMonths?: MonthRange;
}

function trendSummary(trend: TrendResponse) {
  const posted = trend.posted;
  const totalPosted = posted.reduce((s, m) => s + m.total, 0);
  const peak = posted.reduce(
    (best, m) => (m.total > (best?.total ?? 0) ? m : best),
    posted[0] as (typeof posted)[0] | undefined
  );
  const upcomingTotal = trend.upcoming_deadlines.reduce((s, m) => s + m.count, 0);
  return { totalPosted, peak, upcomingTotal };
}

export function TrendsDashboard({
  initialTrend,
  initialMonths = 12,
}: TrendsDashboardProps) {
  const [months, setMonths] = useState<MonthRange>(initialMonths);
  const [trend, setTrend] = useState<TrendResponse>(initialTrend);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTrend = useCallback(async (range: MonthRange) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/charts/trend?months=${range}`, { cache: "no-store" });
      if (!res.ok) throw new Error(`Trend API error (${res.status})`);
      const json = (await res.json()) as TrendResponse;
      setTrend(normalizeTrend(json));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load trends");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (months === initialMonths) {
      setTrend(initialTrend);
      return;
    }
    loadTrend(months);
  }, [months, initialMonths, initialTrend, loadTrend]);

  const summary = trendSummary(trend);

  return (
    <div className="space-y-8">
      <header className="space-y-4">
        <Button variant="ghost" size="sm" className="-ml-2" asChild>
          <Link href="/">
            <ArrowLeft className="h-4 w-4" aria-hidden />
            Back to overview
          </Link>
        </Button>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">
              Trends
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground sm:text-base">
              Monthly posting volume and upcoming deadlines across all indexed portals.
            </p>
          </div>
          <div
            className="inline-flex rounded-lg border border-border bg-card p-1 shadow-sm"
            role="group"
            aria-label="Time range"
          >
            {MONTH_OPTIONS.map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setMonths(n)}
                disabled={loading}
                className={cn(
                  "interactive min-h-[40px] rounded-md px-4 py-2 text-sm font-medium",
                  months === n
                    ? "bg-warm-200 text-warm-black shadow-sm"
                    : "text-muted-foreground hover:bg-warm-100 hover:text-warm-900",
                  loading && "opacity-60"
                )}
              >
                {n} mo
              </button>
            ))}
          </div>
        </div>
      </header>

      {error && <ErrorState message={error} onRetry={() => loadTrend(months)} />}

      <section aria-label="Trend summary" className="grid gap-3 sm:grid-cols-3">
        <Card className="interactive-card">
          <CardContent className="p-5">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Posted in range
            </p>
            <p className="mt-2 font-stat-md">
              {loading ? "—" : summary.totalPosted.toLocaleString()}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">Last {months} months</p>
          </CardContent>
        </Card>
        <Card className="interactive-card">
          <CardContent className="p-5">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Peak month
            </p>
            <p className="mt-2 font-stat-md">
              {loading || !summary.peak
                ? "—"
                : summary.peak.total.toLocaleString()}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {summary.peak ? formatChartMonth(summary.peak.month) : "—"}
            </p>
          </CardContent>
        </Card>
        <Card className="interactive-card">
          <CardContent className="p-5">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Upcoming deadlines
            </p>
            <p className="mt-2 font-stat-md">
              {loading ? "—" : summary.upcomingTotal.toLocaleString()}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">Next {months} months</p>
          </CardContent>
        </Card>
      </section>

      {loading && !error && (
        <Card>
          <CardContent className="space-y-4 p-6">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-52 w-full" />
          </CardContent>
        </Card>
      )}

      {!loading && !error && (
        <div className="space-y-6">
          <Card className="interactive-card">
            <CardHeader>
              <CardTitle className="font-display text-lg">Posting volume over time</CardTitle>
              <p className="text-sm text-muted-foreground">
                New contracts indexed per month, split by open vs closed status
              </p>
            </CardHeader>
            <CardContent>
              {trend.posted.length > 0 ? (
                <>
                  <TrendVolumeChart
                    aria-label="Monthly posting trend by status"
                    columns={trend.posted}
                  />
                  <p className="mt-6 border-t border-border pt-4 text-xs text-muted-foreground">
                    {trend.posted.length} months in view
                    {summary.peak &&
                      ` · peak ${formatChartMonth(summary.peak.month)} (${summary.peak.total.toLocaleString()} contracts)`}
                  </p>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No posting dates in the selected range.
                </p>
              )}
            </CardContent>
          </Card>

          <Card className="interactive-card">
            <CardHeader>
              <CardTitle className="font-display text-lg">Upcoming deadlines</CardTitle>
              <p className="text-sm text-muted-foreground">
                Contracts due by month over the next year
              </p>
            </CardHeader>
            <CardContent>
              {trend.upcoming_deadlines.length > 0 ? (
                <>
                  <DeadlineTrendChart
                    aria-label="Upcoming deadlines by month"
                    columns={trend.upcoming_deadlines.map((m) => ({
                      month: m.month,
                      count: m.count,
                    }))}
                  />
                  <p className="mt-6 border-t border-border pt-4 text-xs text-muted-foreground">
                    {summary.upcomingTotal.toLocaleString()} open deadlines across{" "}
                    {trend.upcoming_deadlines.length} months
                  </p>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">No upcoming deadlines indexed.</p>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
