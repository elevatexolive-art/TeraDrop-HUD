import type { ReactNode } from "react";
import { ParticleField } from "./particle-field";

export function HudBackdrop({ children }: { children: ReactNode }) {
  return (
    <div className="relative min-h-dvh overflow-hidden bg-bg text-foreground">
      <ParticleField />
      <div className="hud-floor" aria-hidden />
      <div className="hud-vignette" aria-hidden />
      <div
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-[18%] z-0 size-[min(70vw,520px)] -translate-x-1/2"
        style={{ perspective: "900px" }}
      >
        <span
          className="hud-orbit absolute inset-0"
          style={{ animation: "hud-spin 36s linear infinite" }}
        />
        <span
          className="hud-orbit absolute inset-[12%]"
          style={{ animation: "hud-spin-rev 22s linear infinite", opacity: 0.7 }}
        />
        <span
          className="hud-orbit absolute inset-[28%]"
          style={{ animation: "hud-spin 14s linear infinite", opacity: 0.45 }}
        />
      </div>
      <div className="hud-scanlines" aria-hidden />
      <div className="relative z-10">{children}</div>
    </div>
  );
}
