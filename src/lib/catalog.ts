export type EnvType = "string" | "number" | "boolean" | "secret" | "text";

export type EnvCategory =
  | "telegram"
  | "security"
  | "database"
  | "limits"
  | "content"
  | "resolvers"
  | "miniapps"
  | "payments"
  | "delivery"
  | "custom";

export interface EnvMeta {
  key: string;
  category: EnvCategory;
  type: EnvType;
  label: string;
  description: string;
  restart: boolean;
}

export const CATEGORY_LABEL: Record<EnvCategory, string> = {
  telegram: "Telegram",
  security: "Security",
  database: "Database",
  limits: "Limits & queue",
  content: "Copy",
  resolvers: "Resolvers",
  miniapps: "Mini Apps",
  payments: "Payments",
  delivery: "Delivery",
  custom: "Custom",
};

export const ENV_CATALOG: EnvMeta[] = [
  { key: "BOT_TOKEN", category: "telegram", type: "secret", label: "Bot token", description: "Token from BotFather. Changing it reconnects the bot.", restart: true },
  { key: "BOT_NAME", category: "telegram", type: "string", label: "Bot name", description: "Display name used in messages and the control center.", restart: false },
  { key: "BOT_USERNAME", category: "telegram", type: "string", label: "Bot username", description: "Public @username without the @.", restart: false },
  { key: "OWNER_IDS", category: "telegram", type: "string", label: "Owner IDs", description: "Comma-separated Telegram user IDs with full control.", restart: false },
  { key: "AUTHORIZED_IDS", category: "telegram", type: "string", label: "Authorized IDs", description: "Allow-list used when the bot is private.", restart: false },
  { key: "BOT_PUBLIC", category: "telegram", type: "boolean", label: "Public access", description: "Anyone can use the bot when enabled.", restart: false },
  { key: "BOT_API_URL", category: "telegram", type: "string", label: "Local Bot API URL", description: "Local Bot API root for uploads up to 2 GB.", restart: true },
  { key: "TELEGRAM_API_ID", category: "telegram", type: "number", label: "Telegram API ID", description: "From my.telegram.org, required for Mini App login.", restart: true },
  { key: "TELEGRAM_API_HASH", category: "telegram", type: "secret", label: "Telegram API hash", description: "From my.telegram.org, required for Mini App login.", restart: true },
  { key: "LOG_CHANNEL", category: "telegram", type: "string", label: "Log channel", description: "Channel or chat ID for operational logs.", restart: false },
  { key: "DUMP_CHANNEL", category: "telegram", type: "string", label: "Dump channel", description: "Channel or chat ID for payment notices.", restart: false },
  { key: "ADMIN_PANEL_PASSWORD", category: "security", type: "secret", label: "Admin password", description: "Password for this control center. Applied immediately.", restart: false },
  { key: "SESSION_SECRET", category: "security", type: "secret", label: "Session secret", description: "Encrypts Telethon Mini App sessions.", restart: true },
  { key: "MONGODB_URI", category: "database", type: "secret", label: "MongoDB URI", description: "Connection string. Requires a process restart.", restart: true },
  { key: "MONGODB_DATABASE", category: "database", type: "string", label: "MongoDB database", description: "Database name. Requires a process restart.", restart: true },
  { key: "MAINTENANCE", category: "limits", type: "boolean", label: "Maintenance mode", description: "Pause public processing without stopping the bot.", restart: false },
  { key: "MAX_FILE_MB", category: "limits", type: "number", label: "Max send size (MB)", description: "Owner cap for send-to-chat.", restart: false },
  { key: "MAX_CONCURRENT", category: "limits", type: "number", label: "Worker count", description: "Download/upload workers. Applied live.", restart: false },
  { key: "MAX_QUEUE_SIZE", category: "limits", type: "number", label: "Queue size", description: "Maximum waiting jobs before new requests are rejected.", restart: false },
  { key: "FREE_LINKS_PER_24H", category: "limits", type: "number", label: "Free links / 24h", description: "Rolling free-tier link budget.", restart: false },
  { key: "FREE_SEND_FILE_LIFETIME", category: "limits", type: "number", label: "Free send-file credits", description: "Lifetime send-to-Telegram credits for free users.", restart: false },
  { key: "AUTO_DELETE_MINUTES", category: "limits", type: "number", label: "Auto-delete (minutes)", description: "How long sent files remain in chat.", restart: false },
  { key: "WELCOME_TEXT", category: "content", type: "text", label: "Welcome text", description: "Override for the /start message.", restart: false },
  { key: "CAPTION_TEMPLATE", category: "content", type: "text", label: "Caption template", description: "Supports {filename}, {size}, {url}.", restart: false },
  { key: "TERABOXDL_URL", category: "resolvers", type: "string", label: "TeraBox resolver", description: "Primary TeraBox resolver host.", restart: false },
  { key: "SOLVER_URL", category: "resolvers", type: "string", label: "Turnstile solver", description: "Cloudflare Turnstile solver endpoint.", restart: false },
  { key: "UPFILES_SOLVER_URL", category: "resolvers", type: "string", label: "UpFiles solver", description: "Solver used for UpFiles.", restart: false },
  { key: "FLEZEN_TG_BOT", category: "miniapps", type: "string", label: "Flezen bot", description: "Username of the Flezen Mini App bot.", restart: false },
  { key: "FLEZEN_WEBAPP_URL", category: "miniapps", type: "string", label: "Flezen WebApp URL", description: "Flezen Mini App URL.", restart: false },
  { key: "DISKWALA_TG_BOT", category: "miniapps", type: "string", label: "DiskWala bot", description: "Username of the DiskWala Mini App bot.", restart: false },
  { key: "DISKWALA_WEBAPP_URL", category: "miniapps", type: "string", label: "DiskWala WebApp URL", description: "DiskWala Mini App URL.", restart: false },
  { key: "VIDBUNKER_TG_BOT", category: "miniapps", type: "string", label: "VidBunker bot", description: "Username of the VidBunker Mini App bot.", restart: false },
  { key: "VIDBUNKER_WEBAPP_URL", category: "miniapps", type: "string", label: "VidBunker WebApp URL", description: "VidBunker Mini App URL.", restart: false },
  { key: "PAYTM_MID", category: "payments", type: "secret", label: "Paytm MID", description: "Paytm merchant ID used by the payment proxy.", restart: false },
  { key: "UPI_ID", category: "payments", type: "secret", label: "UPI ID", description: "UPI address printed on premium QR codes.", restart: false },
  { key: "UPI_PAYEE_NAME", category: "payments", type: "string", label: "UPI payee name", description: "Name shown in the UPI collect request.", restart: false },
  { key: "PAYMENT_API_URL", category: "payments", type: "string", label: "Payment API", description: "Paytm verification proxy URL.", restart: false },
  { key: "PUBLIC_BASE_URL", category: "delivery", type: "string", label: "Public base URL", description: "HTTPS origin used to hide stream/direct links.", restart: false },
  { key: "PUBLIC_HOST", category: "delivery", type: "string", label: "Public host", description: "Hostname or IP in front of Caddy.", restart: false },
  { key: "PUBLIC_PORT", category: "delivery", type: "string", label: "Public port", description: "Public HTTPS port, default 6969.", restart: false },
  { key: "DOWNLOAD_DIR", category: "delivery", type: "string", label: "Download directory", description: "Scratch directory. Per-user folders are created automatically.", restart: true },
  { key: "HEALTH_PORT", category: "delivery", type: "number", label: "Health/admin port", description: "Internal port for /admin, /media and health checks.", restart: true },
];

export const SENSITIVE = new Set(
  ENV_CATALOG.filter((item) => item.type === "secret").map((item) => item.key),
);

export function maskValue(key: string, value: string, reveal: boolean) {
  if (reveal || !SENSITIVE.has(key) || !value) return value;
  if (value.length <= 4) return "••••";
  return `••••••••${value.slice(-4)}`;
}

export const DEFAULT_ENV: Record<string, string> = {
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
  HEALTH_PORT: "8080",
};
