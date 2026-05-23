import type { ContractStatus } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { statusBadgeVariant, statusLabel } from "@/lib/status";

export function StatusBadge({ status }: { status: ContractStatus }) {
  return <Badge variant={statusBadgeVariant(status)}>{statusLabel(status)}</Badge>;
}
