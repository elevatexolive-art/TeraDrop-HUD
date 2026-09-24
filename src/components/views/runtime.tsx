import { FormEvent, type ReactNode } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { HudKicker, HudPanel } from "@/components/hud/panel";
import { useAdmin } from "@/lib/admin-store";

export function RuntimeView() {
  const settings = useAdmin((s) => s.settings);
  const applySettings = useAdmin((s) => s.applySettings);
  const env = useAdmin((s) => s.env);
  const setEnv = useAdmin((s) => s.setEnv);
  const workers = useAdmin((s) => s.workers);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const limit = Number(data.get("limit") || settings.limit);
    const workersNext = Number(data.get("workers") || workers);
    applySettings({
      limit,
      maintenance: data.get("maintenance") === "on",
      botPublic: data.get("bot_public") === "true",
      welcome: String(data.get("welcome") || ""),
      caption: String(data.get("caption") || ""),
      logChannel: String(data.get("log_channel") || ""),
      dumpChannel: String(data.get("dump_channel") || ""),
    });
    setEnv("MAX_FILE_MB", String(limit));
    setEnv("MAX_CONCURRENT", String(workersNext));
    setEnv("MAINTENANCE", data.get("maintenance") === "on" ? "true" : "false");
    setEnv("BOT_PUBLIC", data.get("bot_public") === "true" ? "true" : "false");
    toast.success("Runtime settings applied without a reboot");
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <header>
        <HudKicker>Runtime</HudKicker>
        <h1 className="mt-1 font-display text-2xl font-semibold">Live flags</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          These write to Mongo KV and the in-memory settings object. No restart.
        </p>
      </header>
      <HudPanel>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Upload limit MB">
              <Input name="limit" type="number" min={1} defaultValue={settings.limit} />
            </Field>
            <Field label="Workers">
              <Input name="workers" type="number" min={1} max={64} defaultValue={workers} />
            </Field>
            <Field label="Maintenance">
              <select name="maintenance" defaultValue={settings.maintenance ? "on" : "off"} className="h-11 w-full border border-border bg-surface-2 px-3 font-display text-sm">
                <option value="off">off</option>
                <option value="on">on</option>
              </select>
            </Field>
            <Field label="Bot access">
              <select name="bot_public" defaultValue={settings.botPublic ? "true" : "false"} className="h-11 w-full border border-border bg-surface-2 px-3 font-display text-sm">
                <option value="true">public</option>
                <option value="false">authorised only</option>
              </select>
            </Field>
            <Field label="Log channel">
              <Input name="log_channel" defaultValue={settings.logChannel} />
            </Field>
            <Field label="Dump channel">
              <Input name="dump_channel" defaultValue={settings.dumpChannel} />
            </Field>
          </div>
          <Field label="Welcome text">
            <Textarea name="welcome" defaultValue={settings.welcome} />
          </Field>
          <Field label="Caption template">
            <Textarea name="caption" defaultValue={settings.caption} />
          </Field>
          <p className="font-display text-xs tracking-widest text-subtle">
            transport · {env.BOT_API_URL ? "local bot api · 2 GB" : "cloud api · 49 MB"}
          </p>
          <Button type="submit">Save runtime</Button>
        </form>
      </HudPanel>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="hud-kicker">{label}</span>
      {children}
    </label>
  );
}
