import { NextResponse } from "next/server";
import { query, VALID_US_STATES } from "@/lib/db";

export const runtime = "edge";

// Cache for 60 seconds — stats don't need real-time accuracy
export const revalidate = 60;

export async function GET() {
  try {
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
      query(`
        SELECT MAX(last_seen_at) as last_updated FROM opportunities
      `),
      query(`
        SELECT COUNT(DISTINCT state_region) as states
        FROM opportunities
        WHERE state_region = ANY($1::text[])
      `, [Array.from(VALID_US_STATES)]),
    ]);

    const t = totals[0];

    return NextResponse.json({
      total: parseInt(String(t.total)),
      open: parseInt(String(t.open)),
      closed: parseInt(String(t.closed)),
      awarded: parseInt(String(t.awarded)),
      federal: parseInt(String(t.federal)),
      state_count: parseInt(String(t.state_count)),
      portals: parseInt(String(t.portals)),
      states: parseInt(String(stateCount[0]?.states || "0")),
      last_updated: lastRun[0]?.last_updated || null,
    });
  } catch (err) {
    console.error("stats API error:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
