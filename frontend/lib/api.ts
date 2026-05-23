import type {
  FiltersResponse,
  OpportunitiesQuery,
  OpportunitiesResponse,
  OpportunityDetailResponse,
  PortalChartItem,
  StatsResponse,
  TrendResponse,
} from "@/lib/api-types";
import type { ContractFilters } from "@/lib/types";
import type { SortKey, SortOrder } from "@/lib/types";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Base URL for server-side fetches (client uses relative paths). */
export function getApiBaseUrl(): string {
  if (typeof window !== "undefined") return "";
  if (process.env.NEXT_PUBLIC_APP_URL) return process.env.NEXT_PUBLIC_APP_URL;
  if (process.env.VERCEL_URL) return `https://${process.env.VERCEL_URL}`;
  return "http://127.0.0.1:3000";
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${getApiBaseUrl()}${path}`;
  const isClient = typeof window !== "undefined";
  const res = await fetch(url, {
    cache: isClient ? "no-store" : undefined,
    ...init,
    headers: {
      Accept: "application/json",
      ...init?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(res.status, body || res.statusText);
  }

  return res.json() as Promise<T>;
}

function buildQuery(params: Record<string, string | number | undefined>): string {
  const sp = new URLSearchParams();
  for (const [key, val] of Object.entries(params)) {
    if (val !== undefined && val !== "") sp.set(key, String(val));
  }
  const qs = sp.toString();
  return qs ? `?${qs}` : "";
}

const SORT_MAP: Record<SortKey, OpportunitiesQuery["sort"]> = {
  deadline: "deadline",
  amount: "deadline", // API has no amount sort; keep deadline
  title: "title",
  agency: "buyer_name",
};

export function filtersToQuery(
  filters: ContractFilters,
  opts?: {
    page?: number;
    limit?: number;
    sortKey?: SortKey;
    sortOrder?: SortOrder;
  }
): OpportunitiesQuery {
  return {
    q: filters.q || undefined,
    state: filters.state || undefined,
    status: filters.status || undefined,
    portal: filters.portal || undefined,
    portal_region: filters.portalRegion || undefined,
    buyer_type: filters.buyerType || undefined,
    notice_type: filters.noticeType || undefined,
    industry: filters.industry || undefined,
    deadline_from: filters.deadlineFrom || undefined,
    deadline_to: filters.deadlineTo || undefined,
    posted_from: filters.postedFrom || undefined,
    posted_to: filters.postedTo || undefined,
    page: opts?.page ?? 1,
    limit: opts?.limit ?? 20,
    sort: opts?.sortKey ? SORT_MAP[opts.sortKey] : "deadline",
    order: opts?.sortOrder ?? "asc",
  };
}

export function opportunitiesQueryToSearchParams(
  query: OpportunitiesQuery
): string {
  return buildQuery({
    q: query.q,
    state: query.state,
    status: query.status,
    portal: query.portal,
    portal_region: query.portal_region,
    buyer_type: query.buyer_type,
    notice_type: query.notice_type,
    industry: query.industry,
    deadline_from: query.deadline_from,
    deadline_to: query.deadline_to,
    posted_from: query.posted_from,
    posted_to: query.posted_to,
    page: query.page,
    limit: query.limit,
    sort: query.sort,
    order: query.order,
  });
}

export function filtersToExportParams(filters: ContractFilters): string {
  return opportunitiesQueryToSearchParams(filtersToQuery(filters, { limit: 5000 }));
}

export async function fetchStats(
  init?: RequestInit
): Promise<StatsResponse> {
  return apiFetch<StatsResponse>("/api/stats", {
    next: { revalidate: 60 },
    ...init,
  });
}

export async function fetchFilters(
  init?: RequestInit
): Promise<FiltersResponse> {
  return apiFetch<FiltersResponse>("/api/filters", {
    next: { revalidate: 300 },
    ...init,
  });
}

export async function fetchOpportunities(
  query: OpportunitiesQuery,
  init?: RequestInit
): Promise<OpportunitiesResponse> {
  return apiFetch<OpportunitiesResponse>(
    `/api/opportunities${opportunitiesQueryToSearchParams(query)}`,
    { next: { revalidate: 30 }, ...init }
  );
}

export async function fetchOpportunityById(
  id: string,
  init?: RequestInit
): Promise<OpportunityDetailResponse> {
  return apiFetch<OpportunityDetailResponse>(`/api/opportunities/${id}`, {
    next: { revalidate: 60 },
    ...init,
  });
}

export async function fetchTrend(
  months = 12,
  init?: RequestInit
): Promise<TrendResponse> {
  return apiFetch<TrendResponse>(`/api/charts/trend?months=${months}`, {
    next: { revalidate: 300 },
    ...init,
  });
}

export async function fetchChartByPortal(
  init?: RequestInit
): Promise<{ data: PortalChartItem[] }> {
  return apiFetch<{ data: PortalChartItem[] }>("/api/charts/by-portal", {
    next: { revalidate: 300 },
    ...init,
  });
}
