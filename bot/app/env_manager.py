"""Read, write, and hot-apply .env values from the admin panel."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import signal
import threading
import time
from pathlib import Path
from typing import Any

from app.settings import Settings, settings

log = logging.getLogger("teradrop.env")

_ENV_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
_UNSET = object()

SENSITIVE_KEYS = {
    "BOT_TOKEN",
    "SESSION_SECRET",
    "ADMIN_PANEL_PASSWORD",
    "ADMIN_PANEL_TOKEN",
    "MONGODB_URI",
    "TELEGRAM_API_HASH",
    "PAYTM_MID",
    "UPI_ID",
    "DISKWALA_TG_INIT_DATA",
    "FLEZEN_TG_INIT_DATA",
}

RESTART_KEYS = {
    "BOT_TOKEN",
    "BOT_API_URL",
    "MONGODB_URI",
    "MONGODB_DATABASE",
    "TELEGRAM_API_ID",
    "TELEGRAM_API_HASH",
    "SESSION_SECRET",
    "HEALTH_PORT",
    "DOWNLOAD_DIR",
    "DATA_DIR",
}

CATALOG: list[dict[str, str]] = [
    {"key": "BOT_TOKEN", "category": "telegram", "type": "secret", "label": "Bot token", "description": "Token from BotFather. Changing it reconnects the bot."},
    {"key": "BOT_NAME", "category": "telegram", "type": "string", "label": "Bot name", "description": "Display name used in messages and the admin panel."},
    {"key": "BOT_USERNAME", "category": "telegram", "type": "string", "label": "Bot username", "description": "Public @username without the @."},
    {"key": "OWNER_IDS", "category": "telegram", "type": "string", "label": "Owner IDs", "description": "Comma-separated Telegram user IDs with full control."},
    {"key": "AUTHORIZED_IDS", "category": "telegram", "type": "string", "label": "Authorized IDs", "description": "Allow-list used when the bot is private."},
    {"key": "BOT_PUBLIC", "category": "telegram", "type": "boolean", "label": "Public access", "description": "true = anyone can use the bot; false = authorised users only."},
    {"key": "BOT_API_URL", "category": "telegram", "type": "string", "label": "Local Bot API URL", "description": "Local Bot API root for uploads up to 2 GB, e.g. http://telegram-bot-api:8081."},
    {"key": "TELEGRAM_API_ID", "category": "telegram", "type": "number", "label": "Telegram API ID", "description": "From my.telegram.org, required for Mini App login."},
    {"key": "TELEGRAM_API_HASH", "category": "telegram", "type": "secret", "label": "Telegram API hash", "description": "From my.telegram.org, required for Mini App login."},
    {"key": "LOG_CHANNEL", "category": "telegram", "type": "string", "label": "Log channel", "description": "Channel or chat ID for operational logs."},
    {"key": "DUMP_CHANNEL", "category": "telegram", "type": "string", "label": "Dump channel", "description": "Channel or chat ID for payment and dump notices."},
    {"key": "FORCE_SUB_CHANNEL", "category": "telegram", "type": "string", "label": "Force-sub (legacy)", "description": "Initial force-sub channel; live channels are also stored in MongoDB."},
    {"key": "ADMIN_PANEL_PASSWORD", "category": "security", "type": "secret", "label": "Admin panel password", "description": "Password for the web control center. Applied immediately."},
    {"key": "SESSION_SECRET", "category": "security", "type": "secret", "label": "Session secret", "description": "Encrypts Telethon Mini App sessions in MongoDB."},
    {"key": "MONGODB_URI", "category": "database", "type": "secret", "label": "MongoDB URI", "description": "Connection string. Requires a process restart."},
    {"key": "MONGODB_DATABASE", "category": "database", "type": "string", "label": "MongoDB database", "description": "Database name. Requires a process restart."},
    {"key": "MAINTENANCE", "category": "limits", "type": "boolean", "label": "Maintenance mode", "description": "Pause public processing without stopping the bot."},
    {"key": "MAX_FILE_MB", "category": "limits", "type": "number", "label": "Max send size (MB)", "description": "Owner cap for send-to-chat. Capped at 49 without a local Bot API."},
    {"key": "MAX_CONCURRENT", "category": "limits", "type": "number", "label": "Worker count", "description": "Download/upload workers. Applied live; raise only if the host can take it."},
    {"key": "MAX_QUEUE_SIZE", "category": "limits", "type": "number", "label": "Queue size", "description": "Maximum waiting jobs before new requests are rejected."},
    {"key": "FREE_LINKS_PER_24H", "category": "limits", "type": "number", "label": "Free links / 24h", "description": "Rolling free-tier link budget."},
    {"key": "FREE_SEND_FILE_LIFETIME", "category": "limits", "type": "number", "label": "Free send-file credits", "description": "Lifetime send-to-Telegram credits for free users."},
    {"key": "AUTO_DELETE_MINUTES", "category": "limits", "type": "number", "label": "Auto-delete (minutes)", "description": "How long sent files remain in chat before deletion."},
    {"key": "WELCOME_TEXT", "category": "content", "type": "text", "label": "Welcome text", "description": "Override for the /start message. Applied immediately."},
    {"key": "CAPTION_TEMPLATE", "category": "content", "type": "text", "label": "Caption template", "description": "Supports {filename}, {size}, {url}. Applied immediately."},
    {"key": "TERABOXDL_URL", "category": "resolvers", "type": "string", "label": "TeraBox resolver", "description": "Primary TeraBox resolver host."},
    {"key": "SOLVER_URL", "category": "resolvers", "type": "string", "label": "Turnstile solver", "description": "Cloudflare Turnstile solver endpoint."},
    {"key": "SOLVER_TIMEOUT", "category": "resolvers", "type": "number", "label": "Solver timeout (s)", "description": "Seconds to wait for a solver response."},
    {"key": "TURNSTILE_SITEKEY", "category": "resolvers", "type": "string", "label": "Turnstile site key", "description": "Default Turnstile site key."},
    {"key": "UPFILES_SOLVER_URL", "category": "resolvers", "type": "string", "label": "UpFiles solver", "description": "Solver used specifically for UpFiles."},
    {"key": "UPFILES_PLAYWRIGHT_TIMEOUT", "category": "resolvers", "type": "number", "label": "UpFiles Playwright timeout", "description": "Seconds for the UpFiles headless solve."},
    {"key": "UPFILES_TURNSTILE_SITEKEY", "category": "resolvers", "type": "string", "label": "UpFiles Turnstile key", "description": "Turnstile site key for UpFiles."},
    {"key": "FLEZEN_TG_BOT", "category": "miniapps", "type": "string", "label": "Flezen bot", "description": "Username of the Flezen Mini App bot."},
    {"key": "FLEZEN_WEBAPP_URL", "category": "miniapps", "type": "string", "label": "Flezen WebApp URL", "description": "Flezen Mini App URL."},
    {"key": "DISKWALA_TG_BOT", "category": "miniapps", "type": "string", "label": "DiskWala bot", "description": "Username of the DiskWala Mini App bot."},
    {"key": "DISKWALA_WEBAPP_URL", "category": "miniapps", "type": "string", "label": "DiskWala WebApp URL", "description": "DiskWala Mini App URL."},
    {"key": "VIDBUNKER_TG_BOT", "category": "miniapps", "type": "string", "label": "VidBunker bot", "description": "Username of the VidBunker Mini App bot."},
    {"key": "VIDBUNKER_WEBAPP_URL", "category": "miniapps", "type": "string", "label": "VidBunker WebApp URL", "description": "VidBunker Mini App URL."},
    {"key": "VIDBUNKER_API_URL", "category": "miniapps", "type": "string", "label": "VidBunker API", "description": "VidBunker download API endpoint."},
    {"key": "PAYTM_MID", "category": "payments", "type": "secret", "label": "Paytm MID", "description": "Paytm merchant ID used by the payment proxy."},
    {"key": "UPI_ID", "category": "payments", "type": "secret", "label": "UPI ID", "description": "UPI address printed on premium QR codes."},
    {"key": "UPI_PAYEE_NAME", "category": "payments", "type": "string", "label": "UPI payee name", "description": "Name shown in the UPI collect request."},
    {"key": "PAYMENT_API_URL", "category": "payments", "type": "string", "label": "Payment API", "description": "Paytm verification proxy URL."},
    {"key": "PAYMENT_VERIFY_INTERVAL", "category": "payments", "type": "number", "label": "Verify interval (s)", "description": "How often pending orders are checked."},
    {"key": "PAYMENT_MAX_MINUTES", "category": "payments", "type": "number", "label": "Payment window (min)", "description": "How long a QR order stays valid."},
    {"key": "AMOUNT_TOLERANCE", "category": "payments", "type": "number", "label": "Amount tolerance", "description": "Accepted difference when matching UPI payments."},
    {"key": "PAYMENT_LOG_CHANNEL_ID", "category": "payments", "type": "number", "label": "Payment log channel", "description": "Numeric chat ID for sale receipts."},
    {"key": "PUBLIC_BASE_URL", "category": "delivery", "type": "string", "label": "Public base URL", "description": "HTTPS origin used to hide stream/direct links."},
    {"key": "PUBLIC_HOST", "category": "delivery", "type": "string", "label": "Public host", "description": "Hostname or IP in front of Caddy."},
    {"key": "PUBLIC_PORT", "category": "delivery", "type": "string", "label": "Public port", "description": "Public HTTPS port, default 6969."},
    {"key": "DOWNLOAD_DIR", "category": "delivery", "type": "string", "label": "Download directory", "description": "Scratch directory. Per-user subfolders are created automatically."},
    {"key": "DATA_DIR", "category": "delivery", "type": "string", "label": "Data directory", "description": "Durable data directory."},
    {"key": "HEALTH_PORT", "category": "delivery", "type": "number", "label": "Health/admin port", "description": "Internal port for /admin, /media and health checks."},
    {"key": "TELEGRAM_AUTH_REFRESH_MINUTES", "category": "miniapps", "type": "number", "label": "Mini App refresh (min)", "description": "How often Telethon refreshes Mini App initData."},
]

_ALIAS_TO_FIELD = {
    (field.alias or name): name
    for name, field in Settings.model_fields.items()
}


def env_path() -> Path:
    explicit = os.environ.get("ENV_FILE", "").strip()
    if explicit:
        return Path(explicit)
    cwd = Path.cwd() / ".env"
    if cwd.exists():
        return cwd
    packaged = Path(__file__).resolve().parents[1] / ".env"
    return packaged if packaged.exists() else cwd


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _quote(value: str) -> str:
    if value == "":
        return '""'
    if any(ch in value for ch in ' \t#\'"\\$') or "\n" in value:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def parse_env_file(path: Path | None = None) -> dict[str, str]:
    path = path or env_path()
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _ENV_LINE.match(line)
        if not match:
            continue
        values[match.group(1)] = _strip_quotes(match.group(2))
    return values


def upsert_env_file(updates: dict[str, str], path: Path | None = None) -> Path:
    path = path or env_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = dict(updates)
    out: list[str] = []
    for raw in existing:
        match = _ENV_LINE.match(raw.strip()) if raw.strip() and not raw.strip().startswith("#") else None
        if match and match.group(1) in remaining:
            key = match.group(1)
            out.append(f"{key}={_quote(remaining.pop(key))}")
        else:
            out.append(raw)
    if remaining and out and out[-1].strip():
        out.append("")
    for key, value in remaining.items():
        out.append(f"{key}={_quote(value)}")
    text = "\n".join(out).rstrip() + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return path


def mask_value(key: str, value: str, reveal: bool = False) -> str:
    if reveal or key not in SENSITIVE_KEYS or not value:
        return value
    if len(value) <= 4:
        return "••••"
    return f"••••••••{value[-4:]}"


def _coerce(field_name: str, value: str) -> Any:
    annotation = Settings.model_fields[field_name].annotation
    origin = getattr(annotation, "__origin__", annotation)
    if origin is bool or annotation is bool:
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
    if origin is int or annotation is int:
        return int(value or 0)
    if origin is float or annotation is float:
        return float(value or 0)
    if origin is Path or annotation is Path:
        return Path(value)
    return value


def apply_live(key: str, value: str) -> dict[str, Any]:
    """Mutate the in-memory Settings object and related runtime handles."""
    os.environ[key] = value
    field_name = _ALIAS_TO_FIELD.get(key)
    restart = key in RESTART_KEYS
    applied = False
    if field_name:
        try:
            setattr(settings, field_name, _coerce(field_name, value))
            applied = True
        except Exception as exc:
            log.warning("could not coerce %s: %s", key, exc)

    if key in {"WELCOME_TEXT", "CAPTION_TEMPLATE", "MAINTENANCE", "LOG_CHANNEL", "DUMP_CHANNEL", "BOT_PUBLIC"}:
        from app import storage

        kv_key = {
            "WELCOME_TEXT": "welcome",
            "CAPTION_TEMPLATE": "caption",
            "MAINTENANCE": "maintenance",
            "LOG_CHANNEL": "log_channel",
            "DUMP_CHANNEL": "dump_channel",
            "BOT_PUBLIC": "bot_public",
        }[key]
        mapped = value
        if key == "MAINTENANCE":
            mapped = "on" if str(value).strip().lower() in {"1", "true", "yes", "on"} else "off"
        if key == "BOT_PUBLIC":
            mapped = "true" if str(value).strip().lower() in {"1", "true", "yes", "on"} else "false"
        try:
            storage.kv_set(kv_key, mapped[:4000])
            applied = True
        except Exception:
            log.exception("kv persist failed for %s", key)

    if key == "MAX_CONCURRENT":
        try:
            from app import runtime
            from app.job_queue import JOB_QUEUE

            count = max(1, min(int(value or 1), 64))
            if runtime.loop and runtime.loop.is_running():
                fut = asyncio.run_coroutine_threadsafe(JOB_QUEUE.resize(count), runtime.loop)
                fut.result(timeout=8)
            applied = True
        except Exception:
            log.exception("live worker resize failed")

    if key == "BOT_TOKEN" and value:
        try:
            from app import runtime

            bot = getattr(runtime.application, "bot", None)
            if bot is not None and hasattr(bot, "_token"):
                bot._token = value
                applied = True
            elif bot is not None:
                try:
                    object.__setattr__(bot, "token", value)
                    applied = True
                except Exception:
                    restart = True
        except Exception:
            restart = True

    if key == "ADMIN_PANEL_PASSWORD":
        applied = True
        restart = False

    return {"applied": applied, "restart_required": restart}


def list_variables(reveal: bool = False) -> dict[str, Any]:
    file_values = parse_env_file()
    seen: set[str] = set()
    variables: list[dict[str, Any]] = []
    for item in CATALOG:
        key = item["key"]
        seen.add(key)
        field_name = _ALIAS_TO_FIELD.get(key)
        live = file_values.get(key)
        if live is None and field_name:
            live = getattr(settings, field_name, "")
            if live is None:
                live = ""
            live = str(live)
            if live in {"True", "False"}:
                live = live.lower()
        live = "" if live is None else str(live)
        variables.append(
            {
                **item,
                "value": mask_value(key, live, reveal),
                "has_value": bool(live),
                "sensitive": key in SENSITIVE_KEYS,
                "restart": key in RESTART_KEYS,
                "source": "file" if key in file_values else ("settings" if field_name else "unset"),
            }
        )
    for key, value in sorted(file_values.items()):
        if key in seen:
            continue
        variables.append(
            {
                "key": key,
                "category": "custom",
                "type": "secret" if key in SENSITIVE_KEYS else "string",
                "label": key,
                "description": "Custom variable stored in .env.",
                "value": mask_value(key, value, reveal),
                "has_value": bool(value),
                "sensitive": key in SENSITIVE_KEYS,
                "restart": key in RESTART_KEYS,
                "source": "file",
            }
        )
    path = env_path()
    return {
        "file": str(path),
        "writable": True,
        "exists": path.exists(),
        "variables": variables,
    }


def set_variable(key: str, value: str, reveal: bool = False) -> dict[str, Any]:
    key = key.strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
        raise ValueError("environment key must be letters, numbers, or underscore")
    value = value if value is not None else ""
    upsert_env_file({key: value})
    result = apply_live(key, value)
    listing = list_variables(reveal=reveal)
    listing["result"] = {"key": key, **result}
    return listing


def delete_variable(key: str) -> dict[str, Any]:
    key = key.strip()
    path = env_path()
    if path.exists():
        kept: list[str] = []
        for raw in path.read_text(encoding="utf-8").splitlines():
            match = _ENV_LINE.match(raw.strip()) if raw.strip() and not raw.strip().startswith("#") else None
            if match and match.group(1) == key:
                continue
            kept.append(raw)
        path.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")
    os.environ.pop(key, None)
    return list_variables()


def request_restart() -> None:
    from app import runtime

    if runtime.restart_requested:
        return
    runtime.restart_requested = True

    def _kill() -> None:
        time.sleep(1.2)
        log.info("restarting process so new environment values take effect")
        os.kill(os.getpid(), signal.SIGTERM)

    threading.Thread(target=_kill, daemon=True, name="env-restart").start()
