import {
  ExternalLink,
  FileText,
  Building2,
  Calendar,
  DollarSign,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { StatusBadge } from "@/components/contracts/status-badge";
import { WinnersSidebar } from "@/components/contracts/winners-sidebar";
import { BackButton } from "@/components/contracts/back-button";
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
  statValue?: boolean;
}) {
  return (
    <div className="min-w-0 w-full overflow-hidden">
      <dt className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {Icon && <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden />}
        {label}
      </dt>
      <dd
        className={cn(
          "w-full",
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
    <article className="w-full min-w-0 space-y-4">

      {/* ── Header ─────────────────────────────────────────────── */}
      <div className="w-full min-w-0">
        <BackButton />
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 flex-1 space-y-2 overflow-hidden">
            <StatusBadge status={contract.status} />
            <h1 className="font-display text-xl font-semibold leading-tight sm:text-2xl lg:text-3xl break-words hyphens-auto">
              {contract.title}
            </h1>
            <p className="flex min-w-0 items-center gap-2 text-sm text-muted-foreground">
              <Building2 className="h-4 w-4 shrink-0" aria-hidden />
              <span className="min-w-0 truncate">{contract.agency}</span>
            </p>
          </div>
          {contract.sourceUrl && (
            <Button variant="outline" size="sm" className="mt-1 shrink-0 w-full sm:w-auto" asChild>
              <a href={contract.sourceUrl} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-4 w-4" aria-hidden />
                View source
              </a>
            </Button>
          )}
        </div>
      </div>

      {/* ── KPI strip ──────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
        {[
          {
            label: "Amount",
            value: formatCurrency(contract.amount),
            icon: DollarSign,
            statValue: hasCurrencyValue(contract.amount),
            valueClassName: !hasCurrencyValue(contract.amount) ? "italic text-muted-foreground" : undefined,
          },
          { label: "Due date", value: formatDate(contract.deadline), icon: Calendar },
          { label: "Posted",   value: formatDate(contract.postedDate), icon: Calendar },
          { label: "Portal",   value: contract.portal },
        ].map((item) => (
          <Card key={item.label} className="interactive-card overflow-hidden">
            <CardContent className="p-3 sm:p-4">
              <MetaBlock
                label={item.label}
                value={item.value}
                icon={item.icon}
                statValue={item.statValue}
                valueClassName={item.valueClassName}
              />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* ── MOBILE: flat single-column stack ───────────────────── */}
      {/* ── DESKTOP (lg+): 2-col main + 1-col sidebar ─────────── */}
      <div className="lg:grid lg:grid-cols-3 lg:gap-5">

        {/* ── Main content column ── */}
        <div className="w-full min-w-0 space-y-4 lg:col-span-2">

          {/* Description */}
          <Card className="interactive-card w-full overflow-hidden">
            <CardHeader className="px-4 pb-2 pt-4">
              <CardTitle className="font-display text-base">Description</CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4 pt-0">
              <p className="w-full break-words text-sm leading-relaxed text-warm-900 [overflow-wrap:anywhere]">
                {contract.description ??
                  "No description available. Full text will load from the source portal once integrated."}
              </p>
            </CardContent>
          </Card>

          {/* Award & vendor */}
          <Card className="interactive-card w-full overflow-hidden">
            <CardHeader className="px-4 pb-2 pt-4">
              <CardTitle className="font-display text-base">Award &amp; vendor</CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4 pt-0">
              <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <MetaBlock label="Vendor"        value={contract.vendor ?? "Not specified"} />
                <MetaBlock label="Buyer type"    value={contract.buyerType ?? "Not specified"} />
                <MetaBlock label="Industry"      value={contract.industry ?? "Not specified"} />
                <MetaBlock label="Solicitation #" value={contract.solicitationNumber ?? "Not available"} />
              </dl>
            </CardContent>
          </Card>

          {/* Attachments */}
          <Card className="interactive-card w-full overflow-hidden">
            <CardHeader className="px-4 pb-2 pt-4">
              <CardTitle className="font-display text-base">Attachments</CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4 pt-0">
              {contract.documents &&
              typeof contract.documents === "object" &&
              contract.documents !== null &&
              Object.keys(contract.documents as object).length > 0 ? (
                <pre className="w-full max-h-40 overflow-auto rounded-lg bg-warm-200/50 p-3 text-xs leading-relaxed whitespace-pre-wrap break-all">
                  {JSON.stringify(contract.documents, null, 2)}
                </pre>
              ) : (
                <div className="flex items-center gap-3 rounded-lg border border-dashed border-border bg-warm-50/50 p-4">
                  <FileText className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
                  <p className="text-sm text-muted-foreground">
                    No attachments indexed for this record yet.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* ── Sidebar column ── */}
        {/* On mobile: renders after main content (correct DOM order) */}
        {/* On lg+: floats right as 1-col sidebar */}
        <div className="mt-4 w-full min-w-0 space-y-4 lg:mt-0">

          {/* Metadata */}
          <Card className="interactive-card w-full overflow-hidden">
            <CardHeader className="px-4 pb-2 pt-4">
              <CardTitle className="font-display text-base">Metadata</CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4 pt-0">
              <dl className="space-y-3">
                <MetaBlock label="Region"      value={contract.portalRegion} />
                <MetaBlock label="State"       value={stateLabel(contract.state)} />
                <MetaBlock label="Notice type" value={contract.noticeType ?? "Not specified"} />
                <MetaBlock
                  label="Record ID"
                  value={contract.id}
                  valueClassName="break-all font-mono text-[11px] leading-relaxed text-warm-900 [overflow-wrap:anywhere]"
                />
              </dl>
            </CardContent>
          </Card>

          {/* Award enrichment */}
          <WinnersSidebar
            opportunityId={contract.id}
            industry={contract.industry}
          />

          {/* Activity */}
          <Card className="interactive-card w-full overflow-hidden">
            <CardHeader className="px-4 pb-2 pt-4">
              <CardTitle className="font-display text-base">Activity</CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4 pt-0">
              <Separator className="mb-3" />
              <ul className="space-y-3">
                <li className="flex gap-3">
                  <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-coral-500" />
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium text-warm-900">Last seen in scrape</p>
                    <p className="text-xs text-muted-foreground">
                      {formatDate(contract.lastSeenAt ?? contract.updatedAt)}
                    </p>
                  </div>
                </li>
                {contract.createdAt && (
                  <li className="flex gap-3">
                    <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-warm-300" />
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium text-warm-900">First indexed</p>
                      <p className="text-xs text-muted-foreground">
                        {formatDate(contract.createdAt)}
                      </p>
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
