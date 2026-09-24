import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function HudPanel({
  className,
  children,
  sweep = false,
}: {
  className?: string;
  children: ReactNode;
  sweep?: boolean;
}) {
  return (
    <section className={cn("hud-panel p-4 sm:p-5", sweep && "hud-sweep overflow-hidden", className)}>
      {children}
    </section>
  );
}

export function HudKicker({ children }: { children: ReactNode }) {
  return <p className="hud-kicker">{children}</p>;
}
