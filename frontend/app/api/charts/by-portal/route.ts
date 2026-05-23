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
  "SAM.gov":              "#c2714f",   // coral-600 — primary, most prominent
  "nyscr.ny.gov":         "#d4845f",   // coral-500/muted
  "data.cityofnewyork.us":"#b8956a",   // warm amber
  "data.cityofchicago.org":"#a89080",  // warm taupe
  "caleprocure.ca.gov":   "#c9956c",   // sandy amber
  "eva.virginia.gov":     "#b07d6b",   // dusty rose-brown
  "txsmartbuy.gov":       "#c08060",   // terracotta
  "doas.ga.gov":          "#a87c70",   // muted clay
  "vita.virginia.gov":    "#b89080",   // warm mauve
  "bidbuy.illinois.gov":  "#c09878",   // warm sand
  "dms.myflorida.com":    "#b88870",   // soft sienna
  "nyc_contract_awards":  "#c4906a",   // warm peach
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
      color: PORTAL_COLORS[r.source_portal as string] || "#c09880",
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
