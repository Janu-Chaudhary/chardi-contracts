"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Download, FileJson, FileText, Search, SlidersHorizontal } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import {
  Sheet,
  SheetContent,
  SheetFooter,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { ContractsFilters } from "@/components/contracts/contracts-filters";
import { ContractCard } from "@/components/contracts/contract-card";
import { ContractsTable } from "@/components/contracts/contracts-table";
import { ContractsPagination } from "@/components/contracts/contracts-pagination";
import { NoResultsState } from "@/components/states/no-results-state";
import { ErrorState } from "@/components/states/error-state";
import { ContractListSkeleton } from "@/components/states/loading-skeletons";
import { useDebounce } from "@/hooks/use-debounce";
import {
  fetchFilters,
  fetchOpportunities,
  filtersToExportParams,
  filtersToQuery,
} from "@/lib/api";
import { mapOpportunities } from "@/lib/map-opportunity";
import type { FiltersResponse } from "@/lib/api-types";
import {
  DEFAULT_FILTERS,
  type Contract,
  type ContractFilters,
  type SortKey,
  type SortOrder,
} from "@/lib/types";

const PAGE_SIZE = 20;

export function ContractsExplorer() {
  const [filters, setFilters] = useState<ContractFilters>(DEFAULT_FILTERS);
  const debouncedQ = useDebounce(filters.q, 400);
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>("deadline");
  const [sortOrder, setSortOrder] = useState<SortOrder>("asc");
  const [page, setPage] = useState(1);

  const [results, setResults] = useState<Contract[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [facetOptions, setFacetOptions] = useState<FiltersResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchFilters()
      .then(setFacetOptions)
      .catch(() => setFacetOptions(null));
  }, []);

  const loadContracts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const queryFilters = { ...filters, q: debouncedQ };
      const res = await fetchOpportunities(
        filtersToQuery(queryFilters, {
          page,
          limit: PAGE_SIZE,
          sortKey,
          sortOrder,
        })
      );
      setResults(mapOpportunities(res.data));
      setTotal(res.pagination.total);
      setTotalPages(res.pagination.total_pages);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load contracts");
      setResults([]);
      setTotal(0);
      setTotalPages(0);
    } finally {
      setLoading(false);
    }
  }, [filters, debouncedQ, page, sortKey, sortOrder]);

  useEffect(() => {
    loadContracts();
  }, [loadContracts]);

  // Derive a stable string key from all non-search filters so the
  // useEffect dependency array never changes size (rules-of-hooks safe).
  const filterKey = [
    filters.status,
    filters.portalRegion,
    filters.portal,
    filters.state,
    filters.noticeType,
    filters.buyerType,
    filters.industry,
    filters.deadlineFrom,
    filters.deadlineTo,
    filters.postedFrom,
    filters.postedTo,
    debouncedQ,
  ].join("|");

  // Reset to page 1 whenever any filter changes
  useEffect(() => {
    setPage(1);
  // filterKey is a stable primitive — safe single dep
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterKey]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortOrder((o) => (o === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortOrder("asc");
    }
    setPage(1);
  };

  const resetFilters = () => {
    setFilters(DEFAULT_FILTERS);
    setPage(1);
    setMobileFiltersOpen(false);
  };

  const activeFilterCount = [
    filters.status,
    filters.portalRegion,
    filters.portal,
    filters.state,
    filters.noticeType,
    filters.deadlineFrom,
    filters.deadlineTo,
    filters.postedFrom,
    filters.postedTo,
  ].filter(Boolean).length;

  const exportBaseHref = `/api/export${filtersToExportParams({ ...filters, q: debouncedQ })}`;
  const exportCsvHref = exportBaseHref.includes("?")
    ? exportBaseHref.replace("?", "?format=csv&")
    : `${exportBaseHref}?format=csv`;
  const exportJsonHref = exportBaseHref.includes("?")
    ? exportBaseHref.replace("?", "?format=json&")
    : `${exportBaseHref}?format=json`;

  const [downloadOpen, setDownloadOpen] = useState(false);
  const [downloadActive, setDownloadActive] = useState(false);
  const downloadRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    if (!downloadOpen) return;
    const handler = (e: MouseEvent) => {
      if (downloadRef.current && !downloadRef.current.contains(e.target as Node)) {
        setDownloadOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [downloadOpen]);

  return (
    <div className="flex flex-col gap-6 lg:flex-row lg:gap-8">
      <aside className="hidden w-64 shrink-0 lg:block">
        <Card className="sticky top-24">
          <CardHeader className="pb-2">
            <CardTitle className="font-sans text-base font-semibold">Filters</CardTitle>
          </CardHeader>
          <CardContent className="pt-2">
            <ContractsFilters
              filters={filters}
              onChange={setFilters}
              onReset={resetFilters}
              facetOptions={facetOptions}
            />
          </CardContent>
        </Card>
      </aside>

      <div className="min-w-0 flex-1 space-y-4">
        <div className="sticky top-14 z-30 -mx-4 border-b border-border bg-background/95 px-4 py-3 backdrop-blur-sm sm:-mx-6 sm:px-6 lg:static lg:mx-0 lg:border-0 lg:bg-transparent lg:p-0 lg:backdrop-blur-none">
          <div className="flex gap-2">
            <div className="relative min-w-0 flex-1">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden
              />
              <Input
                type="search"
                placeholder="Search contracts, agencies…"
                className="pl-9"
                value={filters.q}
                onChange={(e) => setFilters({ ...filters, q: e.target.value })}
                aria-label="Search contracts"
              />
            </div>

            {/* ── Download dropdown ── */}
            <div className="relative shrink-0" ref={downloadRef}>
              <Button
                variant="outline"
                size="icon"
                aria-label="Download contracts"
                aria-expanded={downloadOpen}
                aria-haspopup="menu"
                onClick={() => {
                  setDownloadOpen((v) => !v);
                  setDownloadActive(true);
                  setTimeout(() => setDownloadActive(false), 300);
                }}
                className={cn(
                  "transition-colors",
                  downloadOpen || downloadActive
                    ? "border-coral-500 text-coral-600 ring-1 ring-coral-400/50"
                    : "hover:border-coral-400 hover:text-coral-600"
                )}
              >
                <Download className="h-4 w-4" />
              </Button>

              {downloadOpen && (
                <div
                  role="menu"
                  className="absolute right-0 top-full z-50 mt-1.5 w-44 overflow-hidden rounded-lg border border-border bg-card shadow-lg"
                >
                  <p className="border-b border-border px-3 py-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                    Export as
                  </p>
                  <a
                    href={exportCsvHref}
                    download
                    role="menuitem"
                    onClick={() => setDownloadOpen(false)}
                    className="flex items-center gap-2.5 px-3 py-2.5 text-sm text-warm-black transition-colors hover:bg-coral-500/10 hover:text-coral-700"
                  >
                    <FileText className="h-4 w-4 shrink-0 text-coral-500" aria-hidden />
                    CSV
                    <span className="ml-auto text-xs text-muted-foreground">spreadsheet</span>
                  </a>
                  <a
                    href={exportJsonHref}
                    download
                    role="menuitem"
                    onClick={() => setDownloadOpen(false)}
                    className="flex items-center gap-2.5 px-3 py-2.5 text-sm text-warm-black transition-colors hover:bg-coral-500/10 hover:text-coral-700"
                  >
                    <FileJson className="h-4 w-4 shrink-0 text-coral-500" aria-hidden />
                    JSON
                    <span className="ml-auto text-xs text-muted-foreground">raw data</span>
                  </a>
                </div>
              )}
            </div>

            <Sheet open={mobileFiltersOpen} onOpenChange={setMobileFiltersOpen}>
              <SheetTrigger asChild>
                <Button
                  variant="outline"
                  size="icon"
                  className="relative shrink-0 lg:hidden"
                  aria-label="Open filters"
                >
                  <SlidersHorizontal className="h-4 w-4" />
                  {activeFilterCount > 0 && (
                    <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-coral-500 text-[10px] font-bold text-warm-black">
                      {activeFilterCount}
                    </span>
                  )}
                </Button>
              </SheetTrigger>
              <SheetContent side="bottom" className="flex max-h-[92vh] flex-col p-0">
                <SheetHeader className="border-b border-border px-6 py-4 text-left">
                  <SheetTitle>Filters</SheetTitle>
                </SheetHeader>
                <div className="flex-1 overflow-y-auto px-6 py-6">
                  <ContractsFilters
                    filters={filters}
                    onChange={setFilters}
                    onReset={resetFilters}
                    facetOptions={facetOptions}
                    compact
                  />
                </div>
                <SheetFooter className="flex-row gap-2 sm:justify-stretch">
                  <Button variant="outline" className="flex-1" onClick={resetFilters}>
                    Reset
                  </Button>
                  <Button className="flex-1" onClick={() => setMobileFiltersOpen(false)}>
                    Apply filters
                  </Button>
                </SheetFooter>
              </SheetContent>
            </Sheet>
          </div>

          <p className="mt-2 text-sm text-muted-foreground">
            {loading ? "Loading…" : `${total.toLocaleString()} contract${total !== 1 ? "s" : ""}`}
          </p>
        </div>

        {error && (
          <ErrorState message={error} onRetry={loadContracts} />
        )}

        {!error && loading && <ContractListSkeleton count={5} />}

        {!error && !loading && results.length === 0 && (
          <NoResultsState onClearFilters={resetFilters} />
        )}

        {!error && !loading && results.length > 0 && (
          <>
            <div className="space-y-3 lg:hidden">
              {results.map((contract) => (
                <ContractCard key={contract.id} contract={contract} />
              ))}
            </div>

            <Card className="hidden min-w-0 overflow-hidden lg:block">
              <ContractsTable
                contracts={results}
                sortKey={sortKey}
                sortOrder={sortOrder}
                onSort={handleSort}
              />
            </Card>

            <ContractsPagination
              page={page}
              totalPages={totalPages}
              total={total}
              onPageChange={setPage}
            />
          </>
        )}
      </div>
    </div>
  );
}
