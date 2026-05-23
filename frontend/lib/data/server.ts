/**
 * Server-only Neon access for RSC pages.
 * Client components call /api/* (same data, full HTTP E2E on the browser path).
 */

import { query, VALID_US_STATES } from "@/lib/db";
import type {
  OpportunityRow,
  PortalChartItem,
  StateChartItem,
  StatsResponse,
  TrendResponse,
} from "@/lib/api-types";

const PORTAL_LABELS: Record<string, string> = {
  "nyscr.ny.gov": "New York",
  "caleprocure.ca.gov": "California",
  "eva.virginia.gov": "Virginia (eVA)",
  "txsmartbuy.gov": "Texas",
  "vita.virginia.gov": "Virginia (VITA)",
  "SAM.gov": "SAM.gov",
  "doas.ga.gov": "Georgia",
  "bidbuy.illinois.gov": "Illinois",
  "dms.myflorida.com": "Florida",
};

const PORTAL_COLORS: Record<string, string> = {
  "nyscr.ny.gov": "#6366f1",
  "caleprocure.ca.gov": "#f59e0b",
  "eva.virginia.gov": "#10b981",
  "txsmartbuy.gov": "#ea580c",
  "vita.virginia.gov": "#8b5cf6",
  "SAM.gov": "#1f1a17",
  "doas.ga.gov": "#16a34a",
  "bidbuy.illinois.gov": "#0ea5e9",
  "dms.myflorida.com": "#f97316",
};

const OPPORTUNITY_LIST_SELECT = `
  id, source_portal, source_record_id, solicitation_number,
  portal_region, title, description, notice_type,
  TO_CHAR(posted_date AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as posted_date,
  TO_CHAR(deadline AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as deadline,
  state_region, industry, naics_code,
  value_numeric, value_min, value_max, currency,
  status, buyer_name, buyer_type, source_url
`;

export async function getStatsDirect(): Promise<StatsResponse> {
  const [totals, lastRun, stateCount] = await Promise.all([
    query(`
      SELECT
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE status = 'OPEN') as open,
        COUNT(*) FILTER (WHERE status = 'CLOSED') as closed,
        COUNT(*) FILTER (WHERE status = 'AWARDED') as awarded,
        COUNT(*) FILTER (WHERE portal_region = 'Federal') as federal,
        COUNT(*) FILTER (WHERE portal_region = 'State') as state_count,
        COUNT(DISTINCT source_portal) as portals
      FROM opportunities
    `),
    query(`SELECT MAX(last_seen_at) as last_updated FROM opportunities`),
    query(
      `SELECT COUNT(DISTINCT state_region) as states
       FROM opportunities WHERE state_region = ANY($1::text[])`,
      [Array.from(VALID_US_STATES)]
    ),
  ]);

  const t = totals[0] as Record<string, string>;
  return {
    total: parseInt(String(t.total)),
    open: parseInt(String(t.open)),
    closed: parseInt(String(t.closed)),
    awarded: parseInt(String(t.awarded)),
    federal: parseInt(String(t.federal)),
    state_count: parseInt(String(t.state_count)),
    portals: parseInt(String(t.portals)),
    states: parseInt(String(stateCount[0]?.states || "0")),
    last_updated: (lastRun[0]?.last_updated as string) || null,
  };
}

export async function getRecentOpportunitiesDirect(
  limit = 3
): Promise<OpportunityRow[]> {
  const rows = await query(
    `SELECT ${OPPORTUNITY_LIST_SELECT}
     FROM opportunities
     ORDER BY posted_date DESC NULLS LAST
     LIMIT $1`,
    [limit]
  );
  return rows as unknown as OpportunityRow[];
}

