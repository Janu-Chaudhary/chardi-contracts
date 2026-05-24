import { NextRequest, NextResponse } from "next/server";
import { query } from "@/lib/db";

export const runtime = "edge";
export const revalidate = 300;

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const months = Math.min(24, Math.max(1, parseInt(searchParams.get("months") || "12")));

  try {
    // Trend by posted_date (monthly buckets)
    const rows = await query(`
      SELECT
        TO_CHAR(DATE_TRUNC('month', posted_date), 'YYYY-MM') as month,
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE status = 'OPEN') as open,
        COUNT(*) FILTER (WHERE status = 'CLOSED') as closed
      FROM opportunities
      WHERE posted_date IS NOT NULL
        AND posted_date >= NOW() - INTERVAL '${months} months'
        AND posted_date <= NOW()
      GROUP BY DATE_TRUNC('month', posted_date)
      ORDER BY DATE_TRUNC('month', posted_date) ASC
    `);

    // Also get deadline trend (upcoming deadlines by month — same range as posted)
    const deadlineRows = await query(`
      SELECT
        TO_CHAR(DATE_TRUNC('month', deadline), 'YYYY-MM') as month,
        COUNT(*) as count
      FROM opportunities
      WHERE deadline IS NOT NULL
        AND deadline >= NOW()
        AND deadline <= NOW() + INTERVAL '${months} months'
        AND deadline <= '2030-01-01'::timestamptz
      GROUP BY DATE_TRUNC('month', deadline)
      ORDER BY DATE_TRUNC('month', deadline) ASC
    `);

    return NextResponse.json({
      posted: rows.map((r) => ({
        month: r.month,
        total: parseInt(String(r.total)),
        open: parseInt(String(r.open)),
        closed: parseInt(String(r.closed)),
      })),
      upcoming_deadlines: deadlineRows.map((r) => ({
        month: r.month,
        count: parseInt(String(r.count)),
      })),
    });
  } catch (err) {
    console.error("charts/trend error:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
