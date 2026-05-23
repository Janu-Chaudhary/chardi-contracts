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
  "dms.myflorida.com": "Florida (DMS)",
};

const PORTAL_COLORS: Record<string, string> = {
  "SAM.gov":               "#e07b54",  // coral — primary brand anchor
  "nyscr.ny.gov":          "#5b8db8",  // steel blue — calm, readable
  "data.cityofnewyork.us": "#5b8db8",  // same family as NYSCR
  "data.cityofchicago.org":"#7b9e87",  // sage green — neutral, earthy
  "caleprocure.ca.gov":    "#c4956a",  // warm amber — sun-baked
  "eva.virginia.gov":      "#8a7db8",  // soft indigo — distinguished
  "txsmartbuy.gov":        "#b85c5c",  // muted rose-red — warm but not loud
  "doas.ga.gov":           "#6aab9e",  // teal-sage — fresh
  "vita.virginia.gov":     "#9b7db8",  // lavender — pairs with indigo
  "bidbuy.illinois.gov":   "#6a8fb8",  // slate blue — distinct from steel
  "dms.myflorida.com":     "#c4a46a",  // golden sand
  "nyc_contract_awards":   "#7aab7a",  // muted green
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
      color: PORTAL_COLORS[r.source_portal as string] || "#8a9bb8",
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
