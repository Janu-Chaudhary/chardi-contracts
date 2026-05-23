import { TrendsDashboard } from "@/components/dashboard/trends-dashboard";
import { getTrendDirect } from "@/lib/data/server";

export const dynamic = "force-dynamic";

export default async function TrendsPage() {
  const trend = await getTrendDirect(12);

  return <TrendsDashboard initialTrend={trend} initialMonths={12} />;
}
