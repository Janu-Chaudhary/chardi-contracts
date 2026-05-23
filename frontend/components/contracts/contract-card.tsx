"use client";

import Link from "next/link";
import { ChevronRight, Building2, Calendar, DollarSign } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/contracts/status-badge";
import type { Contract } from "@/lib/types";
import { formatCurrency, formatDate, cn } from "@/lib/utils";

interface ContractCardProps {
  contract: Contract;
  className?: string;
}

export function ContractCard({ contract, className }: ContractCardProps) {
  return (
    <Link href={`/contracts/${contract.id}`} className="block group">
      <Card
        className={cn(
          "transition-colors group-active:bg-warm-200/50 group-hover:border-warm-300",
          className
        )}
      >
        <CardContent className="space-y-4 p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1 space-y-1">
              <h3 className="line-clamp-2 text-base font-semibold leading-snug text-warm-black">
                {contract.title}
              </h3>
              <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <Building2 className="h-3.5 w-3.5 shrink-0" aria-hidden />
                <span className="truncate">{contract.agency}</span>
              </p>
            </div>
            <StatusBadge status={contract.status} />
          </div>

          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            <div>
              <dt className="text-xs text-muted-foreground">Vendor</dt>
              <dd className="mt-0.5 truncate font-medium">
                {contract.vendor ?? "—"}
              </dd>
            </div>
            <div>
              <dt className="flex items-center gap-1 text-xs text-muted-foreground">
                <DollarSign className="h-3 w-3" aria-hidden />
                Amount
              </dt>
              <dd className="mt-0.5 tabular-nums font-medium">
                {formatCurrency(contract.amount)}
              </dd>
            </div>
            <div>
              <dt className="flex items-center gap-1 text-xs text-muted-foreground">
                <Calendar className="h-3 w-3" aria-hidden />
                Due date
              </dt>
              <dd className="mt-0.5 tabular-nums">{formatDate(contract.deadline)}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Portal</dt>
              <dd className="mt-0.5 truncate text-warm-900">{contract.portal}</dd>
            </div>
          </dl>

          <div className="flex items-center justify-between border-t border-border pt-3 text-sm font-medium text-coral-600">
            <span className="text-muted-foreground font-normal">
              {contract.portalRegion}
              {contract.state ? ` · ${contract.state}` : ""}
            </span>
            <span className="inline-flex items-center gap-0.5">
              View details
              <ChevronRight className="h-4 w-4" aria-hidden />
            </span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
