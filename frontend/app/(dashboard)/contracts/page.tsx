import { ContractsExplorer } from "@/components/contracts/contracts-explorer";

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
      <ContractsExplorer />
    </div>
  );
}
