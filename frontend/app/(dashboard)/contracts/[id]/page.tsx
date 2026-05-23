import { notFound } from "next/navigation";
import { ContractDetail } from "@/components/contracts/contract-detail";
import { getOpportunityByIdDirect } from "@/lib/data/server";
import { mapOpportunity } from "@/lib/map-opportunity";

interface ContractDetailPageProps {
  params: Promise<{ id: string }>;
}

export const dynamic = "force-dynamic";

export default async function ContractDetailPage({ params }: ContractDetailPageProps) {
  const { id } = await params;
  const row = await getOpportunityByIdDirect(id);

  if (!row) {
    notFound();
  }

  return <ContractDetail contract={mapOpportunity(row)} />;
}
