"use client";

import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { StatusBadge } from "@/components/contracts/status-badge";
import type { Contract } from "@/lib/types";
import { cn, formatCurrency, formatDate } from "@/lib/utils";
import { ArrowUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";

import type { SortKey, SortOrder } from "@/lib/types";

export type { SortKey, SortOrder };

interface ContractsTableProps {
  contracts: Contract[];
  sortKey?: SortKey;
  sortOrder?: SortOrder;
  onSort?: (key: SortKey) => void;
}

function SortHeader({
  label,
  column,
  sortKey,
  sortOrder,
  onSort,
  className,
}: {
  label: string;
  column: SortKey;
  sortKey?: SortKey;
  sortOrder?: SortOrder;
  onSort?: (key: SortKey) => void;
  className?: string;
}) {
  const active = sortKey === column;
  return (
    <Button
      variant="ghost"
      size="sm"
      className={cn(
        "-ml-3 h-8 gap-1 px-2 text-xs font-medium uppercase tracking-wide text-muted-foreground hover:text-warm-black",
        className
      )}
      onClick={() => onSort?.(column)}
      aria-label={`Sort by ${label}`}
    >
      {label}
      <ArrowUpDown
        className={`h-3 w-3 shrink-0 ${active ? "text-coral-600" : "opacity-40"}`}
        aria-hidden
      />
      {active && (
        <span className="sr-only">{sortOrder === "asc" ? "ascending" : "descending"}</span>
      )}
    </Button>
  );
}

export function ContractsTable({
  contracts,
  sortKey,
  sortOrder,
  onSort,
}: ContractsTableProps) {
  return (
    <Table containerClassName="overflow-x-hidden" className="table-fixed">
      <colgroup>
        <col className="w-[36%]" />
        <col className="w-[28%]" />
        <col className="w-[14%]" />
        <col className="w-[12%]" />
        <col className="w-[10%]" />
      </colgroup>
      <TableHeader>
        <TableRow>
          <TableHead>
            <SortHeader label="Contract" column="title" sortKey={sortKey} sortOrder={sortOrder} onSort={onSort} />
          </TableHead>
          <TableHead>
            <SortHeader label="Agency" column="agency" sortKey={sortKey} sortOrder={sortOrder} onSort={onSort} />
          </TableHead>
          <TableHead className="text-right">
            <SortHeader
              label="Amount"
              column="amount"
              sortKey={sortKey}
              sortOrder={sortOrder}
              onSort={onSort}
              className="ml-auto -mr-2"
            />
          </TableHead>
          <TableHead>
            <SortHeader label="Due" column="deadline" sortKey={sortKey} sortOrder={sortOrder} onSort={onSort} />
          </TableHead>
          <TableHead className="whitespace-nowrap">Status</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {contracts.map((contract) => (
          <TableRow key={contract.id} className="cursor-pointer">
            <TableCell className="max-w-0">
              <Link
                href={`/contracts/${contract.id}`}
                className="block min-w-0 truncate font-medium text-warm-black hover:text-coral-600"
                title={contract.title}
              >
                {contract.title}
              </Link>
              <p className="mt-0.5 truncate text-xs text-muted-foreground" title={contract.portal}>
                {contract.portal}
              </p>
            </TableCell>
            <TableCell className="max-w-0">
              <p className="truncate text-muted-foreground" title={contract.agency}>
                {contract.agency}
              </p>
              {(contract.portalRegion || contract.state) && (
                <p className="mt-0.5 truncate text-xs text-muted-foreground/80">
                  {[contract.portalRegion, contract.state].filter(Boolean).join(" · ")}
                </p>
              )}
            </TableCell>
            <TableCell className="whitespace-nowrap text-right tabular-nums font-medium">
              {formatCurrency(contract.amount)}
            </TableCell>
            <TableCell className="whitespace-nowrap tabular-nums text-muted-foreground">
              {formatDate(contract.deadline)}
            </TableCell>
            <TableCell className="whitespace-nowrap">
              <StatusBadge status={contract.status} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
