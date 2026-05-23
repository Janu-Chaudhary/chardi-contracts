"use client";

import { useState, useCallback, useRef } from "react";
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

interface TooltipState {
  col: TrendVolumeColumn;
  x: number;   // px from left of chart area
  side: "left" | "right";
}

const CHART_HEIGHT = 220;
const OPEN_COLOR = "var(--coral-500)";
const CLOSED_COLOR = "#b0aaa6";

export function TrendVolumeChart({
  columns,
  "aria-label": ariaLabel,
  className,
}: TrendVolumeChartProps) {
  const [showOpen, setShowOpen] = useState(true);
  const [showClosed, setShowClosed] = useState(true);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const chartRef = useRef<HTMLDivElement>(null);

  const toggleOpen = useCallback(() => setShowOpen((v) => !v), []);
  const toggleClosed = useCallback(() => setShowClosed((v) => !v), []);

  const handleBarEnter = useCallback(
    (col: TrendVolumeColumn, e: React.MouseEvent<HTMLDivElement>) => {
      const chartEl = chartRef.current;
      if (!chartEl) return;
      const chartRect = chartEl.getBoundingClientRect();
      const barRect = e.currentTarget.getBoundingClientRect();
      const barCenterX = barRect.left + barRect.width / 2 - chartRect.left;
      const side: "left" | "right" = barCenterX > chartRect.width / 2 ? "right" : "left";
      setTooltip({ col, x: barCenterX, side });
    },
    []
  );

  const handleBarLeave = useCallback(() => setTooltip(null), []);

  if (columns.length === 0) {
    return <p className="text-sm text-muted-foreground">No data for this period.</p>;
  }

  const safe = columns.map((c) => ({
    month: c.month,
    total: Number(c.total) || 0,
    open: Number(c.open) || 0,
    closed: Number(c.closed) || 0,
  }));

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

        {/* Chart area — position:relative so tooltip is anchored here */}
        <div className="relative min-w-0 flex-1" ref={chartRef}>
          {/* Grid lines */}
          <div className="pointer-events-none absolute inset-0" aria-hidden>
            {ticks.map((tick) => (
              <div
                key={tick}
                className="absolute left-0 right-0 border-t border-dashed border-warm-300/80"
                style={{ bottom: `${(tick / axisMax) * 100}%` }}
              />
            ))}
          </div>

          {/* Bars */}
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
              const isHovered = tooltip?.col.month === col.month;

              return (
                <div
                  key={col.month}
                  className="group flex min-w-0 flex-1 flex-col items-center justify-end"
                >
                  <div
                    className={cn(
                      "interactive-fast mb-1 flex w-full max-w-[3rem] cursor-default flex-col justify-end overflow-hidden rounded-t-md shadow-sm transition-opacity",
                      isHovered ? "opacity-100" : "hover:opacity-90"
                    )}
                    style={{ height: Math.max(openH + closedH, minSeg) }}
                    aria-label={`${formatChartMonth(col.month)}: ${col.total.toLocaleString()} total`}
                    onMouseEnter={(e) => handleBarEnter(col, e)}
                    onMouseLeave={handleBarLeave}
                    onFocus={(e) => handleBarEnter(col, e as unknown as React.MouseEvent<HTMLDivElement>)}
                    onBlur={handleBarLeave}
                    tabIndex={0}
                    role="img"
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

          {/* ── Tooltip ── */}
          {tooltip && (
            <div
              className={cn(
                "pointer-events-none absolute bottom-full z-20 mb-2 w-44 rounded-lg border border-border bg-card px-3 py-2.5 shadow-lg",
                tooltip.side === "right"
                  ? "-translate-x-full"
                  : "translate-x-0"
              )}
              style={{ left: tooltip.x }}
              role="tooltip"
            >
              {/* Month header */}
              <p className="mb-2 text-xs font-semibold text-warm-black">
                {formatChartMonth(tooltip.col.month)}
              </p>

              {/* Total */}
              <div className="mb-1.5 flex items-center justify-between gap-2">
                <span className="text-xs text-muted-foreground">Total</span>
                <span className="text-xs font-semibold tabular-nums text-warm-black">
                  {tooltip.col.total.toLocaleString()}
                </span>
              </div>

              <div className="my-1.5 border-t border-border" />

              {/* Open row */}
              <div className="flex items-center justify-between gap-2">
                <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
                  <span
                    className="h-2 w-2 rounded-sm"
                    style={{ backgroundColor: OPEN_COLOR }}
                    aria-hidden
                  />
                  Open
                </span>
                <span className="text-xs font-medium tabular-nums text-emerald-700">
                  {tooltip.col.open.toLocaleString()}
                </span>
              </div>

              {/* Closed row */}
              <div className="mt-1 flex items-center justify-between gap-2">
                <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
                  <span
                    className="h-2 w-2 rounded-sm"
                    style={{ backgroundColor: CLOSED_COLOR }}
                    aria-hidden
                  />
                  Closed
                </span>
                <span className="text-xs font-medium tabular-nums text-slate-500">
                  {tooltip.col.closed.toLocaleString()}
                </span>
              </div>

              {/* Open % bar */}
              {tooltip.col.total > 0 && (
                <div className="mt-2.5">
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-warm-200">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${Math.round((tooltip.col.open / tooltip.col.total) * 100)}%`,
                        backgroundColor: OPEN_COLOR,
                      }}
                    />
                  </div>
                  <p className="mt-1 text-right text-[10px] text-muted-foreground">
                    {Math.round((tooltip.col.open / tooltip.col.total) * 100)}% open
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* X-axis labels */}
      <div className="mt-2 flex justify-between gap-1 pl-[3.25rem] sm:pl-14">
        {safe.map((col) => (
          <span
            key={`${col.month}-label`}
            className={cn(
              "min-w-0 flex-1 truncate text-center text-[10px] transition-colors sm:text-xs",
              tooltip?.col.month === col.month
                ? "font-medium text-warm-black"
                : "text-muted-foreground"
            )}
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
