/**
 * Normalizers for chart API responses.
 * Coerce numeric strings → numbers and provide safe defaults.
 */

import type {
  PortalChartItem,
  PortalChartResponse,
  StateChartItem,
  StateChartResponse,
  TrendResponse,
} from "@/lib/api-types";

export function normalizePortalChart(res: PortalChartResponse): PortalChartItem[] {
  if (!res?.data || !Array.isArray(res.data)) return [];
  return res.data.map((r) => ({
    portal: String(r.portal ?? ""),
    label: String(r.label ?? r.portal ?? ""),
    color: String(r.color ?? "#94a3b8"),
    total: Number(r.total) || 0,
    open: Number(r.open) || 0,
    closed: Number(r.closed) || 0,
  }));
}

export function normalizeStateChart(res: StateChartResponse): StateChartItem[] {
  if (!res?.data || !Array.isArray(res.data)) return [];
  return res.data.map((r) => ({
    state: String(r.state ?? ""),
    total: Number(r.total) || 0,
    open: Number(r.open) || 0,
    closed: Number(r.closed) || 0,
    awarded: Number(r.awarded) || 0,
  }));
}

export function normalizeTrend(res: TrendResponse): TrendResponse {
  if (!res) return { posted: [], upcoming_deadlines: [] };
  return {
    posted: Array.isArray(res.posted)
      ? res.posted.map((r) => ({
          month: String(r.month ?? ""),
          total: Number(r.total) || 0,
          open: Number(r.open) || 0,
          closed: Number(r.closed) || 0,
        }))
      : [],
    upcoming_deadlines: Array.isArray(res.upcoming_deadlines)
      ? res.upcoming_deadlines.map((r) => ({
          month: String(r.month ?? ""),
          count: Number(r.count) || 0,
        }))
      : [],
  };
}