export async function getTrendDirect(months = 6): Promise<TrendResponse> {
  const [posted, deadlines] = await Promise.all([
    query(`
      SELECT
        TO_CHAR(DATE_TRUNC('month', posted_date), 'YYYY-MM') as month,
        COUNT(*)::int as total,
        COUNT(*) FILTER (WHERE status = 'OPEN')::int as open,
        COUNT(*) FILTER (WHERE status = 'CLOSED')::int as closed
      FROM opportunities
      WHERE posted_date IS NOT NULL
        AND posted_date >= NOW() - INTERVAL '${months} months'
      GROUP BY DATE_TRUNC('month', posted_date)
      ORDER BY DATE_TRUNC('month', posted_date) ASC
    `),
    query(`
      SELECT
        TO_CHAR(DATE_TRUNC('month', deadline), 'YYYY-MM') as month,
        COUNT(*)::int as count
      FROM opportunities
      WHERE deadline IS NOT NULL
        AND deadline >= NOW()
        AND deadline <= NOW() + INTERVAL '12 months'
        AND deadline <= '2030-01-01'::timestamptz
      GROUP BY DATE_TRUNC('month', deadline)
      ORDER BY DATE_TRUNC('month', deadline) ASC
    `),
  ]);

  return {
    posted: (posted as { month: string; total: number; open: number; closed: number }[]).map(
      (r) => ({
        month: r.month,
        total: Number(r.total),
        open: Number(r.open),
        closed: Number(r.closed),
      })
    ),
    upcoming_deadlines: (deadlines as { month: string; count: number }[]).map((r) => ({
      month: r.month,
      count: Number(r.count),
    })),
  };
}

export async function getChartByPortalDirect(): Promise<PortalChartItem[]> {
  const rows = await query(`
    SELECT
      source_portal,
      COUNT(*)::int as total,
      COUNT(*) FILTER (WHERE status = 'OPEN')::int as open,
      COUNT(*) FILTER (WHERE status = 'CLOSED')::int as closed
    FROM opportunities
    GROUP BY source_portal
    ORDER BY total DESC
  `);

  return (rows as { source_portal: string; total: number; open: number; closed: number }[]).map(
    (r) => ({
      portal: r.source_portal,
      label: PORTAL_LABELS[r.source_portal] || r.source_portal,
      color: PORTAL_COLORS[r.source_portal] || "#94a3b8",
      total: Number(r.total),
      open: Number(r.open),
      closed: Number(r.closed),
    })
  );
}

export async function getChartByStateDirect(): Promise<StateChartItem[]> {
  const rows = await query(
    `
    SELECT
      COALESCE(state_region, 'Unknown') as state,
      COUNT(*)::int as total,
      COUNT(*) FILTER (WHERE status = 'OPEN')::int as open,
      COUNT(*) FILTER (WHERE status = 'CLOSED')::int as closed,
      COUNT(*) FILTER (WHERE status = 'AWARDED')::int as awarded
    FROM opportunities
    WHERE state_region = ANY($1::text[])
    GROUP BY state_region
    ORDER BY total DESC
    `,
    [Array.from(VALID_US_STATES)]
  );

  const federalRow = await query(`
    SELECT
      COUNT(*)::int as total,
      COUNT(*) FILTER (WHERE status = 'OPEN')::int as open,
      COUNT(*) FILTER (WHERE status = 'CLOSED')::int as closed,
      COUNT(*) FILTER (WHERE status = 'AWARDED')::int as awarded
    FROM opportunities
    WHERE portal_region = 'Federal'
  `);

  const f = federalRow[0] as { total: number; open: number; closed: number; awarded: number };

  const stateItems: StateChartItem[] = (
    rows as { state: string; total: number; open: number; closed: number; awarded: number }[]
  ).map((r) => ({
    state: r.state,
    total: Number(r.total),
    open: Number(r.open),
    closed: Number(r.closed),
    awarded: Number(r.awarded),
  }));

  stateItems.push({
    state: "Federal",
    total: Number(f?.total ?? 0),
    open: Number(f?.open ?? 0),
    closed: Number(f?.closed ?? 0),
    awarded: Number(f?.awarded ?? 0),
  });

  return stateItems.sort((a, b) => b.total - a.total);
}

export async function getOpportunityByIdDirect(
  id: string
): Promise<OpportunityRow | null> {
  const rows = await query(
    `SELECT
      ${OPPORTUNITY_LIST_SELECT},
      documents,
      TO_CHAR(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as created_at,
      TO_CHAR(updated_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as updated_at,
      TO_CHAR(last_seen_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as last_seen_at
     FROM opportunities WHERE id = $1`,
    [id]
  );
  return (rows[0] as unknown as OpportunityRow) ?? null;
}
