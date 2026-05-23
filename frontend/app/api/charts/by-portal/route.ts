import { NextResponse } from "next/server";
import { query } from "@/lib/db";

export const runtime = "edge";
export const revalidate = 300;

const PORTAL_LABELS: Record<string, string> = {
  "nyscr.ny.gov": "New York (NYSCR)",
  "caleprocure.ca.gov": "California",
  "eva.virginia.gov": "Virginia (eVA)",
  "txsmartbuy.gov": "Texas",
  "vita.virginia.gov": "Virginia (VITA)",
  "SAM.gov": "Federal (SAM.gov)",
  "doas.ga.gov": "Georgia (TGM)",
  "bidbuy.illinois.gov": "Illinois (BidBuy)",
};

const PORTAL_COLORS: Record<string, string> = {
  "nyscr.ny.gov": "#3b82f6",
  "caleprocure.ca.gov": "#f59e0b",
  "eva.virginia.gov": "#10b981",
  "txsmartbuy.gov": "#ef4444",
  "vita.virginia.gov": "#8b5cf6",
  "SAM.gov": "#6366f1",
  "doas.ga.gov": "#16a34a",
  "bidbuy.illinois.gov": "#0ea5e9",
};

export async function GET() {
  try {
    const rows = await query(`
      SELECT
        source_portal,
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE status = 'OPEN') as open,
        COUNT(*) FILTER (WHERE status = 'CLOSED') as closed
      FROM opportunities
      GROUP BY source_portal
      ORDER BY total DESC
    `);

    const data = rows.map((r) => ({
      portal: r.source_portal,
      label: PORTAL_LABELS[r.source_portal as string] || r.source_portal,
      color: PORTAL_COLORS[r.source_portal as string] || "#94a3b8",
      total: parseInt(String(r.total)),
      open: parseInt(String(r.open)),
      closed: parseInt(String(r.closed)),
    }));

    return NextResponse.json({ data });
  } catch (err) {
    console.error("charts/by-portal error:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
