import { create } from "zustand";
import { DEFAULT_ENV, ENV_CATALOG, type EnvCategory } from "./catalog";

export type ViewId =
  | "overview"
  | "environment"
  | "runtime"
  | "plans"
  | "users"
  | "channels"
  | "apps"
  | "logs";

export interface Plan {
  key: string;
  label: string;
  short_label: string;
  price: number;
  duration_days: number;
  batch_limit: number;
  total_links: number;
  active: boolean;
}

export interface UserRow {
  user_id: number;
  name: string;
  username: string;
  downloads: number;
  plan: string;
  banned: boolean;
  seen: string;
}

export interface JobRow {
  job_id: string;
  user_id: number;
  kind: "resolve" | "transfer";
  filename: string;
  path: string;
  progress: number;
  speed: string;
}

export interface LogRow {
  id: string;
  level: "info" | "warn" | "error";
  message: string;
  at: string;
}

export interface ChannelRow {
  chat_id: string;
  invite_url: string;
}

interface AdminState {
  authed: boolean;
  view: ViewId;
  env: Record<string, string>;
  customKeys: string[];
  stats: { users: number; downloads: number; premium: number; bans: number };
  workers: number;
  queued: number;
  completed: number;
  failed: number;
  jobs: JobRow[];
  plans: Plan[];
  users: UserRow[];
  channels: ChannelRow[];
  logs: LogRow[];
  settings: {
    maintenance: boolean;
    botPublic: boolean;
    limit: number;
    welcome: string;
    caption: string;
    logChannel: string;
    dumpChannel: string;
  };
  login: (password: string) => boolean;
  logout: () => void;
  setView: (view: ViewId) => void;
  setEnv: (key: string, value: string) => { restart: boolean };
  addEnv: (key: string, value: string) => void;
  deleteEnv: (key: string) => void;
  applySettings: (patch: Partial<AdminState["settings"]>) => void;
  savePlan: (plan: Plan) => void;
  hidePlan: (key: string) => void;
  applyUserAction: (userId: number, action: "ban" | "unban" | "premium", planKey?: string) => void;
  addChannel: (chat_id: string, invite_url: string) => void;
  removeChannel: (chat_id: string) => void;
  tickJobs: () => void;
  pushLog: (level: LogRow["level"], message: string) => void;
}

const SEED_PLANS: Plan[] = [
  { key: "r", label: "Regular premium", short_label: "regular", price: 69, duration_days: 14, batch_limit: 5, total_links: 50, active: true },
  { key: "s", label: "Super premium", short_label: "super", price: 149, duration_days: 30, batch_limit: 10, total_links: 150, active: true },
  { key: "v", label: "VIP premium", short_label: "vip", price: 249, duration_days: 30, batch_limit: 20, total_links: 0, active: true },
];

const SEED_USERS: UserRow[] = [
  { user_id: 582194033, name: "Arjun", username: "arjunx", downloads: 41, plan: "v", banned: false, seen: "2m ago" },
  { user_id: 901233441, name: "Meera", username: "meerak", downloads: 12, plan: "s", banned: false, seen: "7m ago" },
  { user_id: 110293884, name: "Dev", username: "devnull", downloads: 3, plan: "free", banned: false, seen: "11m ago" },
  { user_id: 774120098, name: "Sana", username: "sana", downloads: 19, plan: "r", banned: false, seen: "18m ago" },
  { user_id: 330192774, name: "Kabir", username: "kabir", downloads: 0, plan: "free", banned: true, seen: "1h ago" },
  { user_id: 448201993, name: "Nisha", username: "nisha", downloads: 8, plan: "free", banned: false, seen: "2h ago" },
];

const SEED_JOBS: JobRow[] = [
  { job_id: "a91c", user_id: 582194033, kind: "transfer", filename: "episode-04.mp4", path: "/data/tmp/u582194033/a91c2e10/4f21_episode-04.mp4", progress: 62, speed: "18.4 MB/s" },
  { job_id: "b33f", user_id: 901233441, kind: "transfer", filename: "lecture.mkv", path: "/data/tmp/u901233441/b33f90aa/91c0_lecture.mkv", progress: 28, speed: "11.1 MB/s" },
  { job_id: "c10e", user_id: 110293884, kind: "resolve", filename: "terabox link", path: "isolated resolve slot", progress: 80, speed: "—" },
];

const SEED_LOGS: LogRow[] = [
  { id: "1", level: "info", message: "worker resize applied · MAX_CONCURRENT=8", at: "12:41:02" },
  { id: "2", level: "info", message: "transfer complete · user 582194033 · 842 MB isolated path cleaned", at: "12:38:44" },
  { id: "3", level: "warn", message: "queue rejected free user 330192774 · already in flight", at: "12:36:11" },
  { id: "4", level: "info", message: "welcome text updated from control center", at: "12:22:09" },
  { id: "5", level: "error", message: "resolver timeout on upfiles · retried and recovered", at: "12:18:57" },
];

