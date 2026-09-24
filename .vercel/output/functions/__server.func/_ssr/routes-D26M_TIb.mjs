import { i as __toESM } from "../_runtime.mjs";
import { R as require_react, y as require_jsx_runtime } from "../_libs/@tanstack/react-router+[...].mjs";
import { a as RotateCcw, c as LogOut, d as KeyRound, f as Eye, h as Activity, i as Save, l as ListTree, m as Boxes, o as Radio, p as EyeOff, r as SlidersHorizontal, s as Plus, t as Users, u as LayoutDashboard } from "../_libs/lucide-react.mjs";
import { n as toast } from "../_libs/sonner.mjs";
import { n as clsx, t as cva } from "../_libs/class-variance-authority+clsx.mjs";
import { t as twMerge } from "../_libs/tailwind-merge.mjs";
import { t as create } from "../_libs/zustand.mjs";
import { a as Tooltip, i as ResponsiveContainer, n as XAxis, r as Area, t as AreaChart } from "../_libs/recharts+[...].mjs";
//#region node_modules/.nitro/vite/services/ssr/assets/routes-D26M_TIb.js
var import_react = /* @__PURE__ */ __toESM(require_react());
var import_jsx_runtime = require_jsx_runtime();
function cn(...inputs) {
	return twMerge(clsx(inputs));
}
var CATEGORY_LABEL = {
	telegram: "Telegram",
	security: "Security",
	database: "Database",
	limits: "Limits & queue",
	content: "Copy",
	resolvers: "Resolvers",
	miniapps: "Mini Apps",
	payments: "Payments",
	delivery: "Delivery",
	custom: "Custom"
};
var ENV_CATALOG = [
	{
		key: "BOT_TOKEN",
		category: "telegram",
		type: "secret",
		label: "Bot token",
		description: "Token from BotFather. Changing it reconnects the bot.",
		restart: true
	},
	{
		key: "BOT_NAME",
		category: "telegram",
		type: "string",
		label: "Bot name",
		description: "Display name used in messages and the control center.",
		restart: false
	},
	{
		key: "BOT_USERNAME",
		category: "telegram",
		type: "string",
		label: "Bot username",
		description: "Public @username without the @.",
		restart: false
	},
	{
		key: "OWNER_IDS",
		category: "telegram",
		type: "string",
		label: "Owner IDs",
		description: "Comma-separated Telegram user IDs with full control.",
		restart: false
	},
	{
		key: "AUTHORIZED_IDS",
		category: "telegram",
		type: "string",
		label: "Authorized IDs",
		description: "Allow-list used when the bot is private.",
		restart: false
	},
	{
		key: "BOT_PUBLIC",
		category: "telegram",
		type: "boolean",
		label: "Public access",
		description: "Anyone can use the bot when enabled.",
		restart: false
	},
	{
		key: "BOT_API_URL",
		category: "telegram",
		type: "string",
		label: "Local Bot API URL",
		description: "Local Bot API root for uploads up to 2 GB.",
		restart: true
	},
	{
		key: "TELEGRAM_API_ID",
		category: "telegram",
		type: "number",
		label: "Telegram API ID",
		description: "From my.telegram.org, required for Mini App login.",
		restart: true
	},
	{
		key: "TELEGRAM_API_HASH",
		category: "telegram",
		type: "secret",
		label: "Telegram API hash",
		description: "From my.telegram.org, required for Mini App login.",
		restart: true
	},
	{
		key: "LOG_CHANNEL",
		category: "telegram",
		type: "string",
		label: "Log channel",
		description: "Channel or chat ID for operational logs.",
		restart: false
	},
	{
		key: "DUMP_CHANNEL",
		category: "telegram",
		type: "string",
		label: "Dump channel",
		description: "Channel or chat ID for payment notices.",
		restart: false
	},
	{
		key: "ADMIN_PANEL_PASSWORD",
		category: "security",
		type: "secret",
		label: "Admin password",
		description: "Password for this control center. Applied immediately.",
		restart: false
	},
	{
		key: "SESSION_SECRET",
		category: "security",
		type: "secret",
		label: "Session secret",
		description: "Encrypts Telethon Mini App sessions.",
		restart: true
	},
	{
		key: "MONGODB_URI",
		category: "database",
		type: "secret",
		label: "MongoDB URI",
		description: "Connection string. Requires a process restart.",
		restart: true
	},
	{
		key: "MONGODB_DATABASE",
		category: "database",
		type: "string",
		label: "MongoDB database",
		description: "Database name. Requires a process restart.",
		restart: true
	},
	{
		key: "MAINTENANCE",
		category: "limits",
		type: "boolean",
		label: "Maintenance mode",
		description: "Pause public processing without stopping the bot.",
		restart: false
	},
	{
		key: "MAX_FILE_MB",
		category: "limits",
		type: "number",
		label: "Max send size (MB)",
		description: "Owner cap for send-to-chat.",
		restart: false
	},
	{
		key: "MAX_CONCURRENT",
		category: "limits",
		type: "number",
		label: "Worker count",
		description: "Download/upload workers. Applied live.",
		restart: false
	},
	{
		key: "MAX_QUEUE_SIZE",
		category: "limits",
		type: "number",
		label: "Queue size",
		description: "Maximum waiting jobs before new requests are rejected.",
		restart: false
	},
	{
		key: "FREE_LINKS_PER_24H",
		category: "limits",
		type: "number",
		label: "Free links / 24h",
		description: "Rolling free-tier link budget.",
		restart: false
	},
	{
		key: "FREE_SEND_FILE_LIFETIME",
		category: "limits",
		type: "number",
		label: "Free send-file credits",
		description: "Lifetime send-to-Telegram credits for free users.",
		restart: false
	},
	{
		key: "AUTO_DELETE_MINUTES",
		category: "limits",
		type: "number",
		label: "Auto-delete (minutes)",
		description: "How long sent files remain in chat.",
		restart: false
	},
	{
		key: "WELCOME_TEXT",
		category: "content",
		type: "text",
		label: "Welcome text",
		description: "Override for the /start message.",
		restart: false
	},
	{
		key: "CAPTION_TEMPLATE",
		category: "content",
		type: "text",
		label: "Caption template",
		description: "Supports {filename}, {size}, {url}.",
		restart: false
	},
	{
		key: "TERABOXDL_URL",
		category: "resolvers",
		type: "string",
		label: "TeraBox resolver",
		description: "Primary TeraBox resolver host.",
		restart: false
	},
	{
		key: "SOLVER_URL",
		category: "resolvers",
		type: "string",
		label: "Turnstile solver",
		description: "Cloudflare Turnstile solver endpoint.",
		restart: false
	},
	{
		key: "UPFILES_SOLVER_URL",
		category: "resolvers",
		type: "string",
		label: "UpFiles solver",
		description: "Solver used for UpFiles.",
		restart: false
	},
	{
		key: "FLEZEN_TG_BOT",
		category: "miniapps",
		type: "string",
		label: "Flezen bot",
		description: "Username of the Flezen Mini App bot.",
		restart: false
	},
	{
		key: "FLEZEN_WEBAPP_URL",
		category: "miniapps",
		type: "string",
		label: "Flezen WebApp URL",
		description: "Flezen Mini App URL.",
		restart: false
	},
	{
		key: "DISKWALA_TG_BOT",
		category: "miniapps",
		type: "string",
		label: "DiskWala bot",
		description: "Username of the DiskWala Mini App bot.",
		restart: false
	},
	{
		key: "DISKWALA_WEBAPP_URL",
		category: "miniapps",
		type: "string",
		label: "DiskWala WebApp URL",
		description: "DiskWala Mini App URL.",
		restart: false
	},
	{
		key: "VIDBUNKER_TG_BOT",
		category: "miniapps",
		type: "string",
		label: "VidBunker bot",
		description: "Username of the VidBunker Mini App bot.",
		restart: false
	},
	{
		key: "VIDBUNKER_WEBAPP_URL",
		category: "miniapps",
		type: "string",
		label: "VidBunker WebApp URL",
		description: "VidBunker Mini App URL.",
		restart: false
	},
	{
		key: "PAYTM_MID",
		category: "payments",
		type: "secret",
		label: "Paytm MID",
		description: "Paytm merchant ID used by the payment proxy.",
		restart: false
	},
	{
		key: "UPI_ID",
		category: "payments",
		type: "secret",
		label: "UPI ID",
		description: "UPI address printed on premium QR codes.",
		restart: false
	},
	{
		key: "UPI_PAYEE_NAME",
		category: "payments",
		type: "string",
		label: "UPI payee name",
		description: "Name shown in the UPI collect request.",
		restart: false
	},
	{
		key: "PAYMENT_API_URL",
		category: "payments",
		type: "string",
		label: "Payment API",
		description: "Paytm verification proxy URL.",
		restart: false
	},
	{
		key: "PUBLIC_BASE_URL",
		category: "delivery",
		type: "string",
		label: "Public base URL",
		description: "HTTPS origin used to hide stream/direct links.",
		restart: false
	},
	{
		key: "PUBLIC_HOST",
		category: "delivery",
		type: "string",
		label: "Public host",
		description: "Hostname or IP in front of Caddy.",
		restart: false
	},
	{
		key: "PUBLIC_PORT",
		category: "delivery",
		type: "string",
		label: "Public port",
		description: "Public HTTPS port, default 6969.",
		restart: false
	},
	{
		key: "DOWNLOAD_DIR",
		category: "delivery",
		type: "string",
		label: "Download directory",
		description: "Scratch directory. Per-user folders are created automatically.",
		restart: true
	},
	{
		key: "HEALTH_PORT",
		category: "delivery",
		type: "number",
		label: "Health/admin port",
		description: "Internal port for /admin, /media and health checks.",
		restart: true
	}
];
var SENSITIVE = new Set(ENV_CATALOG.filter((item) => item.type === "secret").map((item) => item.key));
function maskValue(key, value, reveal) {
	if (reveal || !SENSITIVE.has(key) || !value) return value;
	if (value.length <= 4) return "••••";
	return `••••••••${value.slice(-4)}`;
}
var DEFAULT_ENV = {
	BOT_TOKEN: "1234567890:AAExampleTokenNotReal",
	BOT_NAME: "TeraDrop",
	BOT_USERNAME: "TeraDropBot",
	OWNER_IDS: "123456789",
	AUTHORIZED_IDS: "",
	BOT_PUBLIC: "true",
	BOT_API_URL: "http://telegram-bot-api:8081",
	TELEGRAM_API_ID: "12345678",
	TELEGRAM_API_HASH: "abcdef0123456789abcdef0123456789",
	LOG_CHANNEL: "-1001234567890",
	DUMP_CHANNEL: "-1001987654321",
	ADMIN_PANEL_PASSWORD: "teradrop",
	SESSION_SECRET: "replace-with-a-long-random-secret",
	MONGODB_URI: "mongodb://user:pass@mongo:27017",
	MONGODB_DATABASE: "downloader_bot",
	MAINTENANCE: "false",
	MAX_FILE_MB: "2000",
	MAX_CONCURRENT: "8",
	MAX_QUEUE_SIZE: "1000",
	FREE_LINKS_PER_24H: "5",
	FREE_SEND_FILE_LIFETIME: "5",
	AUTO_DELETE_MINUTES: "45",
	WELCOME_TEXT: "Send a Flezen, DiskWala, VidBunker, TeraBox or UpFiles link.",
	CAPTION_TEMPLATE: "{filename}\n{size}",
	TERABOXDL_URL: "https://www.teraboxdl.site",
	SOLVER_URL: "http://solver:42271",
	UPFILES_SOLVER_URL: "http://solver:42271",
	FLEZEN_TG_BOT: "flezenbot",
	FLEZEN_WEBAPP_URL: "https://flezen-downloader.pages.dev/",
	DISKWALA_TG_BOT: "diskwalabot",
	DISKWALA_WEBAPP_URL: "https://miniapp.diskwala.net/",
	VIDBUNKER_TG_BOT: "vidbunkerbot",
	VIDBUNKER_WEBAPP_URL: "https://vidbunker-ma.pages.dev/",
	PAYTM_MID: "MIDXXXXXXXXXXXXXX",
	UPI_ID: "merchant@upi",
	UPI_PAYEE_NAME: "TeraDrop Premium",
	PAYMENT_API_URL: "https://paytm-example.example/",
	PUBLIC_BASE_URL: "https://drop.example:6969",
	PUBLIC_HOST: "drop.example",
	PUBLIC_PORT: "6969",
	DOWNLOAD_DIR: "/app/data/tmp",
	HEALTH_PORT: "8080"
};
var SEED_PLANS = [
	{
		key: "r",
		label: "Regular premium",
		short_label: "regular",
		price: 69,
		duration_days: 14,
		batch_limit: 5,
		total_links: 50,
		active: true
	},
	{
		key: "s",
		label: "Super premium",
		short_label: "super",
		price: 149,
		duration_days: 30,
		batch_limit: 10,
		total_links: 150,
		active: true
	},
	{
		key: "v",
		label: "VIP premium",
		short_label: "vip",
		price: 249,
		duration_days: 30,
		batch_limit: 20,
		total_links: 0,
		active: true
	}
];
var SEED_USERS = [
	{
		user_id: 582194033,
		name: "Arjun",
		username: "arjunx",
		downloads: 41,
		plan: "v",
		banned: false,
		seen: "2m ago"
	},
	{
		user_id: 901233441,
		name: "Meera",
		username: "meerak",
		downloads: 12,
		plan: "s",
		banned: false,
		seen: "7m ago"
	},
	{
		user_id: 110293884,
		name: "Dev",
		username: "devnull",
		downloads: 3,
		plan: "free",
		banned: false,
		seen: "11m ago"
	},
	{
		user_id: 774120098,
		name: "Sana",
		username: "sana",
		downloads: 19,
		plan: "r",
		banned: false,
		seen: "18m ago"
	},
	{
		user_id: 330192774,
		name: "Kabir",
		username: "kabir",
		downloads: 0,
		plan: "free",
		banned: true,
		seen: "1h ago"
	},
	{
		user_id: 448201993,
		name: "Nisha",
		username: "nisha",
		downloads: 8,
		plan: "free",
		banned: false,
		seen: "2h ago"
	}
];
var SEED_JOBS = [
	{
		job_id: "a91c",
		user_id: 582194033,
		kind: "transfer",
		filename: "episode-04.mp4",
		path: "/data/tmp/u582194033/a91c2e10/4f21_episode-04.mp4",
		progress: 62,
		speed: "18.4 MB/s"
	},
	{
		job_id: "b33f",
		user_id: 901233441,
		kind: "transfer",
		filename: "lecture.mkv",
		path: "/data/tmp/u901233441/b33f90aa/91c0_lecture.mkv",
		progress: 28,
		speed: "11.1 MB/s"
	},
	{
		job_id: "c10e",
		user_id: 110293884,
		kind: "resolve",
		filename: "terabox link",
		path: "isolated resolve slot",
		progress: 80,
		speed: "—"
	}
];
var SEED_LOGS = [
	{
		id: "1",
		level: "info",
		message: "worker resize applied · MAX_CONCURRENT=8",
		at: "12:41:02"
	},
	{
		id: "2",
		level: "info",
		message: "transfer complete · user 582194033 · 842 MB isolated path cleaned",
		at: "12:38:44"
	},
	{
		id: "3",
		level: "warn",
		message: "queue rejected free user 330192774 · already in flight",
		at: "12:36:11"
	},
	{
		id: "4",
		level: "info",
		message: "welcome text updated from control center",
		at: "12:22:09"
	},
	{
		id: "5",
		level: "error",
		message: "resolver timeout on upfiles · retried and recovered",
		at: "12:18:57"
	}
];
var useAdmin = create()((set, get) => ({
	authed: false,
	view: "overview",
	env: { ...DEFAULT_ENV },
	customKeys: [],
	stats: {
		users: 1284,
		downloads: 8432,
		premium: 96,
		bans: 7
	},
	workers: 8,
	queued: 3,
	completed: 8411,
	failed: 14,
	jobs: SEED_JOBS,
	plans: SEED_PLANS,
	users: SEED_USERS,
	channels: [{
		chat_id: "@teradrop_updates",
		invite_url: "https://t.me/teradrop_updates"
	}],
	logs: SEED_LOGS,
	settings: {
		maintenance: false,
		botPublic: true,
		limit: 2e3,
		welcome: DEFAULT_ENV.WELCOME_TEXT,
		caption: DEFAULT_ENV.CAPTION_TEMPLATE,
		logChannel: DEFAULT_ENV.LOG_CHANNEL,
		dumpChannel: DEFAULT_ENV.DUMP_CHANNEL
	},
	login: (password) => {
		const expected = get().env.ADMIN_PANEL_PASSWORD || "teradrop";
		if (password.trim() !== expected) return false;
		set({ authed: true });
		return true;
	},
	logout: () => set({
		authed: false,
		view: "overview"
	}),
	setView: (view) => set({ view }),
	setEnv: (key, value) => {
		const meta = ENV_CATALOG.find((item) => item.key === key);
		set((state) => ({ env: {
			...state.env,
			[key]: value
		} }));
		if (key === "MAX_CONCURRENT") set({ workers: Math.max(1, Math.min(64, Number(value) || 1)) });
		if (key === "MAINTENANCE") set((s) => ({ settings: {
			...s.settings,
			maintenance: /^(1|true|yes|on)$/i.test(value)
		} }));
		if (key === "BOT_PUBLIC") set((s) => ({ settings: {
			...s.settings,
			botPublic: /^(1|true|yes|on)$/i.test(value)
		} }));
		if (key === "WELCOME_TEXT") set((s) => ({ settings: {
			...s.settings,
			welcome: value
		} }));
		if (key === "CAPTION_TEMPLATE") set((s) => ({ settings: {
			...s.settings,
			caption: value
		} }));
		if (key === "MAX_FILE_MB") set((s) => ({ settings: {
			...s.settings,
			limit: Number(value) || s.settings.limit
		} }));
		get().pushLog("info", `${key} updated · ${meta?.restart ? "restart required" : "applied live"}`);
		return { restart: Boolean(meta?.restart) };
	},
	addEnv: (key, value) => {
		const clean = key.trim().toUpperCase().replace(/[^A-Z0-9_]/g, "_");
		if (!clean) return;
		set((state) => ({
			env: {
				...state.env,
				[clean]: value
			},
			customKeys: state.customKeys.includes(clean) ? state.customKeys : [...state.customKeys, clean]
		}));
		get().pushLog("info", `custom variable ${clean} added`);
	},
	deleteEnv: (key) => {
		set((state) => {
			const env = { ...state.env };
			delete env[key];
			return {
				env,
				customKeys: state.customKeys.filter((item) => item !== key)
			};
		});
		get().pushLog("warn", `${key} removed from environment`);
	},
	applySettings: (patch) => {
		set((state) => ({ settings: {
			...state.settings,
			...patch
		} }));
		get().pushLog("info", "runtime settings saved · applied live");
	},
	savePlan: (plan) => {
		set((state) => {
			return { plans: state.plans.some((item) => item.key === plan.key) ? state.plans.map((item) => item.key === plan.key ? plan : item) : [...state.plans, plan] };
		});
		get().pushLog("info", `plan ${plan.key} saved`);
	},
	hidePlan: (key) => {
		set((state) => ({ plans: state.plans.map((item) => item.key === key ? {
			...item,
			active: false
		} : item) }));
		get().pushLog("warn", `plan ${key} hidden from new purchases`);
	},
	applyUserAction: (userId, action, planKey) => {
		set((state) => ({ users: state.users.map((user) => {
			if (user.user_id !== userId) return user;
			if (action === "ban") return {
				...user,
				banned: true
			};
			if (action === "unban") return {
				...user,
				banned: false
			};
			return {
				...user,
				plan: planKey || "r"
			};
		}) }));
		get().pushLog("info", `user ${userId} · ${action}${planKey ? ` ${planKey}` : ""}`);
	},
	addChannel: (chat_id, invite_url) => {
		set((state) => ({ channels: [...state.channels.filter((item) => item.chat_id !== chat_id), {
			chat_id,
			invite_url: invite_url || `https://t.me/${chat_id.replace(/^@/, "")}`
		}] }));
	},
	removeChannel: (chat_id) => {
		set((state) => ({ channels: state.channels.filter((item) => item.chat_id !== chat_id) }));
	},
	tickJobs: () => {
		set((state) => ({ jobs: state.jobs.map((job) => {
			if (job.kind === "resolve") {
				const progress = Math.min(100, job.progress + 4);
				return {
					...job,
					progress
				};
			}
			const bump = 1.5 + Math.random() * 3.5;
			return {
				...job,
				progress: Math.min(100, job.progress + bump)
			};
		}) }));
	},
	pushLog: (level, message) => {
		const at = (/* @__PURE__ */ new Date()).toLocaleTimeString("en-GB", { hour12: false });
		set((state) => ({ logs: [{
			id: `${Date.now()}`,
			level,
			message,
			at
		}, ...state.logs].slice(0, 40) }));
	}
}));
function Badge({ className, tone = "neutral", children }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
		className: cn("inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium tracking-wide", tone === "neutral" && "bg-surface-2 text-muted-foreground", tone === "live" && "bg-ok/15 text-ok", tone === "restart" && "bg-warn/15 text-warn", tone === "ok" && "bg-ok/15 text-ok", tone === "warn" && "bg-warn/15 text-warn", tone === "danger" && "bg-danger/15 text-danger", className),
		children
	});
}
var SERIES = [
	{
		day: "Wed",
		n: 820
	},
	{
		day: "Thu",
		n: 940
	},
	{
		day: "Fri",
		n: 1012
	},
	{
		day: "Sat",
		n: 1288
	},
	{
		day: "Sun",
		n: 1440
	},
	{
		day: "Mon",
		n: 1195
	},
	{
		day: "Tue",
		n: 1362
	}
];
function OverviewView() {
	const stats = useAdmin((s) => s.stats);
	const jobs = useAdmin((s) => s.jobs);
	const workers = useAdmin((s) => s.workers);
	const queued = useAdmin((s) => s.queued);
	const completed = useAdmin((s) => s.completed);
	const env = useAdmin((s) => s.env);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-6xl space-y-6",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-[11px] uppercase tracking-[0.18em] text-subtle",
				children: "Overview"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
				className: "mt-1 font-display text-2xl font-semibold tracking-tight",
				children: "Operations"
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("section", {
				className: "grid grid-cols-2 gap-3 lg:grid-cols-4",
				children: [
					{
						label: "Users",
						value: stats.users.toLocaleString()
					},
					{
						label: "Downloads",
						value: stats.downloads.toLocaleString()
					},
					{
						label: "Premium",
						value: String(stats.premium)
					},
					{
						label: "Workers",
						value: `${workers} live`
					}
				].map((card) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "rounded-lg border border-border bg-surface p-4",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-[11px] uppercase tracking-[0.14em] text-subtle",
						children: card.label
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-2 font-display text-2xl font-semibold tabular-nums",
						children: card.value
					})]
				}, card.label))
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "grid gap-4 lg:grid-cols-[1.4fr_0.8fr]",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "rounded-lg border border-border bg-surface p-4 sm:p-5",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "mb-3 flex items-end justify-between",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
							className: "font-display text-base font-semibold",
							children: "Throughput"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-sm text-muted-foreground",
							children: "Completed sends, last 7 days"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
							className: "font-mono text-xs text-subtle",
							children: [completed.toLocaleString(), " total"]
						})]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "h-44",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ResponsiveContainer, {
							width: "100%",
							height: "100%",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(AreaChart, {
								data: SERIES,
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("defs", { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("linearGradient", {
										id: "fillN",
										x1: "0",
										y1: "0",
										x2: "0",
										y2: "1",
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("stop", {
											offset: "0%",
											stopColor: "#c5ccd6",
											stopOpacity: .28
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("stop", {
											offset: "100%",
											stopColor: "#c5ccd6",
											stopOpacity: 0
										})]
									}) }),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(XAxis, {
										dataKey: "day",
										tick: {
											fill: "#6d7380",
											fontSize: 11
										},
										axisLine: false,
										tickLine: false
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Tooltip, {
										contentStyle: {
											background: "#111318",
											border: "1px solid rgba(243,244,246,0.12)",
											borderRadius: 8
										},
										labelStyle: { color: "#9aa0ab" }
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Area, {
										type: "monotone",
										dataKey: "n",
										stroke: "#d7dde6",
										fill: "url(#fillN)",
										strokeWidth: 1.6
									})
								]
							})
						})
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "rounded-lg border border-border bg-surface p-4 sm:p-5",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
							className: "font-display text-base font-semibold",
							children: "Queue"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-1 text-sm text-muted-foreground",
							children: "Fair priority: VIP, Super, Regular, then free. One user cannot occupy another user's files."
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("dl", {
							className: "mt-5 space-y-3",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex justify-between text-sm",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("dt", {
										className: "text-muted-foreground",
										children: "Waiting"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("dd", {
										className: "font-mono tabular-nums",
										children: queued
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex justify-between text-sm",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("dt", {
										className: "text-muted-foreground",
										children: "Max concurrent"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("dd", {
										className: "font-mono tabular-nums",
										children: env.MAX_CONCURRENT
									})]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
									className: "flex justify-between text-sm",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("dt", {
										className: "text-muted-foreground",
										children: "Queue cap"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("dd", {
										className: "font-mono tabular-nums",
										children: env.MAX_QUEUE_SIZE
									})]
								})
							]
						})
					]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "rounded-lg border border-border bg-surface p-4 sm:p-5",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mb-4 flex items-center justify-between gap-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
						className: "font-display text-base font-semibold",
						children: "Isolated lanes"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-sm text-muted-foreground",
						children: "Each transfer writes only under its own user/job directory."
					})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Badge, {
						tone: "live",
						children: [jobs.length, " in flight"]
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
					className: "space-y-4",
					children: jobs.map((job) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
						className: "rounded-md bg-surface-2 p-3",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex flex-wrap items-center justify-between gap-2",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
									className: "text-sm font-medium",
									children: [job.filename, /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
										className: "ml-2 font-mono text-xs text-subtle",
										children: ["u", job.user_id]
									})]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
									className: "font-mono text-xs text-muted-foreground",
									children: [
										Math.round(job.progress),
										"% · ",
										job.speed
									]
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "mt-2 h-1.5 overflow-hidden rounded-full bg-bg",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "h-full rounded-full bg-primary transition-[width] duration-[var(--motion-fast)]",
									style: { width: `${Math.min(100, job.progress)}%` }
								})
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "mt-2 truncate font-mono text-[11px] text-subtle",
								children: job.path
							})
						]
					}, job.job_id))
				})]
			})
		]
	});
}
var buttonVariants = cva("inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-[opacity,transform,background-color,color,border-color] duration-[var(--motion-quick)] ease-[var(--ease-out)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-40 active:scale-[0.98]", {
	variants: {
		variant: {
			default: "bg-primary text-primary-foreground hover:opacity-90",
			secondary: "bg-secondary text-secondary-foreground border border-border hover:bg-surface-2",
			ghost: "text-muted-foreground hover:bg-surface-2 hover:text-foreground",
			danger: "bg-danger text-white hover:opacity-90"
		},
		size: {
			default: "h-11 px-4",
			sm: "h-9 px-3 text-xs",
			lg: "h-12 px-5",
			icon: "size-11"
		}
	},
	defaultVariants: {
		variant: "default",
		size: "default"
	}
});
var Button = import_react.forwardRef(({ className, variant, size, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
	ref,
	className: cn(buttonVariants({
		variant,
		size
	}), className),
	...props
}));
Button.displayName = "Button";
var Input = import_react.forwardRef(({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
	ref,
	suppressHydrationWarning: true,
	className: cn("flex h-11 w-full rounded-md border border-border bg-surface px-3 text-sm text-foreground placeholder:text-subtle outline-none transition-[border-color,box-shadow] duration-[var(--motion-quick)] focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40", className),
	...props
}));
Input.displayName = "Input";
var Textarea = import_react.forwardRef(({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
	ref,
	className: cn("flex min-h-24 w-full rounded-md border border-border bg-surface px-3 py-2.5 text-sm text-foreground placeholder:text-subtle outline-none transition-[border-color,box-shadow] duration-[var(--motion-quick)] focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40", className),
	...props
}));
Textarea.displayName = "Textarea";
var CATS = [
	"telegram",
	"security",
	"database",
	"limits",
	"content",
	"resolvers",
	"miniapps",
	"payments",
	"delivery",
	"custom"
];
function EnvironmentView() {
	const env = useAdmin((s) => s.env);
	const customKeys = useAdmin((s) => s.customKeys);
	const setEnv = useAdmin((s) => s.setEnv);
	const addEnv = useAdmin((s) => s.addEnv);
	const deleteEnv = useAdmin((s) => s.deleteEnv);
	const [query, setQuery] = (0, import_react.useState)("");
	const [cat, setCat] = (0, import_react.useState)("all");
	const [reveal, setReveal] = (0, import_react.useState)({});
	const [draft, setDraft] = (0, import_react.useState)({});
	const [newKey, setNewKey] = (0, import_react.useState)("");
	const [newVal, setNewVal] = (0, import_react.useState)("");
	const rows = (0, import_react.useMemo)(() => {
		const catalogRows = ENV_CATALOG.map((meta) => ({
			...meta,
			value: env[meta.key] ?? ""
		}));
		const extra = customKeys.filter((key) => !ENV_CATALOG.some((item) => item.key === key)).map((key) => ({
			key,
			category: "custom",
			type: "string",
			label: key,
			description: "Custom variable stored in the environment file.",
			restart: false,
			value: env[key] ?? ""
		}));
		return [...catalogRows, ...extra].filter((row) => {
			if (cat !== "all" && row.category !== cat) return false;
			if (!query.trim()) return true;
			return `${row.key} ${row.label} ${row.description}`.toLowerCase().includes(query.trim().toLowerCase());
		});
	}, [
		env,
		customKeys,
		cat,
		query
	]);
	function valueOf(key) {
		return draft[key] ?? env[key] ?? "";
	}
	function saveOne(key) {
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
		for (const key of keys) if (setEnv(key, draft[key] ?? "").restart) restart = true;
		setDraft({});
		toast.success(restart ? "Saved. Some values need a process restart." : "All changes applied live.");
	}
	function onAdd(event) {
		event.preventDefault();
		if (!newKey.trim()) return;
		addEnv(newKey, newVal);
		setNewKey("");
		setNewVal("");
		toast.success("Variable added");
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-6xl space-y-5",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
				className: "flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-[11px] uppercase tracking-[0.18em] text-subtle",
						children: "Environment"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
						className: "mt-1 font-display text-2xl font-semibold tracking-tight",
						children: ".env control"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-1 max-w-xl text-sm text-muted-foreground",
						children: "View, edit, and add values. Live keys update the running bot; restart keys are written now and take effect on the next process boot."
					})
				] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "flex gap-2",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
						variant: "secondary",
						onClick: saveDirty,
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Save, { className: "size-4" }), "Save edits"]
					})
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-col gap-3 lg:flex-row",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
					value: query,
					onChange: (e) => setQuery(e.target.value),
					placeholder: "Search keys, for example BOT_TOKEN",
					className: "lg:max-w-sm"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex gap-2 overflow-x-auto pb-1",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						onClick: () => setCat("all"),
						className: cn("h-11 shrink-0 rounded-full px-3 text-xs", cat === "all" ? "bg-primary text-primary-foreground" : "bg-surface-2 text-muted-foreground"),
						children: "All"
					}), CATS.map((item) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						onClick: () => setCat(item),
						className: cn("h-11 shrink-0 rounded-full px-3 text-xs", cat === item ? "bg-primary text-primary-foreground" : "bg-surface-2 text-muted-foreground"),
						children: CATEGORY_LABEL[item]
					}, item))]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
				className: "space-y-3",
				children: rows.map((row) => {
					const shown = reveal[row.key];
					const current = valueOf(row.key);
					const display = SENSITIVE.has(row.key) && !shown ? maskValue(row.key, current, false) : current;
					const dirty = draft[row.key] !== void 0 && draft[row.key] !== env[row.key];
					return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
						className: "rounded-lg border border-border bg-surface p-4",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex flex-wrap items-start justify-between gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex flex-wrap items-center gap-2",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
										className: "font-mono text-sm font-medium",
										children: row.key
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
										tone: row.restart ? "restart" : "live",
										children: row.restart ? "restart" : "live"
									}),
									dirty ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
										tone: "warn",
										children: "unsaved"
									}) : null
								]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "mt-1 text-sm text-muted-foreground",
								children: row.description
							})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "text-[11px] uppercase tracking-[0.12em] text-subtle",
								children: CATEGORY_LABEL[row.category]
							})]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mt-3 flex flex-col gap-2 sm:flex-row",
							children: [
								row.type === "text" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Textarea, {
									value: display,
									onChange: (e) => setDraft((d) => ({
										...d,
										[row.key]: e.target.value
									})),
									className: "min-h-20 flex-1"
								}) : row.type === "boolean" ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
									className: "h-11 flex-1 rounded-md border border-border bg-surface px-3 text-sm",
									value: /^(1|true|yes|on)$/i.test(current) ? "true" : "false",
									onChange: (e) => setDraft((d) => ({
										...d,
										[row.key]: e.target.value
									})),
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: "true",
										children: "true"
									}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: "false",
										children: "false"
									})]
								}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
									type: SENSITIVE.has(row.key) && !shown ? "password" : row.type === "number" ? "text" : "text",
									inputMode: row.type === "number" ? "decimal" : void 0,
									value: SENSITIVE.has(row.key) && !shown ? display : current,
									onChange: (e) => setDraft((d) => ({
										...d,
										[row.key]: e.target.value
									})),
									className: "flex-1 font-mono"
								}),
								SENSITIVE.has(row.key) ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
									type: "button",
									variant: "secondary",
									size: "icon",
									onClick: () => setReveal((r) => ({
										...r,
										[row.key]: !r[row.key]
									})),
									"aria-label": shown ? "Hide value" : "Reveal value",
									children: shown ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EyeOff, { className: "size-4" }) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Eye, { className: "size-4" })
								}) : null,
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
									type: "button",
									onClick: () => saveOne(row.key),
									children: "Apply"
								}),
								row.category === "custom" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
									type: "button",
									variant: "danger",
									onClick: () => deleteEnv(row.key),
									children: "Remove"
								}) : null
							]
						})]
					}, row.key);
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("form", {
				onSubmit: onAdd,
				className: "rounded-lg border border-dashed border-border p-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
						className: "font-display text-base font-semibold",
						children: "Add variable"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-1 text-sm text-muted-foreground",
						children: "Any KEY=value pair is written to the environment file. Unknown keys are treated as custom."
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "mt-4 grid gap-2 sm:grid-cols-[1fr_1fr_auto]",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
								placeholder: "NEW_KEY",
								value: newKey,
								onChange: (e) => setNewKey(e.target.value.toUpperCase()),
								className: "font-mono"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
								placeholder: "value",
								value: newVal,
								onChange: (e) => setNewVal(e.target.value)
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
								type: "submit",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Plus, { className: "size-4" }), "Add"]
							})
						]
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
				className: "flex items-center gap-2 text-xs text-subtle",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(RotateCcw, { className: "size-3.5" }), "BOT_TOKEN, MongoDB, and Bot API URL write immediately and flag a process restart."]
			})
		]
	});
}
function RuntimeView() {
	const settings = useAdmin((s) => s.settings);
	const applySettings = useAdmin((s) => s.applySettings);
	const env = useAdmin((s) => s.env);
	const setEnv = useAdmin((s) => s.setEnv);
	const workers = useAdmin((s) => s.workers);
	function onSubmit(event) {
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
			dumpChannel: String(data.get("dump_channel") || "")
		});
		setEnv("MAX_FILE_MB", String(limit));
		setEnv("MAX_CONCURRENT", String(workersNext));
		setEnv("MAINTENANCE", data.get("maintenance") === "on" ? "true" : "false");
		setEnv("BOT_PUBLIC", data.get("bot_public") === "true" ? "true" : "false");
		toast.success("Runtime settings applied without a reboot");
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-3xl space-y-5",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", { children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-[11px] uppercase tracking-[0.18em] text-subtle",
				children: "Runtime"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
				className: "mt-1 font-display text-2xl font-semibold tracking-tight",
				children: "Live flags"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-1 text-sm text-muted-foreground",
				children: "These write to Mongo KV and the in-memory settings object. No restart."
			})
		] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("form", {
			onSubmit,
			className: "space-y-4 rounded-lg border border-border bg-surface p-4 sm:p-5",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "grid gap-4 sm:grid-cols-2",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Field, {
							label: "Upload limit MB",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
								name: "limit",
								type: "number",
								min: 1,
								defaultValue: settings.limit
							})
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Field, {
							label: "Workers",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
								name: "workers",
								type: "number",
								min: 1,
								max: 64,
								defaultValue: workers
							})
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Field, {
							label: "Maintenance",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
								name: "maintenance",
								defaultValue: settings.maintenance ? "on" : "off",
								className: "h-11 w-full rounded-md border border-border bg-surface px-3 text-sm",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "off",
									children: "off"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "on",
									children: "on"
								})]
							})
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Field, {
							label: "Bot access",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
								name: "bot_public",
								defaultValue: settings.botPublic ? "true" : "false",
								className: "h-11 w-full rounded-md border border-border bg-surface px-3 text-sm",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "true",
									children: "public"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "false",
									children: "authorised only"
								})]
							})
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Field, {
							label: "Log channel",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
								name: "log_channel",
								defaultValue: settings.logChannel
							})
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Field, {
							label: "Dump channel",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
								name: "dump_channel",
								defaultValue: settings.dumpChannel
							})
						})
					]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Field, {
					label: "Welcome text",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Textarea, {
						name: "welcome",
						defaultValue: settings.welcome
					})
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Field, {
					label: "Caption template",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Textarea, {
						name: "caption",
						defaultValue: settings.caption
					})
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
					className: "font-mono text-xs text-subtle",
					children: ["transport · ", env.BOT_API_URL ? "local bot api · 2 GB" : "cloud api · 49 MB"]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					type: "submit",
					children: "Save runtime"
				})
			]
		})]
	});
}
function Field({ label, children }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
		className: "block space-y-1.5",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
			className: "text-[11px] uppercase tracking-[0.14em] text-subtle",
			children: label
		}), children]
	});
}
var EMPTY = {
	key: "",
	label: "",
	short_label: "",
	price: 0,
	duration_days: 30,
	batch_limit: 5,
	total_links: 0,
	active: true
};
function PlansView() {
	const plans = useAdmin((s) => s.plans);
	const savePlan = useAdmin((s) => s.savePlan);
	const hidePlan = useAdmin((s) => s.hidePlan);
	const [form, setForm] = (0, import_react.useState)(EMPTY);
	function onSubmit(event) {
		event.preventDefault();
		if (!form.key || !form.label) return;
		savePlan({
			...form,
			key: form.key.toLowerCase()
		});
		setForm(EMPTY);
		toast.success("Plan saved");
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-4xl space-y-5",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-[11px] uppercase tracking-[0.18em] text-subtle",
				children: "Plans"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
				className: "mt-1 font-display text-2xl font-semibold tracking-tight",
				children: "Premium catalog"
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
				className: "space-y-2",
				children: plans.map((plan) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
					className: "flex flex-col gap-3 rounded-lg border border-border bg-surface p-4 sm:flex-row sm:items-center sm:justify-between",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
						className: "font-medium",
						children: [
							plan.label,
							" ",
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "font-mono text-xs text-subtle",
								children: plan.key
							}),
							!plan.active ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "ml-2 text-xs text-warn",
								children: "hidden"
							}) : null
						]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
						className: "text-sm text-muted-foreground",
						children: [
							"₹",
							plan.price,
							" · ",
							plan.duration_days,
							" days · batch ",
							plan.batch_limit,
							" ·",
							" ",
							plan.total_links ? `${plan.total_links} links` : "unlimited"
						]
					})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							variant: "secondary",
							size: "sm",
							onClick: () => setForm(plan),
							children: "Edit"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							variant: "danger",
							size: "sm",
							onClick: () => hidePlan(plan.key),
							children: "Hide"
						})]
					})]
				}, plan.key))
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("form", {
				onSubmit,
				className: "grid gap-3 rounded-lg border border-border bg-surface p-4 sm:grid-cols-2",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
						className: "font-display text-base font-semibold sm:col-span-2",
						children: "Add or edit"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						placeholder: "key",
						value: form.key,
						onChange: (e) => setForm({
							...form,
							key: e.target.value
						})
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						placeholder: "name",
						value: form.label,
						onChange: (e) => setForm({
							...form,
							label: e.target.value
						})
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						placeholder: "short name",
						value: form.short_label,
						onChange: (e) => setForm({
							...form,
							short_label: e.target.value
						})
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						placeholder: "price",
						type: "number",
						value: form.price,
						onChange: (e) => setForm({
							...form,
							price: Number(e.target.value)
						})
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						placeholder: "days",
						type: "number",
						value: form.duration_days,
						onChange: (e) => setForm({
							...form,
							duration_days: Number(e.target.value)
						})
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						placeholder: "batch",
						type: "number",
						value: form.batch_limit,
						onChange: (e) => setForm({
							...form,
							batch_limit: Number(e.target.value)
						})
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						placeholder: "total links, 0 = unlimited",
						type: "number",
						value: form.total_links,
						onChange: (e) => setForm({
							...form,
							total_links: Number(e.target.value)
						})
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "flex items-end sm:col-span-2",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							type: "submit",
							children: "Save plan"
						})
					})
				]
			})
		]
	});
}
function UsersView() {
	const users = useAdmin((s) => s.users);
	const applyUserAction = useAdmin((s) => s.applyUserAction);
	const [userId, setUserId] = (0, import_react.useState)("");
	const [action, setAction] = (0, import_react.useState)("premium");
	const [plan, setPlan] = (0, import_react.useState)("r");
	const [q, setQ] = (0, import_react.useState)("");
	function onSubmit(event) {
		event.preventDefault();
		const id = Number(userId);
		if (!id) return;
		applyUserAction(id, action, plan);
		toast.success(`Applied ${action} to ${id}`);
	}
	const filtered = users.filter((user) => {
		if (!q.trim()) return true;
		return `${user.user_id} ${user.name} ${user.username} ${user.plan}`.toLowerCase().includes(q.toLowerCase());
	});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-4xl space-y-5",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-[11px] uppercase tracking-[0.18em] text-subtle",
				children: "Users"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
				className: "mt-1 font-display text-2xl font-semibold tracking-tight",
				children: "Accounts"
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("form", {
				onSubmit,
				className: "grid gap-2 rounded-lg border border-border bg-surface p-4 sm:grid-cols-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						placeholder: "telegram user id",
						value: userId,
						onChange: (e) => setUserId(e.target.value)
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
						value: action,
						onChange: (e) => setAction(e.target.value),
						className: "h-11 rounded-md border border-border bg-surface px-3 text-sm",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
								value: "premium",
								children: "grant premium"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
								value: "ban",
								children: "ban"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
								value: "unban",
								children: "unban"
							})
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						placeholder: "plan key",
						value: plan,
						onChange: (e) => setPlan(e.target.value)
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						type: "submit",
						children: "Apply"
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
				placeholder: "filter users",
				value: q,
				onChange: (e) => setQ(e.target.value)
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
				className: "divide-y divide-border rounded-lg border border-border bg-surface",
				children: filtered.map((user) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
					className: "flex flex-wrap items-center justify-between gap-3 px-4 py-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
						className: "text-sm font-medium",
						children: [
							user.name,
							" ",
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
								className: "font-mono text-xs text-subtle",
								children: ["@", user.username]
							})
						]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
						className: "font-mono text-xs text-muted-foreground",
						children: [
							user.user_id,
							" · ",
							user.downloads,
							" files · ",
							user.seen
						]
					})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "flex items-center gap-2",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
							tone: user.banned ? "danger" : user.plan === "free" ? "neutral" : "ok",
							children: user.banned ? "banned" : user.plan
						})
					})]
				}, user.user_id))
			})
		]
	});
}
function ChannelsView() {
	const channels = useAdmin((s) => s.channels);
	const addChannel = useAdmin((s) => s.addChannel);
	const removeChannel = useAdmin((s) => s.removeChannel);
	const [chat, setChat] = (0, import_react.useState)("");
	const [invite, setInvite] = (0, import_react.useState)("");
	function onSubmit(event) {
		event.preventDefault();
		if (!chat.trim()) return;
		addChannel(chat.trim(), invite.trim());
		setChat("");
		setInvite("");
		toast.success("Force-sub channel saved");
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-3xl space-y-5",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-[11px] uppercase tracking-[0.18em] text-subtle",
				children: "Channels"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
				className: "mt-1 font-display text-2xl font-semibold tracking-tight",
				children: "Force-sub"
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
				className: "space-y-2",
				children: channels.map((channel) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
					className: "flex items-center justify-between gap-3 rounded-lg border border-border bg-surface p-4",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "min-w-0",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "truncate font-medium",
							children: channel.chat_id
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "truncate font-mono text-xs text-muted-foreground",
							children: channel.invite_url
						})]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						variant: "danger",
						size: "sm",
						onClick: () => removeChannel(channel.chat_id),
						children: "Remove"
					})]
				}, channel.chat_id))
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("form", {
				onSubmit,
				className: "grid gap-2 rounded-lg border border-border bg-surface p-4 sm:grid-cols-[1fr_1fr_auto]",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						placeholder: "channel id or @username",
						value: chat,
						onChange: (e) => setChat(e.target.value)
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						placeholder: "invite url, optional",
						value: invite,
						onChange: (e) => setInvite(e.target.value)
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						type: "submit",
						children: "Add"
					})
				]
			})
		]
	});
}
function AppsView() {
	const env = useAdmin((s) => s.env);
	const apps = [
		{
			name: "Flezen",
			bot: env.FLEZEN_TG_BOT,
			url: env.FLEZEN_WEBAPP_URL
		},
		{
			name: "DiskWala",
			bot: env.DISKWALA_TG_BOT,
			url: env.DISKWALA_WEBAPP_URL
		},
		{
			name: "VidBunker",
			bot: env.VIDBUNKER_TG_BOT,
			url: env.VIDBUNKER_WEBAPP_URL
		}
	];
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-3xl space-y-5",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "text-[11px] uppercase tracking-[0.18em] text-subtle",
			children: "Mini Apps"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
			className: "mt-1 font-display text-2xl font-semibold tracking-tight",
			children: "Resolver connections"
		})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
			className: "space-y-2",
			children: apps.map((app) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
				className: "flex items-center justify-between gap-3 rounded-lg border border-border bg-surface p-4",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "min-w-0",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "font-medium",
						children: app.name
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "truncate font-mono text-xs text-muted-foreground",
						children: app.url || "not configured"
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
					tone: app.bot ? "ok" : "warn",
					children: app.bot ? "configured" : "missing bot"
				})]
			}, app.name))
		})]
	});
}
function LogsView() {
	const logs = useAdmin((s) => s.logs);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-4xl space-y-5",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "text-[11px] uppercase tracking-[0.18em] text-subtle",
			children: "Logs"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
			className: "mt-1 font-display text-2xl font-semibold tracking-tight",
			children: "Recent events"
		})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ol", {
			className: "divide-y divide-border overflow-hidden rounded-lg border border-border bg-surface",
			children: logs.map((log) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
				className: "flex flex-col gap-1 px-4 py-3 sm:flex-row sm:items-start sm:gap-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "font-mono text-xs text-subtle tabular-nums",
						children: log.at
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
						tone: log.level === "error" ? "danger" : log.level === "warn" ? "warn" : "ok",
						children: log.level
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-sm text-foreground",
						children: log.message
					})
				]
			}, log.id))
		})]
	});
}
var NAV = [
	{
		id: "overview",
		label: "Overview",
		icon: LayoutDashboard
	},
	{
		id: "environment",
		label: "Environment",
		icon: KeyRound
	},
	{
		id: "runtime",
		label: "Runtime",
		icon: SlidersHorizontal
	},
	{
		id: "plans",
		label: "Plans",
		icon: Boxes
	},
	{
		id: "users",
		label: "Users",
		icon: Users
	},
	{
		id: "channels",
		label: "Channels",
		icon: Radio
	},
	{
		id: "apps",
		label: "Mini Apps",
		icon: Activity
	},
	{
		id: "logs",
		label: "Logs",
		icon: ListTree
	}
];
function AppShell() {
	const view = useAdmin((s) => s.view);
	const setView = useAdmin((s) => s.setView);
	const logout = useAdmin((s) => s.logout);
	const env = useAdmin((s) => s.env);
	const jobs = useAdmin((s) => s.jobs);
	const tickJobs = useAdmin((s) => s.tickJobs);
	const maintenance = useAdmin((s) => s.settings.maintenance);
	(0, import_react.useEffect)(() => {
		const id = window.setInterval(tickJobs, 900);
		return () => window.clearInterval(id);
	}, [tickJobs]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "min-h-dvh bg-bg lg:grid lg:grid-cols-[240px_1fr]",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("aside", {
				className: "hidden border-r border-border lg:flex lg:flex-col lg:px-4 lg:py-6",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "px-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "font-display text-lg font-semibold tracking-tight",
							children: "TeraDrop"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-0.5 text-[11px] uppercase tracking-[0.18em] text-subtle",
							children: "Control center"
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("nav", {
						className: "mt-8 flex flex-1 flex-col gap-1",
						children: NAV.map((item) => {
							const Icon = item.icon;
							const active = view === item.id;
							return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
								onClick: () => setView(item.id),
								className: cn("flex h-11 items-center gap-3 rounded-md px-3 text-sm transition-colors duration-[var(--motion-quick)]", active ? "bg-surface-2 text-foreground" : "text-muted-foreground hover:bg-surface hover:text-foreground"),
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Icon, { className: "size-4" }), item.label]
							}, item.id);
						})
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						onClick: logout,
						className: "mt-4 flex h-11 items-center gap-3 rounded-md px-3 text-sm text-muted-foreground hover:bg-surface hover:text-foreground",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(LogOut, { className: "size-4" }), "Log out"]
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex min-w-0 flex-col",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
					className: "flex items-center justify-between gap-3 border-b border-border px-4 py-3 sm:px-6",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "min-w-0",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "truncate font-display text-base font-semibold",
							children: env.BOT_NAME || "TeraDrop"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
							className: "truncate font-mono text-xs text-muted-foreground",
							children: ["@", env.BOT_USERNAME || "TeraDropBot"]
						})]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-center gap-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
							className: "hidden rounded-full border border-border px-3 py-1 font-mono text-[11px] text-muted-foreground sm:inline",
							children: [jobs.filter((j) => j.progress < 100).length, " live lanes"]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: cn("rounded-full px-3 py-1 text-[11px] font-medium", maintenance ? "bg-warn/15 text-warn" : "bg-ok/15 text-ok"),
							children: maintenance ? "maintenance" : "live"
						})]
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("main", {
					className: "flex-1 px-4 py-5 pb-24 sm:px-6 lg:pb-8",
					children: [
						view === "overview" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(OverviewView, {}),
						view === "environment" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EnvironmentView, {}),
						view === "runtime" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(RuntimeView, {}),
						view === "plans" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PlansView, {}),
						view === "users" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(UsersView, {}),
						view === "channels" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ChannelsView, {}),
						view === "apps" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(AppsView, {}),
						view === "logs" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(LogsView, {})
					]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("nav", {
				className: "fixed inset-x-0 bottom-0 z-20 flex gap-1 overflow-x-auto border-t border-border bg-bg/95 px-2 py-2 backdrop-blur lg:hidden",
				children: NAV.map((item) => {
					const Icon = item.icon;
					const active = view === item.id;
					return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						onClick: () => setView(item.id),
						className: cn("flex h-11 min-w-16 shrink-0 flex-col items-center justify-center gap-0.5 rounded-md px-2 text-[10px]", active ? "text-foreground" : "text-muted-foreground"),
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Icon, { className: "size-4" }), item.label]
					}, item.id);
				})
			})
		]
	});
}
function LoginScreen() {
	const login = useAdmin((s) => s.login);
	const [password, setPassword] = (0, import_react.useState)("");
	const [error, setError] = (0, import_react.useState)("");
	function onSubmit(event) {
		event.preventDefault();
		if (!login(password)) {
			setError("That password does not match ADMIN_PANEL_PASSWORD.");
			return;
		}
		setError("");
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("main", {
		className: "relative min-h-dvh overflow-hidden px-5 py-10 sm:px-8",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			"aria-hidden": true,
			className: "pointer-events-none absolute inset-x-0 top-0 h-72 bg-[radial-gradient(ellipse_at_top,rgba(197,204,214,0.08),transparent_60%)]"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mx-auto flex min-h-[calc(100dvh-5rem)] w-full max-w-5xl flex-col justify-between gap-12 lg:flex-row lg:items-center",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "max-w-lg",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mb-5 text-[11px] font-medium uppercase tracking-[0.22em] text-muted-foreground",
						children: "TeraDrop · operations"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
						className: "font-display text-4xl font-semibold leading-[1.08] tracking-[-0.03em] text-foreground sm:text-5xl",
						children: "Control center for isolated, concurrent transfers."
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-5 max-w-md text-base leading-relaxed text-muted-foreground",
						children: "Every user gets a private download lane. Environment values — including the bot token — can be edited here and applied live when the process allows."
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("dl", {
						className: "mt-10 grid max-w-md grid-cols-2 gap-6",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("dt", {
							className: "text-[11px] uppercase tracking-[0.16em] text-subtle",
							children: "Isolation"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("dd", {
							className: "mt-1 font-mono text-sm text-foreground",
							children: "/tmp/u<id>/job"
						})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("dt", {
							className: "text-[11px] uppercase tracking-[0.16em] text-subtle",
							children: "Apply"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("dd", {
							className: "mt-1 font-mono text-sm text-foreground",
							children: "live · restart"
						})] })]
					})
				]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("form", {
				onSubmit,
				className: "w-full max-w-md rounded-xl border border-border bg-surface p-5 shadow-[0_0_0_1px_rgba(255,255,255,0.04)] sm:p-7",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "mb-6",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
							className: "font-display text-lg font-semibold",
							children: "Sign in"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
							className: "mt-1 text-sm text-muted-foreground",
							children: [
								"Use the admin password from your environment. Preview default is",
								" ",
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("code", {
									className: "font-mono text-foreground",
									children: "teradrop"
								}),
								"."
							]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
						className: "mb-2 block text-[11px] uppercase tracking-[0.14em] text-subtle",
						children: "Admin password"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						type: "password",
						autoComplete: "current-password",
						placeholder: "enter password",
						value: password,
						onChange: (e) => setPassword(e.target.value)
					}),
					error ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-3 text-sm text-danger",
						children: error
					}) : null,
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						type: "submit",
						className: "mt-5 w-full",
						children: "Open panel"
					})
				]
			})]
		})]
	});
}
function Home() {
	return useAdmin((s) => s.authed) ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(AppShell, {}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(LoginScreen, {});
}
//#endregion
export { Home as component };
