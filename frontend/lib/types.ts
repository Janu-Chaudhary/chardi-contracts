export type ContractStatus = "OPEN" | "CLOSED" | "AWARDED" | "CANCELLED";

export interface Contract {
  id: string;
  title: string;
  agency: string;
  vendor: string | null;
  amount: number | null;
  deadline: string | null;
  postedDate: string | null;
  status: ContractStatus;
  portal: string;
  portalRegion: "Federal" | "State";
  state: string | null;
  noticeType: string | null;
  industry: string | null;
  sourceUrl: string | null;
  description?: string | null;
  solicitationNumber?: string | null;
  buyerType?: string | null;
  documents?: unknown;
  lastSeenAt?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
  currency?: string | null;
  naicsCode?: string | null;
}

export interface ContractFilters {
  q: string;
  status: ContractStatus | "";
  portalRegion: "" | "Federal" | "State";
  portal: string;
  state: string;
  noticeType: string;
  buyerType: string;
  industry: string;
  /** ISO date string YYYY-MM-DD */
  deadlineFrom: string;
  /** ISO date string YYYY-MM-DD */
  deadlineTo: string;
  /** ISO date string YYYY-MM-DD */
  postedFrom: string;
  /** ISO date string YYYY-MM-DD */
  postedTo: string;
}

export type SortKey = "deadline" | "amount" | "title" | "agency";
export type SortOrder = "asc" | "desc";

export const DEFAULT_FILTERS: ContractFilters = {
  q: "",
  status: "",
  portalRegion: "",
  portal: "",
  state: "",
  noticeType: "",
  buyerType: "",
  industry: "",
  deadlineFrom: "",
  deadlineTo: "",
  postedFrom: "",
  postedTo: "",
};
