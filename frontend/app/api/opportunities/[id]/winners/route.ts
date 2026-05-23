/**
 * GET /api/opportunities/[id]/winners
 *
 * Returns the top vendors who have won similar contracts before,
 * matched by industry + state_region from the award_winners table.
 *
 * Zero latency: reads from pre-aggregated award_winners — two indexed lookups.
 * Response cached for 1 hour (award history doesn't change minute-to-minute).
 */

import { NextRequest, NextResponse } from "next/server";
import { query } from "@/lib/db";

export const runtime = "edge";

interface AwardWinner {
  vendor_name: string;
  industry: string;
  state_region: string | null;
  source_portal: string;
  win_count: number;
  total_value: number | null;
  avg_value: number | null;
  last_win_date: string | null;
}

interface OpportunityMeta {
  industry: string | null;
  state_region: string | null;
  title: string;
}

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  if (!id) {
    return NextResponse.json({ error: "ID is required" }, { status: 400 });
  }

  try {
    // Step 1: fetch industry + state from the opportunity (PK lookup — <1ms)
    const metaRows = await query<OpportunityMeta>(
      `SELECT industry, state_region, title
       FROM opportunities
       WHERE id = $1
       LIMIT 1`,
      [id]
    );

    if (!metaRows || metaRows.length === 0) {
      return NextResponse.json({ error: "Opportunity not found" }, { status: 404 });
    }

    const { industry, state_region, title } = metaRows[0];

    // Step 2: query award_winners by industry + state (indexed lookup — <5ms)
    // Falls back to industry-only if no state match found
    let winners: AwardWinner[] = [];

    if (industry) {
      winners = await query<AwardWinner>(
        `SELECT
           vendor_name,
           industry,
           state_region,
           source_portal,
           win_count,
           total_value,
           avg_value,
           TO_CHAR(last_win_date AT TIME ZONE 'UTC', 'YYYY-MM-DD') AS last_win_date
         FROM award_winners
         WHERE industry = $1
           AND ($2::text IS NULL OR state_region = $2 OR state_region IS NULL)
         ORDER BY win_count DESC
         LIMIT 10`,
        [industry, state_region ?? null]
      );
    }

    // If no industry match, fall back to full-text title similarity across all winners
    if (winners.length === 0) {
      winners = await query<AwardWinner>(
        `SELECT
           vendor_name,
           industry,
           state_region,
           source_portal,
           win_count,
           total_value,
           avg_value,
           TO_CHAR(last_win_date AT TIME ZONE 'UTC', 'YYYY-MM-DD') AS last_win_date
         FROM award_winners
         ORDER BY win_count DESC
         LIMIT 10`,
        []
      );
    }

    const response = NextResponse.json({
      opportunity_id: id,
      opportunity_title: title,
      matched_on: {
        industry: industry ?? null,
        state_region: state_region ?? null,
      },
      winners,
      total: winners.length,
    });

    // Cache for 1 hour — award history is refreshed by workers, not real-time
    response.headers.set("Cache-Control", "public, s-maxage=3600, stale-while-revalidate=86400");

    return response;
  } catch (err) {
    console.error("winners API error:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
