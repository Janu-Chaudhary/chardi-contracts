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
  if (columns.length === 0) {
    return <p className="text-sm text-muted-foreground">No data for this period.</p>;
  }

  const safe = columns.map((c) => ({
    month: c.month,
    total: Number(c.total) || 0,
    open: Number(c.open) || 0,
    closed: Number(c.closed) || 0,
  }));

  const maxTotal = Math.max(...safe.map((c) => c.total), 1);
  const ticks = buildAxisTicks(maxTotal);
  const axisMax = ticks[ticks.length - 1] ?? maxTotal;

  return (
    <figure className={cn("w-full", className)} aria-label={ariaLabel}>
      <div className="mb-3 flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1.5">
          <span
            className="h-2.5 w-2.5 rounded-sm"
            style={{ backgroundColor: OPEN_COLOR }}
            aria-hidden
          />
          Open
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span
            className="h-2.5 w-2.5 rounded-sm"
            style={{ backgroundColor: CLOSED_COLOR }}
            aria-hidden
          />
          Closed
        </span>
      </div>

      <div className="flex gap-3">
        <div
          className="flex w-10 shrink-0 flex-col justify-between py-1 text-right text-[10px] tabular-nums text-muted-foreground sm:w-11 sm:text-xs"
          style={{ height: CHART_HEIGHT }}
          aria-hidden
        >
          {[...ticks].reverse().map((tick) => (
            <span key={tick}>{formatAxisValue(tick)}</span>
          ))}
        </div>

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
              const openH = Math.round((col.open / axisMax) * (CHART_HEIGHT - 8));
              const closedH = Math.round((col.closed / axisMax) * (CHART_HEIGHT - 8));
              const minSeg = col.total > 0 ? 3 : 0;

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
                    {col.closed > 0 && (
                      <div
                        className="w-full transition-all"
                        style={{
                          height: Math.max(closedH, col.closed > 0 && col.open === 0 ? minSeg : 0),
                          backgroundColor: CLOSED_COLOR,
                        }}
                      />
                    )}
                    {col.open > 0 && (
                      <div
                        className="w-full transition-all"
                        style={{
                          height: Math.max(openH, col.open > 0 && col.closed === 0 ? minSeg : 0),
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
