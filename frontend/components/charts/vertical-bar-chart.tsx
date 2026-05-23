import { buildAxisTicks, formatAxisValue, formatChartMonth } from "@/lib/chart-utils";

interface Column {
  label: string;
  value: number;
}

interface VerticalBarChartProps {
  columns: Column[];
  "aria-label": string;
}

const CHART_HEIGHT = 200;

/** Simple single-series bar chart (prefer TrendVolumeChart for posting trends). */
export function VerticalBarChart({ columns, "aria-label": ariaLabel }: VerticalBarChartProps) {
  if (columns.length === 0) {
    return <p className="text-sm text-muted-foreground">No data for this period.</p>;
  }

  const safeColumns = columns.map((c) => ({
    label: c.label,
    value: Number(c.value) || 0,
  }));
  const max = Math.max(...safeColumns.map((c) => c.value), 1);
  const ticks = buildAxisTicks(max);
  const axisMax = ticks[ticks.length - 1] ?? max;

  return (
    <figure className="w-full" aria-label={ariaLabel}>
      <div className="flex gap-3">
        <div
          className="flex w-10 shrink-0 flex-col justify-between py-1 text-right text-[10px] tabular-nums text-muted-foreground sm:text-xs"
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
            {safeColumns.map((col) => {
              const h = Math.round((col.value / axisMax) * (CHART_HEIGHT - 12));
              return (
                <div
                  key={col.label}
                  className="flex min-w-0 flex-1 flex-col items-center justify-end"
                >
                  <div
                    className="interactive-fast w-full max-w-[3rem] cursor-default rounded-t-md shadow-sm hover:opacity-90"
                    style={{
                      height: Math.max(h, col.value > 0 ? 6 : 0),
                      backgroundColor: "var(--coral-500)",
                    }}
                    title={`${formatChartMonth(col.label)}: ${col.value.toLocaleString()}`}
                  />
                </div>
              );
            })}
          </div>
        </div>
      </div>
      <div className="mt-2 flex justify-between gap-1 pl-[3.25rem] sm:pl-14">
        {safeColumns.map((col) => (
          <span
            key={`${col.label}-label`}
            className="min-w-0 flex-1 truncate text-center text-[10px] text-muted-foreground sm:text-xs"
          >
            {formatChartMonth(col.label)}
          </span>
        ))}
      </div>
    </figure>
  );
}
