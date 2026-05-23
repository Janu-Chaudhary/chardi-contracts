import Link from "next/link";
import { ArrowLeft, ExternalLink, FileText, Building2, Calendar, DollarSign } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { StatusBadge } from "@/components/contracts/status-badge";
import { WinnersSidebar } from "@/components/contracts/winners-sidebar";
import type { Contract } from "@/lib/types";
import { cn, formatCurrency, formatDate, hasCurrencyValue } from "@/lib/utils";
import { stateLabel } from "@/lib/state-names";

interface ContractDetailProps {
  contract: Contract;
}

function MetaBlock({
  label,
  value,
  icon: Icon,
  valueClassName,
  statValue = false,
}: {
  label: string;
  value: string;
  icon?: React.ComponentType<{ className?: string }>;
  valueClassName?: string;
  /** Use marketing-style Playfair numerals (e.g. amount KPIs). */
  statValue?: boolean;
}) {
  return (
    <div className="min-w-0">
      <dt className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {Icon && <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden />}
        {label}
      </dt>
      <dd
        className={cn(
          statValue ? "mt-1.5 font-stat-md" : "mt-1.5 text-sm font-medium text-warm-black",
          valueClassName
        )}
      >
        {value}
      </dd>
    </div>
  );
}

export function ContractDetail({ contract }: ContractDetailProps) {
  return (
    <article className="space-y-8">
      <div>
        <Button variant="ghost" size="sm" className="-ml-2 mb-4" asChild>
          <Link href="/contracts">
            <ArrowLeft className="h-4 w-4" aria-hidden />
            Back to contracts
          </Link>
        </Button>

        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 space-y-3">
            <StatusBadge status={contract.status} />
            <h1 className="font-display text-2xl font-semibold leading-tight sm:text-3xl">
              {contract.title}
            </h1>
            <p className="flex items-center gap-2 text-muted-foreground">
              <Building2 className="h-4 w-4 shrink-0" aria-hidden />
              {contract.agency}
            </p>
          </div>
          {contract.sourceUrl && (
            <Button variant="outline" className="shrink-0 w-full sm:w-auto" asChild>
              <a href={contract.sourceUrl} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-4 w-4" aria-hidden />
                View source
              </a>
            </Button>
          )}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="interactive hover:bg-warm-50/50">
          <CardContent className="p-5">
            <MetaBlock
              label="Amount"
              value={formatCurrency(contract.amount)}
              icon={DollarSign}
              statValue={hasCurrencyValue(contract.amount)}
              valueClassName={
                !hasCurrencyValue(contract.amount)
                  ? "italic text-muted-foreground"
                  : undefined
              }
            />
          </CardContent>
        </Card>
        <Card className="interactive hover:bg-warm-50/50">
          <CardContent className="p-5">
            <MetaBlock label="Due date" value={formatDate(contract.deadline)} icon={Calendar} />
          </CardContent>
        </Card>
        <Card className="interactive hover:bg-warm-50/50">
          <CardContent className="p-5">
            <MetaBlock label="Posted" value={formatDate(contract.postedDate)} icon={Calendar} />
          </CardContent>
        </Card>
        <Card className="interactive hover:bg-warm-50/50">
          <CardContent className="p-5">
            <MetaBlock label="Portal" value={contract.portal} />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="font-display text-lg">Description</CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-sm leading-relaxed text-warm-900">
                {contract.description ??
                  "No description available. Full text will load from the source portal once integrated."}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="font-display text-lg">Award & vendor</CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <dl className="grid gap-4 sm:grid-cols-2">
                <MetaBlock label="Vendor" value={contract.vendor ?? "Not specified"} />
                <MetaBlock label="Buyer type" value={contract.buyerType ?? "Not specified"} />
                <MetaBlock label="Industry" value={contract.industry ?? "Not specified"} />
                <MetaBlock
                  label="Solicitation #"
                  value={contract.solicitationNumber ?? "Not available"}
                />
              </dl>
            </CardContent>
          </Card>
        </div>

        <div className="min-w-0 space-y-6">
          <Card className="overflow-hidden">
            <CardHeader>
              <CardTitle className="font-display text-lg">Metadata</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 pt-0">
              <dl className="space-y-4">
                <MetaBlock label="Region" value={contract.portalRegion} />
                <MetaBlock label="State" value={stateLabel(contract.state)} />
                <MetaBlock label="Notice type" value={contract.noticeType ?? "Not specified"} />
                <MetaBlock
                  label="Record ID"
                  value={contract.id}
                  valueClassName="break-all font-mono text-xs leading-relaxed text-warm-900"
                />
              </dl>
            </CardContent>
          </Card>

          {/* Award enrichment — lazy loaded, zero blocking */}
          <WinnersSidebar
            opportunityId={contract.id}
            industry={contract.industry}
          />

          <Card>
            <CardHeader>
              <CardTitle className="font-display text-lg">Attachments</CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              {contract.documents &&
              typeof contract.documents === "object" &&
              contract.documents !== null &&
              Object.keys(contract.documents as object).length > 0 ? (
                <pre className="max-h-48 overflow-auto rounded-lg bg-warm-200/50 p-3 text-xs">
                  {JSON.stringify(contract.documents, null, 2)}
                </pre>
              ) : (
                <div className="flex items-center gap-3 rounded-lg border border-dashed border-border bg-warm-50/50 p-4">
                  <FileText className="h-5 w-5 text-muted-foreground" aria-hidden />
                  <p className="text-sm text-muted-foreground">
                    No attachments indexed for this record yet.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="font-display text-lg">Activity</CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <Separator className="mb-4" />
              <ul className="space-y-4 text-sm">
                <li className="flex gap-3">
                  <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-coral-500" />
                  <div>
                    <p className="font-medium">Last seen in scrape</p>
                    <p className="text-muted-foreground">
                      {formatDate(contract.lastSeenAt ?? contract.updatedAt)}
                    </p>
                  </div>
                </li>
                {contract.createdAt && (
                  <li className="flex gap-3 text-muted-foreground">
                    <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-warm-300" />
                    <div>
                      <p className="font-medium text-warm-900">First indexed</p>
                      <p>{formatDate(contract.createdAt)}</p>
                    </div>
                  </li>
                )}
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </article>
  );
}
