import type { Contract } from "@/lib/types";

/**
 * @deprecated Demo-only fixtures. The dashboard uses live /api/* routes.
 * Kept for local UI experiments without a database.
 */
export const MOCK_CONTRACTS: Contract[] = [
  {
    id: "a1b2c3",
    title: "Enterprise Cloud Infrastructure Modernization",
    agency: "Department of Veterans Affairs",
    vendor: "Accenture Federal Services",
    amount: 4200000,
    deadline: "2026-06-15",
    postedDate: "2026-04-02",
    status: "OPEN",
    portal: "SAM.gov",
    portalRegion: "Federal",
    state: "VA",
    noticeType: "Solicitation",
    industry: "IT Services",
    sourceUrl: "https://sam.gov",
    solicitationNumber: "36C10B26Q0042",
    buyerType: "Federal",
    description:
      "Seeking a qualified vendor to modernize legacy cloud infrastructure across regional VA medical centers.",
  },
  {
    id: "d4e5f6",
    title: "HVAC Preventive Maintenance — State Facilities",
    agency: "Texas Facilities Commission",
    vendor: null,
    amount: 890000,
    deadline: "2026-05-30",
    postedDate: "2026-03-18",
    status: "OPEN",
    portal: "txsmartbuy.gov",
    portalRegion: "State",
    state: "TX",
    noticeType: "Term Contract",
    industry: "Facilities",
    sourceUrl: "https://txsmartbuy.gov",
    solicitationNumber: "031-A1",
  },
  {
    id: "g7h8i9",
    title: "Judicial Case Management System Upgrade",
    agency: "California Judicial Branch",
    vendor: "Tyler Technologies",
    amount: 12500000,
    deadline: "2026-02-28",
    postedDate: "2025-11-10",
    status: "AWARDED",
    portal: "caleprocure.ca.gov",
    portalRegion: "State",
    state: "CA",
    noticeType: "Award",
    industry: "Software",
    sourceUrl: "https://caleprocure.ca.gov",
  },
  {
    id: "j0k1l2",
    title: "Cybersecurity Operations Center Staff Augmentation",
    agency: "Department of Homeland Security",
    vendor: null,
    amount: 3100000,
    deadline: "2026-07-01",
    postedDate: "2026-04-20",
    status: "OPEN",
    portal: "SAM.gov",
    portalRegion: "Federal",
    state: "DC",
    noticeType: "Sources Sought",
    industry: "Cybersecurity",
    sourceUrl: "https://sam.gov",
    solicitationNumber: "70RSAT26R00001234",
  },
  {
    id: "m3n4o5",
    title: "Fleet Vehicle Leasing — Light Duty",
    agency: "New York Office of General Services",
    vendor: "Enterprise Fleet Management",
    amount: 2400000,
    deadline: "2026-01-15",
    postedDate: "2025-09-01",
    status: "CLOSED",
    portal: "nyscr.ny.gov",
    portalRegion: "State",
    state: "NY",
    noticeType: "Contract",
    industry: "Transportation",
    sourceUrl: "https://nyscr.ny.gov",
  },
  {
    id: "p6q7r8",
    title: "Statewide IT Infrastructure Services",
    agency: "Virginia Information Technologies Agency",
    vendor: "Carahsoft Technology Corp",
    amount: 8700000,
    deadline: "2027-03-31",
    postedDate: "2026-02-14",
    status: "OPEN",
    portal: "vita.virginia.gov",
    portalRegion: "State",
    state: "VA",
    noticeType: "Master Contract",
    industry: "IT Services",
    sourceUrl: "https://vita.virginia.gov",
  },
  {
    id: "s9t0u1",
    title: "Medical Supplies — Surgical Kits",
    agency: "Defense Logistics Agency",
    vendor: null,
    amount: 560000,
    deadline: "2026-05-10",
    postedDate: "2026-04-25",
    status: "OPEN",
    portal: "SAM.gov",
    portalRegion: "Federal",
    state: null,
    noticeType: "RFQ",
    industry: "Medical",
    sourceUrl: "https://sam.gov",
  },
  {
    id: "v2w3x4",
    title: "Roadway Resurfacing — District 4",
    agency: "Florida Department of Transportation",
    vendor: "Lane Construction",
    amount: 18400000,
    deadline: "2025-12-01",
    postedDate: "2025-06-20",
    status: "AWARDED",
    portal: "SAM.gov",
    portalRegion: "State",
    state: "FL",
    noticeType: "Award",
    industry: "Construction",
    sourceUrl: "https://sam.gov",
  },
];

export const MOCK_KPI = {
  total: 12847,
  open: 4210,
  federal: 8934,
  state: 3913,
  portals: 6,
  lastUpdated: "2026-05-22T14:30:00Z",
};

export function getContractById(id: string): Contract | undefined {
  return MOCK_CONTRACTS.find((c) => c.id === id);
}

export function filterContracts(
  contracts: Contract[],
  filters: {
    q?: string;
    status?: string;
    portalRegion?: string;
    state?: string;
    noticeType?: string;
  }
): Contract[] {
  const q = filters.q?.trim().toLowerCase();
  return contracts.filter((c) => {
    if (q) {
      const haystack = `${c.title} ${c.agency} ${c.vendor ?? ""} ${c.industry ?? ""}`.toLowerCase();
      if (!haystack.includes(q)) return false;
    }
    if (filters.status && c.status !== filters.status) return false;
    if (filters.portalRegion && c.portalRegion !== filters.portalRegion) return false;
    if (filters.state && c.state !== filters.state) return false;
    if (filters.noticeType && c.noticeType !== filters.noticeType) return false;
    return true;
  });
}
