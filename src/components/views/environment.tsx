import { FormEvent, useMemo, useState } from "react";
import { Eye, EyeOff, Plus, RotateCcw, Save } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { HudKicker, HudPanel } from "@/components/hud/panel";
import {
  CATEGORY_LABEL,
  ENV_CATALOG,
  maskValue,
  SENSITIVE,
  type EnvCategory,
} from "@/lib/catalog";
import { useAdmin } from "@/lib/admin-store";
import { cn } from "@/lib/utils";

const CATS: EnvCategory[] = [
  "telegram",
  "security",
  "database",
  "limits",
  "content",
  "resolvers",
  "miniapps",
  "payments",
  "delivery",
  "custom",
];

export function EnvironmentView() {
  const env = useAdmin((s) => s.env);
  const customKeys = useAdmin((s) => s.customKeys);
  const setEnv = useAdmin((s) => s.setEnv);
  const addEnv = useAdmin((s) => s.addEnv);
  const deleteEnv = useAdmin((s) => s.deleteEnv);
  const [query, setQuery] = useState("");
  const [cat, setCat] = useState<EnvCategory | "all">("all");
  const [reveal, setReveal] = useState<Record<string, boolean>>({});
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [newKey, setNewKey] = useState("");
  const [newVal, setNewVal] = useState("");

  const rows = useMemo(() => {
    const catalogRows = ENV_CATALOG.map((meta) => ({
      ...meta,
      value: env[meta.key] ?? "",
    }));
    const extra = customKeys
      .filter((key) => !ENV_CATALOG.some((item) => item.key === key))
      .map((key) => ({
        key,
        category: "custom" as const,
        type: "string" as const,
        label: key,
        description: "Custom variable stored in the environment file.",
        restart: false,
        value: env[key] ?? "",
      }));
    return [...catalogRows, ...extra].filter((row) => {
      if (cat !== "all" && row.category !== cat) return false;
      if (!query.trim()) return true;
      const hay = `${row.key} ${row.label} ${row.description}`.toLowerCase();
      return hay.includes(query.trim().toLowerCase());
    });
  }, [env, customKeys, cat, query]);

  function valueOf(key: string) {
    return draft[key] ?? env[key] ?? "";
  }

  function saveOne(key: string) {
    const value = valueOf(key);
    if (key === "BOT_TOKEN" && value && !window.confirm("Replace the bot token and reconnect?")) return;
    const result = setEnv(key, value);
    setDraft((d) => {
      const next = { ...d };
      delete next[key];
      return next;
    });
    toast.success(result.restart ? `${key} saved · restart required` : `${key} applied live`);
  }

  function saveDirty() {
    const keys = Object.keys(draft);
    if (!keys.length) {
      toast("Nothing to save");
      return;
    }
    let restart = false;
    for (const key of keys) {
      if (setEnv(key, draft[key] ?? "").restart) restart = true;
    }
    setDraft({});
    toast.success(restart ? "Saved. Some values need a process restart." : "All changes applied live.");
  }

  function onAdd(event: FormEvent) {
    event.preventDefault();
    if (!newKey.trim()) return;
    addEnv(newKey, newVal);
    setNewKey("");
    setNewVal("");
    toast.success("Variable added");
  }

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <HudKicker>Environment</HudKicker>
          <h1 className="mt-1 font-display text-2xl font-semibold">.env control</h1>
          <p className="mt-1 max-w-xl text-sm text-muted-foreground">
            View, edit, and add values. Live keys update the running bot; restart keys are written now.
          </p>
        </div>
        <Button variant="secondary" onClick={saveDirty}>
          <Save className="size-4" />
          Save edits
        </Button>
      </header>

      <div className="flex flex-col gap-3 lg:flex-row">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search keys, for example BOT_TOKEN"
          className="lg:max-w-sm"
        />
        <div className="flex gap-2 overflow-x-auto pb-1">
          <button
            onClick={() => setCat("all")}
            className={cn(
              "h-11 shrink-0 border px-3 font-display text-xs uppercase tracking-widest",
              cat === "all" ? "border-primary bg-primary text-primary-foreground" : "border-border bg-surface-2 text-muted-foreground",
            )}
          >
            All
          </button>
          {CATS.map((item) => (
            <button
              key={item}
              onClick={() => setCat(item)}
              className={cn(
                "h-11 shrink-0 border px-3 font-display text-xs uppercase tracking-widest",
                cat === item ? "border-primary bg-primary text-primary-foreground" : "border-border bg-surface-2 text-muted-foreground",
              )}
            >
              {CATEGORY_LABEL[item]}
            </button>
          ))}
        </div>
      </div>

      <ul className="space-y-3">
        {rows.map((row) => {
          const shown = reveal[row.key];
          const current = valueOf(row.key);
          const display = SENSITIVE.has(row.key) && !shown ? maskValue(row.key, current, false) : current;
          const dirty = draft[row.key] !== undefined && draft[row.key] !== env[row.key];
          return (
            <li key={row.key}>
              <HudPanel>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-display text-sm font-medium tracking-widest">{row.key}</p>
                      <Badge tone={row.restart ? "restart" : "live"}>
                        {row.restart ? "restart" : "live"}
                      </Badge>
                      {dirty ? <Badge tone="warn">unsaved</Badge> : null}
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">{row.description}</p>
                  </div>
                  <span className="hud-kicker">{CATEGORY_LABEL[row.category]}</span>
                </div>
                <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                  {row.type === "text" ? (
                    <Textarea
                      value={display}
                      onChange={(e) => setDraft((d) => ({ ...d, [row.key]: e.target.value }))}
                      className="min-h-20 flex-1"
                    />
                  ) : row.type === "boolean" ? (
                    <select
                      className="h-11 flex-1 border border-border bg-surface-2 px-3 font-display text-sm"
                      value={/^(1|true|yes|on)$/i.test(current) ? "true" : "false"}
                      onChange={(e) => setDraft((d) => ({ ...d, [row.key]: e.target.value }))}
                    >
                      <option value="true">true</option>
                      <option value="false">false</option>
                    </select>
                  ) : (
                    <Input
                      type={SENSITIVE.has(row.key) && !shown ? "password" : "text"}
                      inputMode={row.type === "number" ? "decimal" : undefined}
                      value={SENSITIVE.has(row.key) && !shown ? display : current}
                      onChange={(e) => setDraft((d) => ({ ...d, [row.key]: e.target.value }))}
                      className="flex-1"
                    />
                  )}
                  {SENSITIVE.has(row.key) ? (
                    <Button
                      type="button"
                      variant="secondary"
                      size="icon"
                      onClick={() => setReveal((r) => ({ ...r, [row.key]: !r[row.key] }))}
                      aria-label={shown ? "Hide value" : "Reveal value"}
                    >
                      {shown ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                    </Button>
                  ) : null}
                  <Button type="button" onClick={() => saveOne(row.key)}>
                    Apply
                  </Button>
                  {row.category === "custom" ? (
                    <Button type="button" variant="danger" onClick={() => deleteEnv(row.key)}>
                      Remove
                    </Button>
                  ) : null}
                </div>
              </HudPanel>
            </li>
          );
        })}
      </ul>

      <HudPanel>
        <form onSubmit={onAdd}>
          <h2 className="font-display text-base font-semibold">Add variable</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Any KEY=value pair is written to the environment file.
          </p>
          <div className="mt-4 grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
            <Input
              placeholder="NEW_KEY"
              value={newKey}
              onChange={(e) => setNewKey(e.target.value.toUpperCase())}
            />
            <Input placeholder="value" value={newVal} onChange={(e) => setNewVal(e.target.value)} />
            <Button type="submit">
              <Plus className="size-4" />
              Add
            </Button>
          </div>
        </form>
      </HudPanel>

      <p className="flex items-center gap-2 text-xs text-subtle">
        <RotateCcw className="size-3.5" />
        BOT_TOKEN, MongoDB, and Bot API URL write immediately and flag a process restart.
      </p>
    </div>
  );
}
