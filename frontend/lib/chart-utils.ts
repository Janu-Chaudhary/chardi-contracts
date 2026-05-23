/** Format YYYY-MM as "Nov '25" */
export function formatChartMonth(ym: string): string {
  const [y, m] = ym.split("-");
  const months = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ];
  const mi = parseInt(m ?? "1", 10) - 1;
  return `${months[mi] ?? m} '${(y ?? "").slice(2)}`;
}

export function formatAxisValue(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(n >= 10_000 ? 0 : 1)}k`;
  return n.toLocaleString();
}

/** Nice round Y-axis ticks from 0 to max (4–5 steps). */
export function buildAxisTicks(max: number, steps = 4): number[] {
  if (max <= 0) return [0];
  const raw = max / steps;
  const magnitude = Math.pow(10, Math.floor(Math.log10(raw)));
  const normalized = raw / magnitude;
  const niceUnit =
    normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
  const step = niceUnit * magnitude;
  const top = Math.ceil(max / step) * step;
  const ticks: number[] = [];
  for (let v = 0; v <= top; v += step) {
    ticks.push(v);
  }
  return ticks;
}
