"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
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

// ── URL ↔ filter helpers ──────────────────────────────────────────────────────

function filtersFromParams(sp: URLSearchParams): ContractFilters {
  return {
    q:            sp.get("q")            ?? DEFAULT_FILTERS.q,
    status:       (sp.get("status")      ?? DEFAULT_FILTERS.status) as ContractFilters["status"],
    portalRegion: (sp.get("region")      ?? DEFAULT_FILTERS.portalRegion) as ContractFilters["portalRegion"],
    portal:       sp.get("portal")       ?? DEFAULT_FILTERS.portal,
    state:        sp.get("state")        ?? DEFAULT_FILTERS.state,
    noticeType:   sp.get("noticeType")   ?? DEFAULT_FILTERS.noticeType,
    buyerType:    sp.get("buyerType")    ?? DEFAULT_FILTERS.buyerType,
    industry:     sp.get("industry")     ?? DEFAULT_FILTERS.industry,
    deadlineFrom: sp.get("deadlineFrom") ?? DEFAULT_FILTERS.deadlineFrom,
    deadlineTo:   sp.get("deadlineTo")   ?? DEFAULT_FILTERS.deadlineTo,
    postedFrom:   sp.get("postedFrom")   ?? DEFAULT_FILTERS.postedFrom,
    postedTo:     sp.get("postedTo")     ?? DEFAULT_FILTERS.postedTo,
  };
}

function filtersToParams(
  filters: ContractFilters,
  page: number,
  sortKey: SortKey,
  sortOrder: SortOrder
): URLSearchParams {
  const sp = new URLSearchParams();
  const def = DEFAULT_FILTERS;

  if (filters.q)            sp.set("q",            filters.q);
  if (filters.status        !== def.status)        sp.set("status",       filters.status);
  if (filters.portalRegion  !== def.portalRegion)  sp.set("region",       filters.portalRegion);
  if (filters.portal        !== def.portal)        sp.set("portal",       filters.portal);
  if (filters.state         !== def.state)         sp.set("state",        filters.state);
  if (filters.noticeType    !== def.noticeType)    sp.set("noticeType",   filters.noticeType);
  if (filters.buyerType     !== def.buyerType)     sp.set("buyerType",    filters.buyerType);
  if (filters.industry      !== def.industry)      sp.set("industry",     filters.industry);
  if (filters.deadlineFrom)  sp.set("deadlineFrom", filters.deadlineFrom);
  if (filters.deadlineTo)    sp.set("deadlineTo",   filters.deadlineTo);
  if (filters.postedFrom)    sp.set("postedFrom",   filters.postedFrom);
  if (filters.postedTo)      sp.set("postedTo",     filters.postedTo);
  if (page > 1)              sp.set("page",         String(page));
  if (sortKey !== "deadline") sp.set("sort",        sortKey);
  if (sortOrder !== "asc")   sp.set("order",        sortOrder);

  return sp;
}

// ─────────────────────────────────────────────────────────────────────────────

export function ContractsExplorer() {
  const router       = useRouter();
  const pathname     = usePathname();
  const searchParams = useSearchParams();

  // ── Initialise state from URL on first render ──
  const [filters,    setFiltersState]  = useState<ContractFilters>(() => filtersFromParams(searchParams));
  const [sortKey,    setSortKey]       = useState<SortKey>(() => (searchParams.get("sort") as SortKey) ?? "deadline");
  const [sortOrder,  setSortOrder]     = useState<SortOrder>(() => (searchParams.get("order") as SortOrder) ?? "asc");
  const [page,       setPageState]     = useState<number>(() => Number(searchParams.get("page") ?? 1));

  const debouncedQ = useDebounce(filters.q, 400);
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  const [results,      setResults]      = useState<Contract[]>([]);
  const [total,        setTotal]        = useState(0);
  const [totalPages,   setTotalPages]   = useState(0);
  const [facetOptions, setFacetOptions] = useState<FiltersResponse | null>(null);
  const [loading,      setLoading]      = useState(true);
  const [error,        setError]        = useState<string | null>(null);

  // ── Sync state → URL (replace, not push — no extra history entries) ──
  const syncUrl = useCallback(
    (f: ContractFilters, p: number, sk: SortKey, so: SortOrder) => {
      const sp = filtersToParams(f, p, sk, so);
      const qs = sp.toString();
      router.replace(`${pathname}${qs ? `?${qs}` : ""}`, { scroll: false });
    },
    [router, pathname]
  );

  // ── Wrapped setters that also update the URL ──
  const setFilters = useCallback(
    (f: ContractFilters) => {
      setFiltersState(f);
      setPageState(1);
      syncUrl(f, 1, sortKey, sortOrder);
    },
    [syncUrl, sortKey, sortOrder]
  );

  const setPage = useCallback(
    (p: number) => {
      setPageState(p);
      syncUrl(filters, p, sortKey, sortOrder);
    },
    [syncUrl, filters, sortKey, sortOrder]
  );

  // ── Load facet options once ──
  useEffect(() => {
    fetchFilters()
      .then(setFacetOptions)
      .catch(() => setFacetOptions(null));
  }, []);

  // ── Load contracts whenever effective query changes ──
  const loadContracts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const queryFilters = { ...filters, q: debouncedQ };
      const res = await fetchOpportunities(
        filtersToQuery(queryFilters, { page, limit: PAGE_SIZE, sortKey, sortOrder })
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

  // ── Sort handler ──
  const handleSort = useCallback(
    (key: SortKey) => {
      const newOrder: SortOrder = sortKey === key && sortOrder === "asc" ? "desc" : "asc";
      const newKey = key;
      setSortKey(newKey);
      setSortOrder(newOrder);
      setPageState(1);
      syncUrl(filters, 1, newKey, newOrder);
    },
    [sortKey, sortOrder, filters, syncUrl]
  );

  // ── Reset ──
  const resetFilters = useCallback(() => {
    setFiltersState(DEFAULT_FILTERS);
    setSortKey("deadline");
    setSortOrder("asc");
    setPageState(1);
    setMobileFiltersOpen(false);
    router.replace(pathname, { scroll: false });
  }, [router, pathname]);

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
  const exportCsvHref  = exportBaseHref.includes("?")
    ? exportBaseHref.replace("?", "?format=csv&")
    : `${exportBaseHref}?format=csv`;
  const exportJsonHref = exportBaseHref.includes("?")
    ? exportBaseHref.replace("?", "?format=json&")
    : `${exportBaseHref}?format=json`;

  const [downloadOpen,   setDownloadOpen]   = useState(false);
  const [downloadActive, setDownloadActive] = useState(false);
  const downloadRef = useRef<HTMLDivElement>(null);

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

            {/* Download dropdown */}
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

        {error && <ErrorState message={error} onRetry={loadContracts} />}
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
