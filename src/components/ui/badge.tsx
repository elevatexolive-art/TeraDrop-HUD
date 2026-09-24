import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Badge({
  className,
  tone = "neutral",
  children,
}: {
  className?: string;
  tone?: "neutral" | "live" | "restart" | "ok" | "warn" | "danger";
  children: ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 font-display text-xs font-medium uppercase tracking-[0.16em]",
        tone === "neutral" && "bg-surface-2 text-muted-foreground",
        tone === "live" && "bg-ok/15 text-ok",
        tone === "restart" && "bg-warn/15 text-warn",
        tone === "ok" && "bg-ok/15 text-ok",
        tone === "warn" && "bg-warn/15 text-warn",
        tone === "danger" && "bg-danger/15 text-danger",
        className,
      )}
    >
      {children}
    </span>
  );
}
