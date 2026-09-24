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
import { HudClock } from "@/components/hud/telemetry";
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
  const live = jobs.filter((j) => j.progress < 100).length;

  useEffect(() => {
    const id = window.setInterval(tickJobs, 900);
    return () => window.clearInterval(id);
  }, [tickJobs]);

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[220px_1fr]">
      <aside className="hidden border-r border-border/70 lg:flex lg:flex-col lg:px-3 lg:py-6">
        <div className="px-3">
          <p className="font-display text-lg font-semibold tracking-[0.22em]">TERADROP</p>
          <p className="mt-1 hud-kicker text-primary">Control HUD</p>
        </div>
        <nav className="mt-8 flex flex-1 flex-col gap-1">
          {NAV.map((item) => {
            const Icon = item.icon;
            const active = view === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setView(item.id)}
                data-active={active}
                className={cn(
                  "hud-nav-btn flex h-11 items-center gap-3 px-3 text-sm tracking-wide transition-colors duration-[var(--motion-quick)]",
                  active
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-surface-2 hover:text-foreground",
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
          className="mt-4 flex h-11 items-center gap-3 px-3 text-sm text-muted-foreground hover:bg-surface-2 hover:text-foreground"
        >
          <LogOut className="size-4" />
          Log out
        </button>
      </aside>

      <div className="flex min-w-0 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-border/70 px-4 py-3 sm:px-6">
          <div className="min-w-0">
            <p className="truncate font-display text-base font-semibold tracking-[0.18em]">
              {env.BOT_NAME || "TeraDrop"}
            </p>
            <p className="truncate font-display text-xs tracking-widest text-muted-foreground">
              @{env.BOT_USERNAME || "TeraDropBot"}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <HudClock />
            <span className="hidden font-display text-xs tracking-widest text-muted-foreground sm:inline">
              {live} lanes
            </span>
            <span className={cn("hud-live font-display text-xs tracking-[0.2em] uppercase", maintenance ? "text-warn" : "text-ok")}>
              {maintenance ? "hold" : "live"}
            </span>
          </div>
        </header>

        <main className="flex-1 px-4 py-5 pb-24 sm:px-6 lg:pb-8">
          <div key={view} className="hud-enter">
            {view === "overview" && <OverviewView />}
            {view === "environment" && <EnvironmentView />}
            {view === "runtime" && <RuntimeView />}
            {view === "plans" && <PlansView />}
            {view === "users" && <UsersView />}
            {view === "channels" && <ChannelsView />}
            {view === "apps" && <AppsView />}
            {view === "logs" && <LogsView />}
          </div>
        </main>
      </div>

      <nav className="fixed inset-x-0 bottom-0 z-20 flex gap-1 overflow-x-auto border-t border-border/70 bg-bg/80 px-2 py-2 backdrop-blur-md lg:hidden">
        {NAV.map((item) => {
          const Icon = item.icon;
          const active = view === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setView(item.id)}
              className={cn(
                "flex h-11 min-w-16 shrink-0 flex-col items-center justify-center gap-0.5 px-2 text-[0.65rem] tracking-wider uppercase",
                active ? "text-primary" : "text-muted-foreground",
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
