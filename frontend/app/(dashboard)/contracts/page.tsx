import { Suspense } from "react";
import { ContractsExplorer } from "@/components/contracts/contracts-explorer";
import { ContractListSkeleton } from "@/components/states/loading-skeletons";

export default function ContractsPage() {
  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">
          Contracts
        </h1>
        <p className="text-sm text-muted-foreground sm:text-base">
          Search and filter opportunities across SAM.gov and state portals.
        </p>
      </header>
      <Suspense fallback={<ContractListSkeleton count={5} />}>
        <ContractsExplorer />
      </Suspense>
    </div>
  );
}
