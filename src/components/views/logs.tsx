import { Badge } from "@/components/ui/badge";
import { HudKicker, HudPanel } from "@/components/hud/panel";
import { useAdmin } from "@/lib/admin-store";

export function LogsView() {
  const logs = useAdmin((s) => s.logs);
  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <header>
        <HudKicker>Logs</HudKicker>
        <h1 className="mt-1 font-display text-2xl font-semibold">Recent events</h1>
      </header>
      <HudPanel className="p-0 sm:p-0">
        <ol>
          {logs.map((log) => (
            <li key={log.id} className="flex flex-col gap-1 border-b border-border/50 px-4 py-3 last:border-0 sm:flex-row sm:items-start sm:gap-4">
              <span className="font-display text-xs tracking-widest text-subtle tabular-nums">{log.at}</span>
              <Badge tone={log.level === "error" ? "danger" : log.level === "warn" ? "warn" : "ok"}>
                {log.level}
              </Badge>
              <p className="text-sm text-foreground">{log.message}</p>
            </li>
          ))}
        </ol>
      </HudPanel>
    </div>
  );
}
