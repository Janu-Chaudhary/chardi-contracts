interface BarItem {
  label: string;
  value: number;
  color?: string;
}

interface HorizontalBarChartProps {
  items: BarItem[];
  maxItems?: number;
  valueFormatter?: (n: number) => string;
  "aria-label": string;
}

export function HorizontalBarChart({
  items,
  maxItems = 10,
  valueFormatter = (n) => n.toLocaleString(),
  "aria-label": ariaLabel,
}: HorizontalBarChartProps) {
  const visible = items.slice(0, maxItems).map((i) => ({
    ...i,
    value: Number(i.value) || 0,
  }));
  const max = Math.max(...visible.map((i) => i.value), 1);

  return (
    <div role="img" aria-label={ariaLabel} className="space-y-4">
      {visible.map((item) => {
        const pct = (item.value / max) * 100;
        return (
          <div key={item.label}>
            <div className="mb-1.5 flex items-baseline justify-between gap-2 text-sm">
              <span className="min-w-0 truncate font-medium text-warm-black">
                {item.label}
              </span>
              <span className="shrink-0 tabular-nums text-muted-foreground">
                {valueFormatter(item.value)}
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-warm-200">
              <div
                className="interactive-fast h-full rounded-full transition-opacity hover:opacity-80"
                style={{
                  width: `${pct}%`,
                  backgroundColor: item.color ?? "var(--coral-500)",
                  minWidth: item.value > 0 ? "4px" : 0,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
