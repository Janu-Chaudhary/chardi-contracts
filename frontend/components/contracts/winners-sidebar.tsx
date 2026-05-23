"use client";

/**
 * WinnersSidebar
 *
 * Lazy-loaded client component that fetches and renders the
 * "Who has won similar before?" award history panel.
 *
 * Zero blocking: fetches after mount, shows skeleton while loading.
 * Data is cached at the API layer for 1 hour.
 */

import { useEffect, useState } from "react";
import { Trophy, TrendingUp, Building2, AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, formatCurrency } from "@/lib/utils";

interface AwardWinner {
  vendor_name: string;
  industry: string;
  state_region: string | null;
  source_portal: string;
  win_count: number;
  total_value: number | null;
  avg_value: number | null;
  last_win_date: string | null;
}

interface WinnersResponse {
  opportunity_id: string;
  opportunity_title: string;
  matched_on: {
    industry: string | null;
    state_region: string | null;
  };
  winners: AwardWinner[];
  total: number;
}

interface WinnersSidebarProps {
  opportunityId: string;
  industry?: string | null;
}

function WinnerSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex items-start gap-3 rounded-lg border border-border/50 p-3">
          <Skeleton className="mt-0.5 h-6 w-6 shrink-0 rounded-full" />
          <div className="min-w-0 flex-1 space-y-1.5">
            <Skeleton className="h-3.5 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}

function MedalIcon({ rank }: { rank: number }) {
  const colors: Record<number, string> = {
    1: "text-yellow-500",
    2: "text-slate-400",
    3: "text-amber-600",
  };
  return (
    <Trophy
      className={cn("h-4 w-4 shrink-0", colors[rank] ?? "text-muted-foreground")}
      aria-hidden
    />
  );
}

function formatPortalLabel(portal: string): string {
  const labels: Record<string, string> = {
    "data.oregon.gov": "Oregon",
    "datacatalog.cookcountyil.gov": "Cook County IL",
    "data.houstontx.gov": "Houston TX",
    "data.cityofnewyork.us": "New York City",
    "dms.myflorida.com": "Florida",
    "bidbuy.illinois.gov": "Illinois",
    "data.cityofchicago.org": "Chicago",
    "eva.virginia.gov": "Virginia",
  };
  return labels[portal] ?? portal;
}

export function WinnersSidebar({ opportunityId, industry }: WinnersSidebarProps) {
  const [data, setData] = useState<WinnersResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!opportunityId) return;

    let cancelled = false;

    async function load() {
      try {
        const res = await fetch(`/api/opportunities/${opportunityId}/winners`, {
          // Use browser cache — API sets s-maxage=3600
          cache: "force-cache",
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json: WinnersResponse = await res.json();
        if (!cancelled) setData(json);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [opportunityId]);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 font-display text-lg">
          <TrendingUp className="h-4 w-4 text-coral-500" aria-hidden />
          Who has won similar?
        </CardTitle>
        {data?.matched_on.industry && (
          <p className="text-xs text-muted-foreground">
            Matched on{" "}
            <span className="font-medium text-warm-900">{data.matched_on.industry}</span>
            {data.matched_on.state_region && (
              <> · <span className="font-medium text-warm-900">{data.matched_on.state_region}</span></>
            )}
          </p>
        )}
        {!data?.matched_on.industry && industry && (
          <p className="text-xs text-muted-foreground">
            Industry: <span className="font-medium text-warm-900">{industry}</span>
          </p>
        )}
      </CardHeader>

      <CardContent className="pt-0">
        {loading && <WinnerSkeleton />}

        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-dashed border-border bg-warm-50/50 p-4 text-sm text-muted-foreground">
            <AlertCircle className="h-4 w-4 shrink-0" aria-hidden />
            Award history unavailable
          </div>
        )}

        {!loading && !error && data && data.winners.length === 0 && (
          <div className="flex items-center gap-2 rounded-lg border border-dashed border-border bg-warm-50/50 p-4 text-sm text-muted-foreground">
            <Building2 className="h-4 w-4 shrink-0" aria-hidden />
            No award history found for this category yet.
          </div>
        )}

        {!loading && !error && data && data.winners.length > 0 && (
          <ol className="space-y-2" aria-label="Past award winners">
            {data.winners.map((winner, idx) => (
              <li
                key={`${winner.vendor_name}-${winner.source_portal}`}
                className="flex items-start gap-3 rounded-lg border border-border/50 bg-warm-50/30 p-3 transition-colors hover:bg-warm-50/70"
              >
                <MedalIcon rank={idx + 1} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-warm-900" title={winner.vendor_name}>
                    {winner.vendor_name}
                  </p>
                  <div className="mt-1 flex flex-wrap items-center gap-1.5">
                    <Badge variant="default" className="text-xs">
                      {winner.win_count} win{winner.win_count !== 1 ? "s" : ""}
                    </Badge>
                    {winner.avg_value && (
                      <span className="text-xs text-muted-foreground">
                        avg {formatCurrency(winner.avg_value)}
                      </span>
                    )}
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-1.5">
                    <span className="text-xs text-muted-foreground">
                      {formatPortalLabel(winner.source_portal)}
                    </span>
                    {winner.last_win_date && (
                      <span className="text-xs text-muted-foreground">
                        · last {winner.last_win_date.slice(0, 7)}
                      </span>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  );
}
