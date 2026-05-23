import { KpiSkeletonGrid } from "@/components/states/loading-skeletons";
import { ContractListSkeleton } from "@/components/states/loading-skeletons";
import { Skeleton } from "@/components/ui/skeleton";

export default function DashboardLoading() {
  return (
    <div className="space-y-10">
      <div className="space-y-2">
        <Skeleton className="h-10 w-56" />
        <Skeleton className="h-4 w-80" />
      </div>
      <KpiSkeletonGrid />
      <ContractListSkeleton count={3} />
    </div>
  );
}
