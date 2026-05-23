import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-warm-200 text-warm-900",
        accent: "border-transparent bg-coral-500/15 text-warm-black",
        open: "border-transparent bg-emerald-50 text-emerald-800",
        closed: "border-transparent bg-warm-200 text-muted-foreground",
        awarded: "border-transparent bg-coral-500/15 text-warm-900",
        cancelled: "border-transparent bg-red-50 text-red-800",
        outline: "border-warm-300 text-warm-900",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
