import type { ContractStatus } from "@/lib/types";
import type { BadgeProps } from "@/components/ui/badge";

export function statusBadgeVariant(status: ContractStatus): BadgeProps["variant"] {
  switch (status) {
    case "OPEN":
      return "open";
    case "CLOSED":
      return "closed";
    case "AWARDED":
      return "awarded";
    case "CANCELLED":
      return "cancelled";
    default:
      return "default";
  }
}

export function statusLabel(status: ContractStatus): string {
  return status.charAt(0) + status.slice(1).toLowerCase();
}
