import { NextRequest, NextResponse } from "next/server";
import { query } from "@/lib/db";

export const runtime = "edge";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const format = searchParams.get("format") === "json" ? "json" : "csv";

  // Same filters as /api/opportunities — no pagination
  const q = searchParams.get("q")?.trim() || null;
  const state = searchParams.get("state") || null;
  const status = searchParams.get("status") || null;
  const portal = searchParams.get("portal") || null;
  const portalRegion = searchParams.get("portal_region") || null;
  const buyerType = searchParams.get("buyer_type") || null;
  const noticeType = searchParams.get("notice_type") || null;
  const industry = searchParams.get("industry") || null;
  const deadlineFrom = searchParams.get("deadline_from") || null;
  const deadlineTo = searchParams.get("deadline_to") || null;
  const postedFrom = searchParams.get("posted_from") || null;
  const postedTo = searchParams.get("posted_to") || null;

  const conditions: string[] = [];
  const params: (string | number)[] = [];
  let paramIdx = 1;

  if (q) {
    conditions.push(`(title ILIKE $${paramIdx} OR description ILIKE $${paramIdx} OR buyer_name ILIKE $${paramIdx})`);
    params.push(`%${q}%`);
    paramIdx++;
  }
  if (state) {
    const states = state.split(",").map((s) => s.trim()).filter(Boolean);
    if (states.length === 1) {
      conditions.push(`state_region = $${paramIdx}`);
      params.push(states[0]);
      paramIdx++;
    } else if (states.length > 1) {
      const placeholders = states.map((_, i) => `$${paramIdx + i}`).join(", ");
      conditions.push(`state_region IN (${placeholders})`);
      params.push(...states);
      paramIdx += states.length;
    }
  }
  if (status) { conditions.push(`status = $${paramIdx}`); params.push(status.toUpperCase()); paramIdx++; }
  if (portal) { conditions.push(`source_portal = $${paramIdx}`); params.push(portal); paramIdx++; }
  if (portalRegion) { conditions.push(`portal_region = $${paramIdx}`); params.push(portalRegion); paramIdx++; }
  if (buyerType) { conditions.push(`buyer_type = $${paramIdx}`); params.push(buyerType); paramIdx++; }
  if (noticeType) { conditions.push(`notice_type = $${paramIdx}`); params.push(noticeType); paramIdx++; }
  if (industry) { conditions.push(`industry ILIKE $${paramIdx}`); params.push(`%${industry}%`); paramIdx++; }
  if (deadlineFrom) { conditions.push(`deadline >= $${paramIdx}::timestamptz`); params.push(deadlineFrom); paramIdx++; }
  if (deadlineTo) { conditions.push(`deadline <= $${paramIdx}::timestamptz`); params.push(deadlineTo); paramIdx++; }
  if (postedFrom) { conditions.push(`posted_date >= $${paramIdx}::timestamptz`); params.push(postedFrom); paramIdx++; }
  if (postedTo) { conditions.push(`posted_date <= $${paramIdx}::timestamptz`); params.push(postedTo); paramIdx++; }

  const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : "";

  try {
    const rows = await query(
      `SELECT
        id, source_portal, source_record_id, solicitation_number,
        portal_region, title, description, notice_type,
        TO_CHAR(posted_date AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as posted_date,
        TO_CHAR(deadline AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as deadline,
        state_region, industry, naics_code,
        value_numeric, currency, status, buyer_name, buyer_type, source_url
       FROM opportunities
       ${whereClause}
       ORDER BY deadline DESC NULLS LAST
       LIMIT 5000`,
      params
    );

    const timestamp = new Date().toISOString().slice(0, 10);

    if (format === "json") {
      return new NextResponse(JSON.stringify(rows, null, 2), {
        headers: {
          "Content-Type": "application/json",
          "Content-Disposition": `attachment; filename="chardi-opportunities-${timestamp}.json"`,
        },
      });
    }

    // CSV format
    if (rows.length === 0) {
      return new NextResponse("No data found", { status: 404 });
    }

    const headers = Object.keys(rows[0] as object);
    const csvRows = [
      headers.join(","),
      ...rows.map((row) =>
        headers
          .map((h) => {
            const val = (row as Record<string, unknown>)[h];
            if (val === null || val === undefined) return "";
            const str = String(val).replace(/"/g, '""');
            return str.includes(",") || str.includes('"') || str.includes("\n")
              ? `"${str}"`
              : str;
          })
          .join(",")
      ),
    ].join("\n");

    return new NextResponse(csvRows, {
      headers: {
        "Content-Type": "text/csv",
        "Content-Disposition": `attachment; filename="chardi-opportunities-${timestamp}.csv"`,
      },
    });
  } catch (err) {
    console.error("export API error:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
