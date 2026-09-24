import { useEffect } from "react";
import {
  Activity,
  Boxes,
  KeyRound,
  LayoutDashboard,
  ListTree,
  LogOut,
  Radio,
  SlidersHorizontal,
  Users,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAdmin, type ViewId } from "@/lib/admin-store";
import { OverviewView } from "@/components/views/overview";
import { EnvironmentView } from "@/components/views/environment";
import { RuntimeView } from "@/components/views/runtime";
import { PlansView } from "@/components/views/plans";
import { UsersView } from "@/components/views/users";
import { ChannelsView } from "@/components/views/channels";
import { AppsView } from "@/components/views/apps";
import { LogsView } from "@/components/views/logs";

const NAV: { id: ViewId; label: string; icon: typeof LayoutDashboard }[] = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "environment", label: "Environment", icon: KeyRound },
  { id: "runtime", label: "Runtime", icon: SlidersHorizontal },
  { id: "plans", label: "Plans", icon: Boxes },
  { id: "users", label: "Users", icon: Users },
  { id: "channels", label: "Channels", icon: Radio },
  { id: "apps", label: "Mini Apps", icon: Activity },
  { id: "logs", label: "Logs", icon: ListTree },
];

export function AppShell() {
  const view = useAdmin((s) => s.view);
  const setView = useAdmin((s) => s.setView);
  const logout = useAdmin((s) => s.logout);
  const env = useAdmin((s) => s.env);
  const jobs = useAdmin((s) => s.jobs);
  const tickJobs = useAdmin((s) => s.tickJobs);
  const maintenance = useAdmin((s) => s.settings.maintenance);

  useEffect(() => {
    const id = window.setInterval(tickJobs, 900);
    return () => window.clearInterval(id);
  }, [tickJobs]);

  return (
    <div className="min-h-dvh bg-bg lg:grid lg:grid-cols-[240px_1fr]">
      <aside className="hidden border-r border-border lg:flex lg:flex-col lg:px-4 lg:py-6">
        <div className="px-3">
          <p className="font-display text-lg font-semibold tracking-tight">TeraDrop</p>
          <p className="mt-0.5 text-[11px] uppercase tracking-[0.18em] text-subtle">Control center</p>
        </div>
        <nav className="mt-8 flex flex-1 flex-col gap-1">
          {NAV.map((item) => {
            const Icon = item.icon;
            const active = view === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setView(item.id)}
                className={cn(
                  "flex h-11 items-center gap-3 rounded-md px-3 text-sm transition-colors duration-[var(--motion-quick)]",
                  active
                    ? "bg-surface-2 text-foreground"
                    : "text-muted-foreground hover:bg-surface hover:text-foreground",
                )}
              >
                <Icon className="size-4" />
                {item.label}
              </button>
            );
          })}
        </nav>
        <button
          onClick={logout}
          className="mt-4 flex h-11 items-center gap-3 rounded-md px-3 text-sm text-muted-foreground hover:bg-surface hover:text-foreground"
        >
          <LogOut className="size-4" />
          Log out
        </button>
      </aside>

      <div className="flex min-w-0 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-3 sm:px-6">
          <div className="min-w-0">
            <p className="truncate font-display text-base font-semibold">{env.BOT_NAME || "TeraDrop"}</p>
            <p className="truncate font-mono text-xs text-muted-foreground">@{env.BOT_USERNAME || "TeraDropBot"}</p>
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden rounded-full border border-border px-3 py-1 font-mono text-[11px] text-muted-foreground sm:inline">
              {jobs.filter((j) => j.progress < 100).length} live lanes
            </span>
            <span
              className={cn(
                "rounded-full px-3 py-1 text-[11px] font-medium",
                maintenance ? "bg-warn/15 text-warn" : "bg-ok/15 text-ok",
              )}
            >
              {maintenance ? "maintenance" : "live"}
            </span>
          </div>
        </header>

        <main className="flex-1 px-4 py-5 pb-24 sm:px-6 lg:pb-8">
          {view === "overview" && <OverviewView />}
          {view === "environment" && <EnvironmentView />}
          {view === "runtime" && <RuntimeView />}
          {view === "plans" && <PlansView />}
          {view === "users" && <UsersView />}
          {view === "channels" && <ChannelsView />}
          {view === "apps" && <AppsView />}
          {view === "logs" && <LogsView />}
        </main>
      </div>

      <nav className="fixed inset-x-0 bottom-0 z-20 flex gap-1 overflow-x-auto border-t border-border bg-bg/95 px-2 py-2 backdrop-blur lg:hidden">
        {NAV.map((item) => {
          const Icon = item.icon;
          const active = view === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setView(item.id)}
              className={cn(
                "flex h-11 min-w-16 shrink-0 flex-col items-center justify-center gap-0.5 rounded-md px-2 text-[10px]",
                active ? "text-foreground" : "text-muted-foreground",
              )}
            >
              <Icon className="size-4" />
              {item.label}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
