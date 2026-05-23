import { AlertCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export function ErrorState({
  message = "Something went wrong while loading contracts.",
  onRetry,
}: ErrorStateProps) {
  return (
    <Card className="border-destructive/20">
      <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
        <AlertCircle className="h-8 w-8 text-destructive" aria-hidden />
        <div className="max-w-sm space-y-2">
          <h3 className="font-display text-lg font-semibold">Unable to load data</h3>
          <p className="text-sm text-muted-foreground">{message}</p>
        </div>
        {onRetry && (
          <Button variant="outline" onClick={onRetry}>
            Try again
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
