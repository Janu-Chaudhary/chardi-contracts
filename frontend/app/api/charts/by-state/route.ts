import { NextResponse } from "next/server";
import { query, VALID_US_STATES } from "@/lib/db";

export const runtime = "edge";
export const revalidate = 300;

export async function GET() {
  try {
    const rows = await query(`
      SELECT
        COALESCE(state_region, 'Unknown') as state,
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE status = 'OPEN') as open,
        COUNT(*) FILTER (WHERE status = 'CLOSED') as closed,
        COUNT(*) FILTER (WHERE status = 'AWARDED') as awarded
      FROM opportunities
      WHERE state_region = ANY($1::text[])
      GROUP BY state_region
      ORDER BY total DESC
    `, [Array.from(VALID_US_STATES)]);

    // Also add Federal as a category
    const federalRow = await query(`
      SELECT
        'Federal' as state,
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE status = 'OPEN') as open,
        COUNT(*) FILTER (WHERE status = 'CLOSED') as closed,
        COUNT(*) FILTER (WHERE status = 'AWARDED') as awarded
      FROM opportunities
      WHERE portal_region = 'Federal'
    `);

    const data = [
      ...rows.map((r) => ({
        state: r.state,
        total: parseInt(String(r.total)),
        open: parseInt(String(r.open)),
        closed: parseInt(String(r.closed)),
        awarded: parseInt(String(r.awarded)),
      })),
      {
        state: "Federal",
        total: parseInt(String(federalRow[0]?.total || "0")),
        open: parseInt(String(federalRow[0]?.open || "0")),
        closed: parseInt(String(federalRow[0]?.closed || "0")),
        awarded: parseInt(String(federalRow[0]?.awarded || "0")),
      },
    ];

    return NextResponse.json({ data });
  } catch (err) {
    console.error("charts/by-state error:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
