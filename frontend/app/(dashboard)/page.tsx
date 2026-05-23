import { KpiCards } from "@/components/dashboard/kpi-cards";
import { RecentContracts } from "@/components/dashboard/recent-contracts";
import { DashboardCharts } from "@/components/dashboard/dashboard-charts";
import { WatchlistPlaceholder } from "@/components/dashboard/watchlist-placeholder";
import { DashboardError } from "@/components/dashboard/dashboard-error";
import { getRecentOpportunitiesDirect, getStatsDirect } from "@/lib/data/server";
import { mapOpportunities } from "@/lib/map-opportunity";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  try {
    const [stats, recentRows] = await Promise.all([
      getStatsDirect(),
      getRecentOpportunitiesDirect(3),
    ]);

    const recent = mapOpportunities(recentRows);

    return (
      <div className="space-y-10">
        <header className="space-y-2">
          <h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">
            Overview
          </h1>
          <p className="max-w-xl text-sm text-muted-foreground sm:text-base">
            Unified federal and state procurement intelligence across{" "}
            {stats.portals} active portals and {stats.total.toLocaleString()} contracts.
          </p>
        </header>

        <KpiCards stats={stats} />

        <DashboardCharts />

        <RecentContracts contracts={recent} />

        <WatchlistPlaceholder />
      </div>
    );
  } catch (e) {
    console.error("Dashboard load error:", e);
    return (
      <div className="space-y-6">
        <h1 className="font-display text-3xl font-semibold">Overview</h1>
        <DashboardError />
      </div>
    );
  }
}
