import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ContractCard } from "@/components/contracts/contract-card";
import type { Contract } from "@/lib/types";

interface RecentContractsProps {
  contracts: Contract[];
}

export function RecentContracts({ contracts }: RecentContractsProps) {
  if (contracts.length === 0) {
    return (
      <section>
        <h2 className="font-display text-2xl font-semibold">Recent contracts</h2>
        <p className="mt-2 text-sm text-muted-foreground">No contracts in the database yet.</p>
      </section>
    );
  }

  return (
    <section aria-labelledby="recent-heading">
      <div className="mb-4 flex items-end justify-between gap-4">
        <div>
          <h2 id="recent-heading" className="font-display text-2xl font-semibold">
            Recent contracts
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Latest opportunities across federal and state portals
          </p>
        </div>
        <Link
          href="/contracts"
          className="hidden items-center gap-1 text-sm font-medium text-coral-600 hover:text-coral-600/80 sm:inline-flex"
        >
          View all
          <ArrowRight className="h-4 w-4" aria-hidden />
        </Link>
      </div>

      <div className="space-y-3 md:hidden">
        {contracts.map((c) => (
          <ContractCard key={c.id} contract={c} />
        ))}
      </div>

      <Card className="hidden md:block">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="font-sans text-base font-semibold">Latest activity</CardTitle>
          <Link href="/contracts" className="text-sm font-medium text-coral-600">
            View all →
          </Link>
        </CardHeader>
        <CardContent className="divide-y divide-border p-0">
          {contracts.map((c) => (
            <Link
              key={c.id}
              href={`/contracts/${c.id}`}
              className="flex items-center justify-between gap-4 px-6 py-4 transition-colors hover:bg-warm-50"
            >
              <div className="min-w-0">
                <p className="truncate font-medium text-warm-black">{c.title}</p>
                <p className="truncate text-sm text-muted-foreground">{c.agency}</p>
              </div>
              <span className="shrink-0 text-xs text-muted-foreground">{c.portal}</span>
            </Link>
          ))}
        </CardContent>
      </Card>

      <Link
        href="/contracts"
        className="mt-4 flex h-11 w-full items-center justify-center rounded-lg border border-border text-sm font-medium sm:hidden"
      >
        View all contracts
      </Link>
    </section>
  );
}
