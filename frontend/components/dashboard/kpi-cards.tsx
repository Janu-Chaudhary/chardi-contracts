import { Card, CardContent } from "@/components/ui/card";
import type { StatsResponse } from "@/lib/api-types";
import { formatDate } from "@/lib/utils";

interface KpiCardsProps {
  stats: StatsResponse;
}

export function KpiCards({ stats }: KpiCardsProps) {
  const items = [
    { label: "Total contracts", value: stats.total.toLocaleString(), key: "total" },
    { label: "Open", value: stats.open.toLocaleString(), key: "open" },
    { label: "Federal", value: stats.federal.toLocaleString(), key: "federal" },
    { label: "State", value: stats.state_count.toLocaleString(), key: "state" },
  ];

  return (
    <section aria-labelledby="kpi-heading">
      <h2 id="kpi-heading" className="sr-only">
        Key metrics
      </h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
        {items.map((item) => (
          <Card key={item.key}>
            <CardContent className="p-5">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {item.label}
              </p>
              <p className="mt-2 font-stat-md">{item.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>
      <p className="mt-3 text-xs text-muted-foreground">
        Last updated {formatDate(stats.last_updated)} · {stats.portals} portals ·{" "}
        {stats.states} states
      </p>
    </section>
  );
}
