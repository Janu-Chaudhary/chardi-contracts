import { SearchX } from "lucide-react";
import { EmptyState } from "@/components/states/empty-state";

interface NoResultsStateProps {
  onClearFilters?: () => void;
}

export function NoResultsState({ onClearFilters }: NoResultsStateProps) {
  return (
    <EmptyState
      icon={SearchX}
      title="No contracts match your filters"
      description="Try broadening your search or clearing filters to see more opportunities."
      actionLabel="Clear all filters"
      onAction={onClearFilters}
    />
  );
}
