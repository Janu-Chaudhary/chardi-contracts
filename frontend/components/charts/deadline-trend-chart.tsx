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

const CHART_HEIGHT = 200;
const BAR_COLOR = "var(--coral-600)";

export function DeadlineTrendChart({
  columns,
  "aria-label": ariaLabel,
  className,
}: DeadlineTrendChartProps) {
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
              const h = Math.round((col.count / axisMax) * (CHART_HEIGHT - 12));
              return (
                <div
                  key={col.month}
                  className="group/bar relative flex min-w-0 flex-1 flex-col items-center justify-end"
                >
                  <div
                    className="interactive-fast w-full max-w-[3rem] cursor-default rounded-t-md shadow-sm hover:brightness-110 hover:scale-x-105 active:brightness-110 active:scale-x-105 origin-bottom"
                    style={{
                      height: Math.max(h, col.count > 0 ? 6 : 0),
                      backgroundColor: BAR_COLOR,
                    }}
                    title={`${formatChartMonth(col.month)}: ${col.count.toLocaleString()} deadlines`}
                  />
                  {col.count > 0 && (
                    <div className="pointer-events-none absolute -top-8 left-1/2 z-10 -translate-x-1/2 rounded bg-warm-black px-2 py-1 text-[10px] font-medium text-white opacity-0 shadow-md transition-opacity group-hover/bar:opacity-100 group-active/bar:opacity-100 whitespace-nowrap">
                      {col.count.toLocaleString()}
                    </div>
                  )}
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
    </figure>
  );
}
