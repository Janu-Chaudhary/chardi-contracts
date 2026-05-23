import type { OpportunityRow } from "@/lib/api-types";
import type { Contract, ContractStatus } from "@/lib/types";

const VALID_STATUS: ContractStatus[] = ["OPEN", "CLOSED", "AWARDED", "CANCELLED"];

function normalizeStatus(raw: string | null | undefined): ContractStatus {
  const upper = String(raw ?? "OPEN").toUpperCase();
  if (VALID_STATUS.includes(upper as ContractStatus)) {
    return upper as ContractStatus;
  }
  return "OPEN";
}

function toNumber(val: number | string | null | undefined): number | null {
  if (val == null || val === "") return null;
  const n = typeof val === "number" ? val : parseFloat(String(val));
  return Number.isFinite(n) ? n : null;
}

function normalizeRegion(
  raw: string | null | undefined
): "Federal" | "State" {
  return raw === "State" ? "State" : "Federal";
}

export function mapOpportunity(row: OpportunityRow): Contract {
  return {
    id: row.id,
    title: row.title?.trim() || "Untitled opportunity",
    agency: row.buyer_name?.trim() || "Unknown agency",
    vendor: null,
    amount: toNumber(row.value_numeric),
    deadline: row.deadline ?? null,
    postedDate: row.posted_date ?? null,
    status: normalizeStatus(row.status),
    portal: row.source_portal ?? "Unknown",
    portalRegion: normalizeRegion(row.portal_region),
    state: row.state_region ?? null,
    noticeType: row.notice_type ?? null,
    industry: row.industry ?? null,
    sourceUrl: row.source_url ?? null,
    description: row.description ?? null,
    solicitationNumber: row.solicitation_number ?? null,
    buyerType: row.buyer_type ?? null,
    documents: row.documents,
    lastSeenAt: row.last_seen_at ?? null,
    createdAt: row.created_at ?? null,
    updatedAt: row.updated_at ?? null,
    currency: row.currency ?? null,
    naicsCode: row.naics_code ?? null,
  };
}

export function mapOpportunities(rows: OpportunityRow[]): Contract[] {
  return rows.map(mapOpportunity);
}
