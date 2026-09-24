import { Badge } from "@/components/ui/badge";
import { useAdmin } from "@/lib/admin-store";

export function LogsView() {
  const logs = useAdmin((s) => s.logs);
  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <header>
        <p className="text-[11px] uppercase tracking-[0.18em] text-subtle">Logs</p>
        <h1 className="mt-1 font-display text-2xl font-semibold tracking-tight">Recent events</h1>
      </header>
      <ol className="divide-y divide-border overflow-hidden rounded-lg border border-border bg-surface">
        {logs.map((log) => (
          <li key={log.id} className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:items-start sm:gap-4">
            <span className="font-mono text-xs text-subtle tabular-nums">{log.at}</span>
            <Badge tone={log.level === "error" ? "danger" : log.level === "warn" ? "warn" : "ok"}>
              {log.level}
            </Badge>
            <p className="text-sm text-foreground">{log.message}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}
