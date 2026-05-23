interface SublabelPart {
  text: string;
  variant?: "open" | "closed" | "default";
}

interface BarItem {
  label: string;
  value: number;
  color?: string;
  sublabel?: string;
  /** Rich sublabel parts with individual styling. Takes priority over `sublabel`. */
  sublabelParts?: SublabelPart[];
}

interface HorizontalBarChartProps {
  items: BarItem[];
  maxItems?: number;
  valueFormatter?: (n: number) => string;
  "aria-label": string;
}

const VARIANT_CLASSES: Record<string, string> = {
  open: "bg-emerald-500/15 text-emerald-700",
  closed: "bg-slate-100 text-slate-500 ring-1 ring-inset ring-slate-200",
  default: "text-muted-foreground",
};

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
    <div role="img" aria-label={ariaLabel} className="space-y-3">
      {visible.map((item) => {
        const pct = (item.value / max) * 100;
        return (
          <div key={item.label}>
            <div className="mb-1 flex items-baseline justify-between gap-2 text-sm">
              <span className="min-w-0 truncate font-medium text-warm-black">
                {item.label}
              </span>
              <span className="shrink-0 tabular-nums text-muted-foreground">
                {valueFormatter(item.value)}
              </span>
            </div>
            <div className="h-2.5 overflow-hidden rounded-full bg-warm-200">
              <div
                className="interactive-fast h-full rounded-full hover:opacity-90"
                style={{
                  width: `${pct}%`,
                  backgroundColor: item.color ?? "var(--coral-500)",
                  minWidth: item.value > 0 ? "4px" : 0,
                }}
              />
            </div>
            {/* Rich sublabel with color-coded badges */}
            {item.sublabelParts && item.sublabelParts.length > 0 ? (
              <div className="mt-1 flex flex-wrap items-center gap-1.5">
                {item.sublabelParts.map((part, i) => {
                  const variant = part.variant ?? "default";
                  if (variant === "default") {
                    return (
                      <span key={i} className="text-xs text-muted-foreground">
                        {part.text}
                      </span>
                    );
                  }
                  return (
                    <span
                      key={i}
                      className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[11px] font-medium ${VARIANT_CLASSES[variant]}`}
                    >
                      {part.text}
                    </span>
                  );
                })}
              </div>
            ) : item.sublabel ? (
              <p className="mt-0.5 text-xs text-muted-foreground">{item.sublabel}</p>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
