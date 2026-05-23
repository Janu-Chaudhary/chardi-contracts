"use client";

import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * BackButton — uses router.back() so the browser restores the previous
 * URL (including all filter search params) when returning from a detail page.
 */
export function BackButton() {
  const router = useRouter();

  return (
    <Button
      variant="ghost"
      size="sm"
      className="-ml-2 mb-4"
      onClick={() => router.back()}
    >
      <ArrowLeft className="h-4 w-4" aria-hidden />
      Back to contracts
    </Button>
  );
}
