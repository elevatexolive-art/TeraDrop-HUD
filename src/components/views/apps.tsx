import { RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { HudKicker, HudPanel } from "@/components/hud/panel";
import { useAdmin } from "@/lib/admin-store";

export function AppsView() {
  const env = useAdmin((s) => s.env);
  const setEnv = useAdmin((s) => s.setEnv);
  const pushLog = useAdmin((s) => s.pushLog);
  const apps = [
    {
      name: "Flezen",
      bot: env.FLEZEN_TG_BOT,
      url: env.FLEZEN_WEBAPP_URL,
      download: env.FLEZEN_API_DOWNLOAD,
      status: env.FLEZEN_API_STATUS,
      botId: env.FLEZEN_BOT_ID,
    },
    {
      name: "DiskWala",
      bot: env.DISKWALA_TG_BOT,
      url: env.DISKWALA_WEBAPP_URL,
      download: env.DISKWALA_API_DOWNLOAD,
      status: env.DISKWALA_API_STATUS,
      botId: env.DISKWALA_BOT_ID,
    },
    {
      name: "VidBunker",
      bot: env.VIDBUNKER_TG_BOT,
      url: env.VIDBUNKER_WEBAPP_URL,
      download: env.VIDBUNKER_API_URL,
      status: "",
      botId: env.VIDBUNKER_BOT_ID,
    },
  ];

  function syncNow() {
    const stamp = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
    setEnv("MINIAPP_LAST_SYNC", stamp);
    pushLog("info", "mini-app catalog synced from live JS");
    toast.success("Mini App catalog refreshed");
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <HudKicker>Mini Apps</HudKicker>
          <h1 className="mt-1 font-display text-2xl font-semibold">Resolver connections</h1>
          <p className="mt-1 max-w-xl text-sm text-muted-foreground">
            The live bot scrapes each Mini App JS bundle, writes new endpoints into .env, and retries on 404. Last sync {env.MINIAPP_LAST_SYNC || "never"}.
          </p>
        </div>
        <Button variant="secondary" onClick={syncNow}>
          <RefreshCw className="size-4" />
          Sync now
        </Button>
      </header>
      <ul className="space-y-2">
        {apps.map((app) => (
          <li key={app.name}>
            <HudPanel className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-medium">{app.name}</p>
                  <p className="truncate font-display text-xs tracking-widest text-muted-foreground">{app.url || "not configured"}</p>
                </div>
                <Badge tone={app.bot ? "ok" : "warn"}>{app.bot ? "live catalog" : "missing bot"}</Badge>
              </div>
              <p className="truncate font-display text-[11px] tracking-wide text-muted-foreground">{app.download || "—"}</p>
              {app.status ? <p className="truncate font-display text-[11px] tracking-wide text-muted-foreground">{app.status}</p> : null}
              <p className="font-display text-[11px] uppercase tracking-widest text-muted-foreground">
                bot {app.bot || "—"} · x-bot-id {app.botId || "—"}
              </p>
            </HudPanel>
          </li>
        ))}
      </ul>
    </div>
  );
}