export const useAdmin = create<AdminState>()((set, get) => ({
      authed: false,
      view: "overview",
      env: { ...DEFAULT_ENV },
      customKeys: [],
      stats: { users: 1284, downloads: 8432, premium: 96, bans: 7 },
      workers: 8,
      queued: 3,
      completed: 8411,
      failed: 14,
      jobs: SEED_JOBS,
      plans: SEED_PLANS,
      users: SEED_USERS,
      channels: [
        { chat_id: "@teradrop_updates", invite_url: "https://t.me/teradrop_updates" },
      ],
      logs: SEED_LOGS,
      settings: {
        maintenance: false,
        botPublic: true,
        limit: 2000,
        welcome: DEFAULT_ENV.WELCOME_TEXT,
        caption: DEFAULT_ENV.CAPTION_TEMPLATE,
        logChannel: DEFAULT_ENV.LOG_CHANNEL,
        dumpChannel: DEFAULT_ENV.DUMP_CHANNEL,
      },
      login: (password) => {
        const expected = get().env.ADMIN_PANEL_PASSWORD || "teradrop";
        if (password.trim() !== expected) return false;
        set({ authed: true });
        return true;
      },
      logout: () => set({ authed: false, view: "overview" }),
      setView: (view) => set({ view }),
      setEnv: (key, value) => {
        const meta = ENV_CATALOG.find((item) => item.key === key);
        set((state) => ({ env: { ...state.env, [key]: value } }));
        if (key === "MAX_CONCURRENT") {
          const n = Math.max(1, Math.min(64, Number(value) || 1));
          set({ workers: n });
        }
        if (key === "MAINTENANCE") {
          set((s) => ({ settings: { ...s.settings, maintenance: /^(1|true|yes|on)$/i.test(value) } }));
        }
        if (key === "BOT_PUBLIC") {
          set((s) => ({ settings: { ...s.settings, botPublic: /^(1|true|yes|on)$/i.test(value) } }));
        }
        if (key === "WELCOME_TEXT") set((s) => ({ settings: { ...s.settings, welcome: value } }));
        if (key === "CAPTION_TEMPLATE") set((s) => ({ settings: { ...s.settings, caption: value } }));
        if (key === "MAX_FILE_MB") set((s) => ({ settings: { ...s.settings, limit: Number(value) || s.settings.limit } }));
        get().pushLog("info", `${key} updated · ${meta?.restart ? "restart required" : "applied live"}`);
        return { restart: Boolean(meta?.restart) };
      },
      addEnv: (key, value) => {
        const clean = key.trim().toUpperCase().replace(/[^A-Z0-9_]/g, "_");
        if (!clean) return;
        set((state) => ({
          env: { ...state.env, [clean]: value },
          customKeys: state.customKeys.includes(clean) ? state.customKeys : [...state.customKeys, clean],
        }));
        get().pushLog("info", `custom variable ${clean} added`);
      },
      deleteEnv: (key) => {
        set((state) => {
          const env = { ...state.env };
          delete env[key];
          return { env, customKeys: state.customKeys.filter((item) => item !== key) };
        });
        get().pushLog("warn", `${key} removed from environment`);
      },
      applySettings: (patch) => {
        set((state) => ({ settings: { ...state.settings, ...patch } }));
        get().pushLog("info", "runtime settings saved · applied live");
      },
      savePlan: (plan) => {
        set((state) => {
          const exists = state.plans.some((item) => item.key === plan.key);
          return {
            plans: exists
              ? state.plans.map((item) => (item.key === plan.key ? plan : item))
              : [...state.plans, plan],
          };
        });
        get().pushLog("info", `plan ${plan.key} saved`);
      },
      hidePlan: (key) => {
        set((state) => ({
          plans: state.plans.map((item) => (item.key === key ? { ...item, active: false } : item)),
        }));
        get().pushLog("warn", `plan ${key} hidden from new purchases`);
      },
      applyUserAction: (userId, action, planKey) => {
        set((state) => ({
          users: state.users.map((user) => {
            if (user.user_id !== userId) return user;
            if (action === "ban") return { ...user, banned: true };
            if (action === "unban") return { ...user, banned: false };
            return { ...user, plan: planKey || "r" };
          }),
        }));
        get().pushLog("info", `user ${userId} · ${action}${planKey ? ` ${planKey}` : ""}`);
      },
      addChannel: (chat_id, invite_url) => {
        set((state) => ({
          channels: [
            ...state.channels.filter((item) => item.chat_id !== chat_id),
            { chat_id, invite_url: invite_url || `https://t.me/${chat_id.replace(/^@/, "")}` },
          ],
        }));
      },
      removeChannel: (chat_id) => {
        set((state) => ({ channels: state.channels.filter((item) => item.chat_id !== chat_id) }));
      },
      tickJobs: () => {
        set((state) => ({
          jobs: state.jobs.map((job) => {
            if (job.kind === "resolve") {
              const progress = Math.min(100, job.progress + 4);
              return { ...job, progress };
            }
            const bump = 1.5 + Math.random() * 3.5;
            return { ...job, progress: Math.min(100, job.progress + bump) };
          }),
        }));
      },
      pushLog: (level, message) => {
        const at = new Date().toLocaleTimeString("en-GB", { hour12: false });
        set((state) => ({
          logs: [{ id: `${Date.now()}`, level, message, at }, ...state.logs].slice(0, 40),
        }));
      },
}));

export function categoryOf(key: string): EnvCategory {
  return ENV_CATALOG.find((item) => item.key === key)?.category ?? "custom";
}
