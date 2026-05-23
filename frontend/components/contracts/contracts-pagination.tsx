"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ContractsPaginationProps {
  page: number;
  totalPages: number;
  total: number;
  onPageChange: (page: number) => void;
}

export function ContractsPagination({
  page,
  totalPages,
  total,
  onPageChange,
}: ContractsPaginationProps) {
  if (totalPages <= 1) return null;

  return (
    <nav
      className="flex items-center justify-between gap-4 border-t border-border pt-4"
      aria-label="Pagination"
    >
      <p className="text-sm text-muted-foreground">
        Page {page} of {totalPages} · {total.toLocaleString()} total
      </p>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          aria-label="Previous page"
        >
          <ChevronLeft className="h-4 w-4" />
          Prev
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          aria-label="Next page"
        >
          Next
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </nav>
  );
}
