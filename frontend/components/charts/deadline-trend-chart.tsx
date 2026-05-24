"use client";

import { useState, useCallback, useRef } from "react";
import { buildAxisTicks, formatAxisValue, formatChartMonth } from "@/lib/chart-utils";
import { cn } from "@/lib/utils";

interface DeadlineColumn {
  month: string;
  count: number;
}

interface DeadlineTrendChartProps {
  columns: DeadlineColumn[];
  "aria-label": string;
  className?: string;
}

interface TooltipState {
  col: DeadlineColumn;
  x: number;
  y: number;
  side: "left" | "right";
}

const CHART_HEIGHT = 200;
const BAR_COLOR = "var(--coral-500)";   // unified with chart 1
const BAR_HOVER = "var(--coral-600)";

export function DeadlineTrendChart({
  columns,
  "aria-label": ariaLabel,
  className,
}: DeadlineTrendChartProps) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const chartRef = useRef<HTMLDivElement>(null);

  const handleBarEnter = useCallback(
    (col: DeadlineColumn, e: React.MouseEvent<HTMLDivElement>) => {
      const chartEl = chartRef.current;
      if (!chartEl) return;
      const chartRect = chartEl.getBoundingClientRect();
      const barRect = e.currentTarget.getBoundingClientRect();
      const barCenterX = barRect.left + barRect.width / 2 - chartRect.left;
      const barTopY = chartRect.bottom - barRect.top;
      const side: "left" | "right" = barCenterX > chartRect.width / 2 ? "right" : "left";
      setTooltip({ col, x: barCenterX, y: barTopY, side });
    },
    []
  );

  const handleBarLeave = useCallback(() => setTooltip(null), []);

  if (columns.length === 0) {
    return <p className="text-sm text-muted-foreground">No upcoming deadlines in range.</p>;
  }

  const safe = columns.map((c) => ({
    month: c.month,
    count: Number(c.count) || 0,
  }));

  const max = Math.max(...safe.map((c) => c.count), 1);
  const ticks = buildAxisTicks(max);
  const axisMax = ticks[ticks.length - 1] ?? max;

  return (
    <figure className={cn("w-full", className)} aria-label={ariaLabel}>
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
              const h = Math.round((col.count / axisMax) * (CHART_HEIGHT - 12));
              const isHovered = tooltip?.col.month === col.month;

              return (
                <div
                  key={col.month}
                  className="flex min-w-0 flex-1 flex-col items-center justify-end"
                >
                  <div
                    className="interactive-fast mb-1 w-full max-w-[3rem] cursor-default rounded-t-md shadow-sm transition-all"
                    style={{
                      height: Math.max(h, col.count > 0 ? 6 : 0),
                      backgroundColor: isHovered ? BAR_HOVER : BAR_COLOR,
                      opacity: tooltip && !isHovered ? 0.6 : 1,
                    }}
                    aria-label={`${formatChartMonth(col.month)}: ${col.count.toLocaleString()} deadlines`}
                    onMouseEnter={(e) => handleBarEnter(col, e)}
                    onMouseLeave={handleBarLeave}
                    onFocus={(e) => handleBarEnter(col, e as unknown as React.MouseEvent<HTMLDivElement>)}
                    onBlur={handleBarLeave}
                    tabIndex={0}
                    role="img"
                  />
                </div>
              );
            })}
          </div>

          {/* Tooltip — anchored to bar top */}
          {tooltip && (
            <div
              className={cn(
                "pointer-events-none absolute z-20 mb-2 w-40 rounded-lg border border-border bg-card px-3 py-2.5 shadow-lg",
                tooltip.side === "right" ? "-translate-x-full" : "translate-x-0"
              )}
              style={{ left: tooltip.x, bottom: tooltip.y + 8 }}
              role="tooltip"
            >
              <p className="mb-2 text-xs font-semibold text-warm-black">
                {formatChartMonth(tooltip.col.month)}
              </p>
              <div className="flex items-center justify-between gap-2">
                <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
                  <span
                    className="h-2 w-2 rounded-sm"
                    style={{ backgroundColor: BAR_COLOR }}
                    aria-hidden
                  />
                  Deadlines
                </span>
                <span className="text-xs font-semibold tabular-nums text-warm-black">
                  {tooltip.col.count.toLocaleString()}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* X-axis labels — rotated vertically so full "Nov '25" fits at any width */}
      <div className="mt-1 flex justify-between gap-1 pl-[3.25rem] sm:pl-14">
        {safe.map((col) => (
          <span
            key={`${col.month}-label`}
            className={cn(
              "flex min-w-0 flex-1 items-end justify-center overflow-hidden transition-colors",
              tooltip?.col.month === col.month
                ? "font-medium text-warm-black"
                : "text-muted-foreground"
            )}
            style={{ height: "3rem" }}
          >
            <span
              className="text-[10px] leading-none sm:text-xs"
              style={{
                writingMode: "vertical-rl",
                transform: "rotate(180deg)",
                whiteSpace: "nowrap",
              }}
            >
              {formatChartMonth(col.month)}
            </span>
          </span>
        ))}
      </div>

      <figcaption className="sr-only">
        {safe.map((c) => `${formatChartMonth(c.month)}: ${c.count} deadlines`).join("; ")}
      </figcaption>
    </figure>
  );
}
