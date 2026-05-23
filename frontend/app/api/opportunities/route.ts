import { NextRequest, NextResponse } from "next/server";
import { query } from "@/lib/db";

export const runtime = "edge";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);

  // Parse all filter params
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
  // value_min / value_max: no data yet — accepted but ignored
  const page = Math.max(1, parseInt(searchParams.get("page") || "1"));
  const limit = Math.min(100, Math.max(1, parseInt(searchParams.get("limit") || "20")));
  const sort = searchParams.get("sort") || "deadline";
  const order = searchParams.get("order") === "asc" ? "ASC" : "DESC";
  const offset = (page - 1) * limit;

  // Allowed sort columns (whitelist to prevent SQL injection)
  const allowedSorts: Record<string, string> = {
    deadline: "deadline",
    posted_date: "posted_date",
    title: "title",
    created_at: "created_at",
    buyer_name: "buyer_name",
    state_region: "state_region",
  };
  const sortCol = allowedSorts[sort] || "deadline";

  // Build WHERE clauses dynamically
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

  if (status) {
    conditions.push(`status = $${paramIdx}`);
    params.push(status.toUpperCase());
    paramIdx++;
  }

  if (portal) {
    conditions.push(`source_portal = $${paramIdx}`);
    params.push(portal);
    paramIdx++;
  }

  if (portalRegion) {
    conditions.push(`portal_region = $${paramIdx}`);
    params.push(portalRegion);
    paramIdx++;
  }

  if (buyerType) {
    conditions.push(`buyer_type = $${paramIdx}`);
    params.push(buyerType);
    paramIdx++;
  }

  if (noticeType) {
    conditions.push(`notice_type = $${paramIdx}`);
    params.push(noticeType);
    paramIdx++;
  }

  if (industry) {
    conditions.push(`industry ILIKE $${paramIdx}`);
    params.push(`%${industry}%`);
    paramIdx++;
  }

  if (deadlineFrom) {
    conditions.push(`deadline >= $${paramIdx}::timestamptz`);
    params.push(deadlineFrom);
    paramIdx++;
  }

  if (deadlineTo) {
    conditions.push(`deadline <= $${paramIdx}::timestamptz`);
    params.push(deadlineTo);
    paramIdx++;
  }

  if (postedFrom) {
    conditions.push(`posted_date >= $${paramIdx}::timestamptz`);
    params.push(postedFrom);
    paramIdx++;
  }

  if (postedTo) {
    conditions.push(`posted_date <= $${paramIdx}::timestamptz`);
    params.push(postedTo);
    paramIdx++;
  }

  const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : "";

  try {
    // Run data + count queries in parallel
    const dataQuery = `
      SELECT
        id, source_portal, source_record_id, solicitation_number,
        portal_region, title, description, notice_type,
        TO_CHAR(posted_date AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as posted_date,
        TO_CHAR(deadline AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as deadline,
        state_region, industry, naics_code,
        value_numeric, value_min, value_max, currency,
        status, buyer_name, buyer_type, source_url
      FROM opportunities
      ${whereClause}
      ORDER BY ${sortCol} ${order} NULLS LAST
      LIMIT $${paramIdx} OFFSET $${paramIdx + 1}
    `;

    const countQuery = `
      SELECT COUNT(*) as total FROM opportunities ${whereClause}
    `;

    const [rows, countResult] = await Promise.all([
      query(dataQuery, [...params, limit, offset]),
      query(countQuery, params),
    ]);

    const total = parseInt(String(countResult[0]?.total || "0"));
    const totalPages = Math.ceil(total / limit);

    return NextResponse.json({
      data: rows,
      pagination: {
        page,
        limit,
        total,
        total_pages: totalPages,
        has_next: page < totalPages,
        has_prev: page > 1,
      },
      filters_applied: {
        q, state, status, portal, portal_region: portalRegion,
        buyer_type: buyerType, notice_type: noticeType, industry,
        deadline_from: deadlineFrom, deadline_to: deadlineTo,
        posted_from: postedFrom, posted_to: postedTo,
        sort, order, page, limit,
      },
    });
  } catch (err) {
    console.error("opportunities API error:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
