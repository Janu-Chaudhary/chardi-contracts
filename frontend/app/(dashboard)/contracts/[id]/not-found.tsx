import Link from "next/link";
import { FileQuestion } from "lucide-react";
import { EmptyState } from "@/components/states/empty-state";
import { Button } from "@/components/ui/button";

export default function ContractNotFound() {
  return (
    <div className="py-12">
      <EmptyState
        icon={FileQuestion}
        title="Contract not found"
        description="This record may have been removed or the link is incorrect."
      />
      <div className="mt-6 flex justify-center">
        <Button asChild>
          <Link href="/contracts">Back to contracts</Link>
        </Button>
      </div>
    </div>
  );
}
