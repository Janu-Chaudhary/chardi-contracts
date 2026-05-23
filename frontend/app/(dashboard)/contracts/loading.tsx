import { ContractListSkeleton } from "@/components/states/loading-skeletons";
import { Skeleton } from "@/components/ui/skeleton";

export default function ContractsLoading() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-9 w-48" />
        <Skeleton className="h-4 w-72" />
      </div>
      <Skeleton className="h-10 w-full" />
      <ContractListSkeleton count={5} />
    </div>
  );
}
