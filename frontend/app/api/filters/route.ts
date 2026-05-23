import { NextResponse } from "next/server";
import { query, VALID_US_STATES } from "@/lib/db";

export const runtime = "edge";

// Cache for 5 minutes — filter values change rarely
export const revalidate = 300;

export async function GET() {
  try {
    const [states, portals, statuses, buyerTypes, noticeTypes, industries] =
      await Promise.all([
        // Only valid US states, sorted by count
        query(`
          SELECT state_region as value, COUNT(*) as count
          FROM opportunities
          WHERE state_region = ANY($1::text[])
          GROUP BY state_region
          ORDER BY count DESC
        `, [Array.from(VALID_US_STATES)]),

        // All portals with labels
        query(`
          SELECT source_portal as value, COUNT(*) as count
          FROM opportunities
          GROUP BY source_portal
          ORDER BY count DESC
        `),

        // Statuses
        query(`
          SELECT status as value, COUNT(*) as count
          FROM opportunities
          GROUP BY status
          ORDER BY count DESC
        `),

        // Buyer types — normalize OFFICE → Federal Agency
        query(`
          SELECT
            CASE buyer_type
              WHEN 'OFFICE' THEN 'Federal Agency'
              ELSE buyer_type
            END as value,
            COUNT(*) as count
          FROM opportunities
          WHERE buyer_type IS NOT NULL
          GROUP BY 1
          ORDER BY count DESC
        `),

        // Notice types (top 20)
        query(`
          SELECT notice_type as value, COUNT(*) as count
          FROM opportunities
          WHERE notice_type IS NOT NULL
          GROUP BY notice_type
          ORDER BY count DESC
          LIMIT 20
        `),

        // Industries (top 30, non-numeric only for display)
        query(`
          SELECT industry as value, COUNT(*) as count
          FROM opportunities
          WHERE industry IS NOT NULL
          GROUP BY industry
          ORDER BY count DESC
          LIMIT 30
        `),
      ]);

    // Portal display labels
    const portalLabels: Record<string, string> = {
      "nyscr.ny.gov": "New York (NYSCR)",
      "caleprocure.ca.gov": "California (CaleProcure)",
      "eva.virginia.gov": "Virginia (eVA)",
      "txsmartbuy.gov": "Texas (TxSmartBuy)",
      "vita.virginia.gov": "Virginia (VITA)",
      "SAM.gov": "Federal (SAM.gov)",
      "doas.ga.gov": "Georgia (TGM)",
      "bidbuy.illinois.gov": "Illinois (BidBuy)",
      "dms.myflorida.com": "Florida (DMS)",
    };

    return NextResponse.json({
      states: states.map((r) => ({
        value: r.value,
        label: r.value,
        count: parseInt(String(r.count)),
      })),
      portals: portals.map((r) => ({
        value: r.value,
        label: portalLabels[r.value as string] || r.value,
        count: parseInt(String(r.count)),
      })),
      statuses: statuses.map((r) => ({
        value: r.value,
        label: r.value,
        count: parseInt(String(r.count)),
      })),
      buyer_types: buyerTypes.map((r) => ({
        value: r.value,
        label: r.value,
        count: parseInt(String(r.count)),
      })),
      notice_types: noticeTypes.map((r) => ({
        value: r.value,
        label: r.value,
        count: parseInt(String(r.count)),
      })),
      industries: industries.map((r) => ({
        value: r.value,
        label: r.value,
        count: parseInt(String(r.count)),
      })),
    });
  } catch (err) {
    console.error("filters API error:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
