import { Bookmark } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

export function WatchlistPlaceholder() {
  return (
    <Card className="border-dashed">
      <CardContent className="flex items-start gap-4 p-5">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-warm-200">
          <Bookmark className="h-4 w-4 text-muted-foreground" aria-hidden />
        </div>
        <div>
          <h3 className="font-display text-base font-semibold">Saved filters & watchlist</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {/* TODO: user-saved searches */}
            Pin high-value searches and get alerts when new contracts match. Coming in a
            future release.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
