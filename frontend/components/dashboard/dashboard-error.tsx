import { ErrorState } from "@/components/states/error-state";

export function DashboardError({ message }: { message?: string }) {
  return (
    <ErrorState
      message={message ?? "Could not load dashboard data from the API."}
    />
  );
}
