import type { ContractStatus } from "@/lib/types";

/** Raw row shape from /api/opportunities */
export interface OpportunityRow {
  id: string;
  source_portal: string;
  source_record_id?: string | null;
  solicitation_number?: string | null;
  portal_region: string;
  title: string;
  description?: string | null;
  notice_type?: string | null;
  posted_date?: string | null;
  deadline?: string | null;
  state_region?: string | null;
  industry?: string | null;
  naics_code?: string | null;
  value_numeric?: number | string | null;
  value_min?: number | string | null;
  value_max?: number | string | null;
  currency?: string | null;
  status: string;
  buyer_name?: string | null;
  buyer_type?: string | null;
  source_url?: string | null;
  documents?: unknown;
  created_at?: string | null;
  updated_at?: string | null;
  last_seen_at?: string | null;
}

export interface StatsResponse {
  total: number;
  open: number;
  closed: number;
  awarded: number;
  federal: number;
  state_count: number;
  portals: number;
  states: number;
  last_updated: string | null;
}

export interface FilterOption {
  value: string;
  label: string;
  count: number;
}

export interface FiltersResponse {
  states: FilterOption[];
  portals: FilterOption[];
  statuses: FilterOption[];
  buyer_types: FilterOption[];
  notice_types: FilterOption[];
  industries: FilterOption[];
}

export interface OpportunitiesResponse {
  data: OpportunityRow[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

export interface OpportunityDetailResponse {
  data: OpportunityRow;
}

export interface TrendMonth {
  month: string;
  total: number;
  open: number;
  closed: number;
}

export interface TrendResponse {
  posted: TrendMonth[];
  upcoming_deadlines: { month: string; count: number }[];
}

export interface PortalChartItem {
  portal: string;
  label: string;
  color: string;
  total: number;
  open: number;
  closed: number;
}

export interface StateChartItem {
  state: string;
  total: number;
  open: number;
  closed: number;
  awarded: number;
}

export interface PortalChartResponse {
  data: PortalChartItem[];
}

export interface StateChartResponse {
  data: StateChartItem[];
}

export type ApiSortField =
  | "deadline"
  | "posted_date"
  | "title"
  | "created_at"
  | "buyer_name"
  | "state_region";

export interface OpportunitiesQuery {
  q?: string;
  state?: string;
  status?: ContractStatus | "";
  portal?: string;
  portal_region?: "" | "Federal" | "State";
  buyer_type?: string;
  notice_type?: string;
  industry?: string;
  deadline_from?: string;
  deadline_to?: string;
  posted_from?: string;
  posted_to?: string;
  page?: number;
  limit?: number;
  sort?: ApiSortField;
  order?: "asc" | "desc";
}
