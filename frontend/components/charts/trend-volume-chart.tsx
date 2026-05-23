"use client";

import { useState, useCallback } from "react";
import { buildAxisTicks, formatAxisValue, formatChartMonth } from "@/lib/chart-utils";
import { cn } from "@/lib/utils";

export interface TrendVolumeColumn {
  month: string;
  total: number;
  open: number;
  closed: number;
}

interface TrendVolumeChartProps {
  columns: TrendVolumeColumn[];
  "aria-label": string;
  className?: string;
}

const CHART_HEIGHT = 220;
const OPEN_COLOR = "var(--coral-500)";
const CLOSED_COLOR = "var(--warm-300)";

export function TrendVolumeChart({
  columns,
  "aria-label": ariaLabel,
  className,
}: TrendVolumeChartProps) {
  const [showOpen, setShowOpen] = useState(true);
  const [showClosed, setShowClosed] = useState(true);

  const toggleOpen = useCallback(() => setShowOpen((v) => !v), []);
  const toggleClosed = useCallback(() => setShowClosed((v) => !v), []);

  if (columns.length === 0) {
    return <p className="text-sm text-muted-foreground">No data for this period.</p>;
  }

  const safe = columns.map((c) => ({
    month: c.month,
    total: Number(c.total) || 0,
    open: Number(c.open) || 0,
    closed: Number(c.closed) || 0,
  }));

  // Compute visible values based on toggle state
  const visibleMax = Math.max(
    ...safe.map((c) => (showOpen ? c.open : 0) + (showClosed ? c.closed : 0)),
    1
  );
  const ticks = buildAxisTicks(visibleMax);
  const axisMax = ticks[ticks.length - 1] ?? visibleMax;

  return (
    <figure className={cn("w-full", className)} aria-label={ariaLabel}>
      {/* ── Interactive legend ── */}
      <div className="mb-3 flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
        <button
          type="button"
          onClick={toggleOpen}
          className={cn(
            "interactive-fast inline-flex items-center gap-1.5 rounded-md px-2 py-1 hover:bg-warm-200/60",
            !showOpen && "opacity-40 line-through"
          )}
          aria-pressed={showOpen}
          aria-label="Toggle open contracts"
        >
          <span
            className="h-2.5 w-2.5 rounded-sm"
            style={{ backgroundColor: OPEN_COLOR }}
            aria-hidden
          />
          Open
        </button>
        <button
          type="button"
          onClick={toggleClosed}
          className={cn(
            "interactive-fast inline-flex items-center gap-1.5 rounded-md px-2 py-1 hover:bg-warm-200/60",
            !showClosed && "opacity-40 line-through"
          )}
          aria-pressed={showClosed}
          aria-label="Toggle closed contracts"
        >
          <span
            className="h-2.5 w-2.5 rounded-sm"
            style={{ backgroundColor: CLOSED_COLOR }}
            aria-hidden
          />
          Closed
        </button>
      </div>

      <div className="flex gap-3">
        {/* Y-axis */}
        <div
          className="flex w-10 shrink-0 flex-col justify-between py-1 text-right text-[10px] tabular-nums text-muted-foreground sm:w-11 sm:text-xs"
          style={{ height: CHART_HEIGHT }}
          aria-hidden
        >
          {[...ticks].reverse().map((tick) => (
            <span key={tick}>{formatAxisValue(tick)}</span>
          ))}
        </div>

        {/* Chart area */}
        <div className="relative min-w-0 flex-1">
          <div className="pointer-events-none absolute inset-0" aria-hidden>
            {ticks.map((tick) => (
              <div
                key={tick}
                className="absolute left-0 right-0 border-t border-dashed border-warm-300/80"
                style={{ bottom: `${(tick / axisMax) * 100}%` }}
              />
            ))}
          </div>

          <div
            className="relative flex items-end justify-between gap-1 border-b border-border pl-1 sm:gap-2"
            style={{ height: CHART_HEIGHT }}
          >
            {safe.map((col) => {
              const visOpen = showOpen ? col.open : 0;
              const visClosed = showClosed ? col.closed : 0;
              const visTotal = visOpen + visClosed;
              const openH = Math.round((visOpen / axisMax) * (CHART_HEIGHT - 8));
              const closedH = Math.round((visClosed / axisMax) * (CHART_HEIGHT - 8));
              const minSeg = visTotal > 0 ? 3 : 0;

              return (
                <div
                  key={col.month}
                  className="group flex min-w-0 flex-1 flex-col items-center justify-end"
                >
                  <div
                    className="interactive-fast mb-1 flex w-full max-w-[3rem] cursor-default flex-col justify-end overflow-hidden rounded-t-md shadow-sm hover:opacity-90"
                    style={{ height: Math.max(openH + closedH, minSeg) }}
                    title={`${formatChartMonth(col.month)}: ${col.total.toLocaleString()} total (${col.open.toLocaleString()} open, ${col.closed.toLocaleString()} closed)`}
                  >
                    {showClosed && visClosed > 0 && (
                      <div
                        className="w-full transition-all"
                        style={{
                          height: Math.max(closedH, visClosed > 0 && visOpen === 0 ? minSeg : 0),
                          backgroundColor: CLOSED_COLOR,
                        }}
                      />
                    )}
                    {showOpen && visOpen > 0 && (
                      <div
                        className="w-full transition-all"
                        style={{
                          height: Math.max(openH, visOpen > 0 && visClosed === 0 ? minSeg : 0),
                          backgroundColor: OPEN_COLOR,
                        }}
                      />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* X-axis labels */}
      <div className="mt-2 flex justify-between gap-1 pl-[3.25rem] sm:pl-14">
        {safe.map((col) => (
          <span
            key={`${col.month}-label`}
            className="min-w-0 flex-1 truncate text-center text-[10px] text-muted-foreground sm:text-xs"
          >
            {formatChartMonth(col.month)}
          </span>
        ))}
      </div>

      <figcaption className="sr-only">
        {safe
          .map(
            (c) =>
              `${formatChartMonth(c.month)}: ${c.total} contracts, ${c.open} open, ${c.closed} closed`
          )
          .join("; ")}
      </figcaption>
    </figure>
  );
}
