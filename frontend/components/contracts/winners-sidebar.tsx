"use client";

/**
 * WinnersSidebar
 * "Who has won similar before?" — compact leaderboard style.
 * Lazy-loaded, zero blocking, 1hr cached.
 */

import { useEffect, useState } from "react";
import { TrendingUp, Building2, AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
  matched_on: { industry: string | null; state_region: string | null };
  winners: AwardWinner[];
  total: number;
}

interface WinnersSidebarProps {
  opportunityId: string;
  industry?: string | null;
}

const PORTAL_LABELS: Record<string, string> = {
  "data.oregon.gov": "Oregon",
  "datacatalog.cookcountyil.gov": "Cook County IL",
  "data.houstontx.gov": "Houston TX",
  "data.cityofnewyork.us": "New York City",
  "dms.myflorida.com": "Florida",
  "bidbuy.illinois.gov": "Illinois",
  "data.cityofchicago.org": "Chicago",
  "eva.virginia.gov": "Virginia",
};

const RANK_STYLES: Record<number, string> = {
  1: "bg-yellow-400/20 text-yellow-700 border-yellow-300/50",
  2: "bg-slate-100 text-slate-500 border-slate-200",
  3: "bg-amber-100/60 text-amber-700 border-amber-200/60",
};

function RankBadge({ rank }: { rank: number }) {
  return (
    <span
      className={cn(
        "flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[10px] font-bold tabular-nums",
        RANK_STYLES[rank] ?? "bg-warm-100 text-warm-500 border-warm-200"
      )}
      aria-label={`Rank ${rank}`}
    >
      {rank}
    </span>
  );
}

function WinnerSkeleton() {
  return (
    <div className="space-y-2.5">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="flex items-center gap-2.5 py-1">
          <Skeleton className="h-5 w-5 shrink-0 rounded-full" />
          <div className="min-w-0 flex-1 space-y-1">
            <Skeleton className="h-3 w-3/4" />
            <Skeleton className="h-2.5 w-1/2" />
          </div>
          <Skeleton className="h-3 w-8 shrink-0" />
        </div>
      ))}
    </div>
  );
}

export function WinnersSidebar({ opportunityId, industry }: WinnersSidebarProps) {
  const [data, setData] = useState<WinnersResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!opportunityId) return;
    let cancelled = false;

    fetch(`/api/opportunities/${opportunityId}/winners`, { cache: "force-cache" })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<WinnersResponse>;
      })
      .then((json) => { if (!cancelled) setData(json); })
      .catch((err) => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [opportunityId]);

  const matchLabel = data?.matched_on.industry
    ? [data.matched_on.industry, data.matched_on.state_region].filter(Boolean).join(" · ")
    : industry ?? null;

  return (
    <Card className="overflow-hidden">
      <CardHeader className="border-b border-border/60 pb-3">
        <CardTitle className="flex items-center gap-2 font-display text-base">
          <TrendingUp className="h-3.5 w-3.5 text-coral-500" aria-hidden />
          Who has won similar?
        </CardTitle>
        {matchLabel && (
          <p className="mt-0.5 text-[11px] text-muted-foreground">
            Matched on{" "}
            <span className="font-medium text-warm-800">{matchLabel}</span>
          </p>
        )}
      </CardHeader>

      <CardContent className="p-0">
        {loading && (
          <div className="px-4 py-3">
            <WinnerSkeleton />
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 px-4 py-4 text-xs text-muted-foreground">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" aria-hidden />
            Award history unavailable
          </div>
        )}

        {!loading && !error && data?.winners.length === 0 && (
          <div className="flex items-center gap-2 px-4 py-4 text-xs text-muted-foreground">
            <Building2 className="h-3.5 w-3.5 shrink-0" aria-hidden />
            No award history for this category yet.
          </div>
        )}

        {!loading && !error && data && data.winners.length > 0 && (
          <>
            {/* Scrollable leaderboard — max 6 rows visible */}
            <ol
              className="max-h-[340px] divide-y divide-border/40 overflow-y-auto"
              aria-label="Past award winners"
            >
              {data.winners.map((winner, idx) => (
                <li
                  key={`${winner.vendor_name}-${winner.source_portal}`}
                  className="flex items-center gap-2.5 px-4 py-2.5 transition-colors hover:bg-warm-50/60"
                >
                  <RankBadge rank={idx + 1} />

                  {/* Vendor name + portal */}
                  <div className="min-w-0 flex-1 overflow-hidden">
                    <p
                      className="truncate text-xs font-semibold text-warm-900 leading-snug"
                      title={winner.vendor_name}
                    >
                      {winner.vendor_name}
                    </p>
                    <p className="mt-0.5 text-[10px] text-muted-foreground leading-none truncate">
                      {PORTAL_LABELS[winner.source_portal] ?? winner.source_portal}
                      {winner.last_win_date && (
                        <> · {winner.last_win_date.slice(0, 7)}</>
                      )}
                    </p>
                  </div>

                  {/* Stats — right-aligned */}
                  <div className="shrink-0 text-right pl-2">
                    <p className="text-xs font-semibold tabular-nums text-warm-900 whitespace-nowrap">
                      {winner.win_count}
                      <span className="ml-0.5 text-[10px] font-normal text-muted-foreground">
                        win{winner.win_count !== 1 ? "s" : ""}
                      </span>
                    </p>
                    {winner.avg_value ? (
                      <p className="text-[10px] tabular-nums text-muted-foreground whitespace-nowrap">
                        avg {formatCurrency(winner.avg_value)}
                      </p>
                    ) : null}
                  </div>
                </li>
              ))}
            </ol>

            {/* Footer — total count */}
            {data.total > 0 && (
              <div className="border-t border-border/40 px-4 py-2">
                <p className="text-[10px] text-muted-foreground">
                  {data.total} vendor{data.total !== 1 ? "s" : ""} found in award history
                </p>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
