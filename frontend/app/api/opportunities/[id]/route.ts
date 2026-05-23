import { NextRequest, NextResponse } from "next/server";
import { query } from "@/lib/db";

export const runtime = "edge";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  if (!id) {
    return NextResponse.json({ error: "ID is required" }, { status: 400 });
  }

  try {
    const rows = await query(
      `SELECT
        id, source_portal, source_record_id, solicitation_number,
        portal_region, title, description, notice_type,
        TO_CHAR(posted_date AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as posted_date,
        TO_CHAR(deadline AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as deadline,
        state_region, industry, naics_code,
        value_numeric, value_min, value_max, currency,
        status, buyer_name, buyer_type, source_url,
        documents,
        TO_CHAR(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as created_at,
        TO_CHAR(updated_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as updated_at,
        TO_CHAR(last_seen_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as last_seen_at
       FROM opportunities
       WHERE id = $1`,
      [id]
    );

    if (!rows || rows.length === 0) {
      return NextResponse.json({ error: "Opportunity not found" }, { status: 404 });
    }

    return NextResponse.json({ data: rows[0] });
  } catch (err) {
    console.error("opportunity detail API error:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
