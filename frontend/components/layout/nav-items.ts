import { LayoutDashboard, FileSearch, Bookmark, LineChart } from "lucide-react";

export const NAV_ITEMS: {
  href: string;
  label: string;
  icon: typeof LayoutDashboard;
  disabled?: boolean;
}[] = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/contracts", label: "Contracts", icon: FileSearch },
  { href: "/trends", label: "Trends", icon: LineChart },
  { href: "/contracts?saved=1", label: "Watchlist", icon: Bookmark, disabled: true },
] as const;
