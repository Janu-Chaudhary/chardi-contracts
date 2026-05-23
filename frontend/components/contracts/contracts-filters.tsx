"use client";

import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Input } from "@/components/ui/input";
import type { FiltersResponse } from "@/lib/api-types";
import type { ContractFilters } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Matches SelectTrigger height and width in the filter sidebar. */
const FILTER_FIELD_CLASS =
  "h-10 w-full min-w-0 text-sm shadow-sm";

interface DateRangeFieldProps {
  id: string;
  label: string;
  value: string;
  min?: string;
  max?: string;
  onChange: (value: string) => void;
}

function DateRangeField({ id, label, value, min, max, onChange }: DateRangeFieldProps) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id} className="text-xs font-normal text-muted-foreground">
        {label}
      </Label>
      <Input
        type="date"
        id={id}
        aria-label={label}
        value={value}
        min={min}
        max={max}
        onChange={(e) => onChange(e.target.value)}
        className={cn(FILTER_FIELD_CLASS, "filter-date")}
      />
    </div>
  );
}

interface ContractsFiltersProps {
  filters: ContractFilters;
  onChange: (filters: ContractFilters) => void;
  onReset: () => void;
  facetOptions?: FiltersResponse | null;
  compact?: boolean;
}

export function ContractsFilters({
  filters,
  onChange,
  onReset,
  facetOptions,
  compact = false,
}: ContractsFiltersProps) {
  const set = (patch: Partial<ContractFilters>) => onChange({ ...filters, ...patch });

  return (
    <div className={compact ? "space-y-5" : "space-y-6"}>
      {/* Status */}
      <div className="space-y-2">
        <Label htmlFor="filter-status">Status</Label>
        <Select
          value={filters.status || "all"}
          onValueChange={(v) => set({ status: v === "all" ? "" : (v as ContractFilters["status"]) })}
        >
          <SelectTrigger id="filter-status">
            <SelectValue placeholder="Any status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Any status</SelectItem>
            {(facetOptions?.statuses ?? []).map((s) => (
              <SelectItem key={s.value} value={s.value}>
                {s.label} ({s.count})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Region */}
      <div className="space-y-2">
        <Label htmlFor="filter-region">Region</Label>
        <Select
          value={filters.portalRegion || "all"}
          onValueChange={(v) =>
            set({ portalRegion: v === "all" ? "" : (v as ContractFilters["portalRegion"]) })
          }
        >
          <SelectTrigger id="filter-region">
            <SelectValue placeholder="Federal or state" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All regions</SelectItem>
            <SelectItem value="Federal">Federal</SelectItem>
            <SelectItem value="State">State</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Portal */}
      <div className="space-y-2">
        <Label htmlFor="filter-portal">Portal</Label>
        <Select
          value={filters.portal || "all"}
          onValueChange={(v) => set({ portal: v === "all" ? "" : v })}
        >
          <SelectTrigger id="filter-portal">
            <SelectValue placeholder="Any portal" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Any portal</SelectItem>
            {(facetOptions?.portals ?? []).map((p) => (
              <SelectItem key={p.value} value={p.value}>
                {p.label} ({p.count})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* State */}
      <div className="space-y-2">
        <Label htmlFor="filter-state">State</Label>
        <Select
          value={filters.state || "all"}
          onValueChange={(v) => set({ state: v === "all" ? "" : v })}
        >
          <SelectTrigger id="filter-state">
            <SelectValue placeholder="Any state" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Any state</SelectItem>
            {(facetOptions?.states ?? []).map((s) => (
              <SelectItem key={s.value} value={s.value}>
                {s.label} ({s.count})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Notice type */}
      <div className="space-y-2">
        <Label htmlFor="filter-notice">Notice type</Label>
        <Select
          value={filters.noticeType || "all"}
          onValueChange={(v) => set({ noticeType: v === "all" ? "" : v })}
        >
          <SelectTrigger id="filter-notice">
            <SelectValue placeholder="Any type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Any type</SelectItem>
            {(facetOptions?.notice_types ?? []).map((n) => (
              <SelectItem key={n.value} value={n.value}>
                {n.label} ({n.count})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Deadline date range */}
      <div className="space-y-2">
        <Label>Deadline range</Label>
        <div className="space-y-3">
          <DateRangeField
            id="filter-deadline-from"
            label="From"
            value={filters.deadlineFrom}
            max={filters.deadlineTo || undefined}
            onChange={(deadlineFrom) => set({ deadlineFrom })}
          />
          <DateRangeField
            id="filter-deadline-to"
            label="To"
            value={filters.deadlineTo}
            min={filters.deadlineFrom || undefined}
            onChange={(deadlineTo) => set({ deadlineTo })}
          />
        </div>
        {(filters.deadlineFrom || filters.deadlineTo) && (
          <button
            type="button"
            onClick={() => set({ deadlineFrom: "", deadlineTo: "" })}
            className="text-[11px] text-muted-foreground underline-offset-2 hover:text-warm-black hover:underline"
          >
            Clear deadline range
          </button>
        )}
      </div>

      {/* Posted date range */}
      <div className="space-y-2">
        <Label>Posted range</Label>
        <div className="space-y-3">
          <DateRangeField
            id="filter-posted-from"
            label="From"
            value={filters.postedFrom}
            max={filters.postedTo || undefined}
            onChange={(postedFrom) => set({ postedFrom })}
          />
          <DateRangeField
            id="filter-posted-to"
            label="To"
            value={filters.postedTo}
            min={filters.postedFrom || undefined}
            onChange={(postedTo) => set({ postedTo })}
          />
        </div>
        {(filters.postedFrom || filters.postedTo) && (
          <button
            type="button"
            onClick={() => set({ postedFrom: "", postedTo: "" })}
            className="text-[11px] text-muted-foreground underline-offset-2 hover:text-warm-black hover:underline"
          >
            Clear posted range
          </button>
        )}
      </div>

      {!compact && (
        <>
          <Separator />
          <Button variant="outline" className="w-full" onClick={onReset}>
            Reset all filters
          </Button>
        </>
      )}
    </div>
  );
}
