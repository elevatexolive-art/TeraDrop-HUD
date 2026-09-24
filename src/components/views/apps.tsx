import { Badge } from "@/components/ui/badge";
import { useAdmin } from "@/lib/admin-store";

export function AppsView() {
  const env = useAdmin((s) => s.env);
  const apps = [
    { name: "Flezen", bot: env.FLEZEN_TG_BOT, url: env.FLEZEN_WEBAPP_URL },
    { name: "DiskWala", bot: env.DISKWALA_TG_BOT, url: env.DISKWALA_WEBAPP_URL },
    { name: "VidBunker", bot: env.VIDBUNKER_TG_BOT, url: env.VIDBUNKER_WEBAPP_URL },
  ];
  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <header>
        <p className="text-[11px] uppercase tracking-[0.18em] text-subtle">Mini Apps</p>
        <h1 className="mt-1 font-display text-2xl font-semibold tracking-tight">Resolver connections</h1>
      </header>
      <ul className="space-y-2">
        {apps.map((app) => (
          <li key={app.name} className="flex items-center justify-between gap-3 rounded-lg border border-border bg-surface p-4">
            <div className="min-w-0">
              <p className="font-medium">{app.name}</p>
              <p className="truncate font-mono text-xs text-muted-foreground">{app.url || "not configured"}</p>
            </div>
            <Badge tone={app.bot ? "ok" : "warn"}>{app.bot ? "configured" : "missing bot"}</Badge>
          </li>
        ))}
      </ul>
    </div>
  );
}
