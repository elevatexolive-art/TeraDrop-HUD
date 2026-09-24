from __future__ import annotations

import asyncio
import logging
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import urlsplit

from telegram import BotCommand, BotCommandScopeChat
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from app import runtime, storage, webproxy
from app.handlers import (
    auth_cmd,
    add_admin_cmd,
    addforcesub_cmd,
    addpremium_cmd,
    ban_cmd,
    broadcast_cmd,
    help_cmd,
    logs_cmd,
    maintenance_cmd,
    myplan_cmd,
    on_callback,
    on_photo,
    on_text,
    owner_cmd,
    premium_cmd,
    clearstartphoto_cmd,
    deleteplan_cmd,
    remove_admin_cmd,
    removeforcesub_cmd,
    removepremium_cmd,
    setcaption_cmd,
    setlimit_cmd,
    setplan_cmd,
    setstartphoto_cmd,
    setwelcome_cmd,
    start,
    stats_cmd,
    tglogin_cmd,
    tglogout_cmd,
    tgstatus_cmd,
    unauth_cmd,
    unban_cmd,
    users_cmd,
)
from app.settings import settings
from app.telegram_auth import telegram_auth

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("teradrop")


async def _post_init(application: Application) -> None:
    from app.http_client import get_client
    from app.job_queue import JOB_QUEUE

    runtime.application = application
    runtime.loop = asyncio.get_running_loop()
    storage.init()
    get_client()
    await JOB_QUEUE.start()
    await telegram_auth.initialize()
    telegram_auth.start_refresh_task()
    await sync_commands(application)


async def _post_shutdown(application: Application) -> None:
    from app.http_client import close_client
    from app.job_queue import JOB_QUEUE

    await JOB_QUEUE.stop()
    await telegram_auth.shutdown()
    await close_client()
    storage.close()
    runtime.application = None
    runtime.loop = None


async def sync_commands(application: Application) -> None:
    user_commands = [
        BotCommand("start", "ᴏᴘᴇɴ ᴛʜᴇ ʙᴏᴛ"),
        BotCommand("help", "sʜᴏᴡ ʜᴇʟᴘ"),
        BotCommand("premium", "ᴠɪᴇᴡ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴs"),
        BotCommand("myplan", "ᴠɪᴇᴡ ʏᴏᴜʀ ʟɪᴍɪᴛs"),
    ]
    admin_commands = user_commands + [
        BotCommand("owner", "ᴏᴘᴇɴ ᴄᴏɴᴛʀᴏʟ ᴘᴀɴᴇʟ"),
        BotCommand("stats", "ᴠɪᴇᴡ sᴛᴀᴛs"),
        BotCommand("users", "ʟɪsᴛ ᴜsᴇʀs"),
        BotCommand("logs", "ᴠɪᴇᴡ ʟᴏɢs"),
        BotCommand("addpremium", "ᴀᴅᴅ ᴀ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴ"),
        BotCommand("removepremium", "ʀᴇᴍᴏᴠᴇ ᴘʀᴇᴍɪᴜᴍ"),
        BotCommand("add_admin", "ᴀᴅᴅ ᴀɴ ᴀᴅᴍɪɴ"),
        BotCommand("remove_admin", "ʀᴇᴍᴏᴠᴇ ᴀɴ ᴀᴅᴍɪɴ"),
        BotCommand("addforcesub", "ᴀᴅᴅ ғᴏʀᴄᴇ-sᴜʙ"),
        BotCommand("removeforcesub", "ʀᴇᴍᴏᴠᴇ ғᴏʀᴄᴇ-sᴜʙ"),
        BotCommand("setstartphoto", "sᴇᴛ sᴛᴀʀᴛ ᴘʜᴏᴛᴏ"),
        BotCommand("clearstartphoto", "ᴄʟᴇᴀʀ sᴛᴀʀᴛ ᴘʜᴏᴛᴏ"),
        BotCommand("setplan", "ᴇᴅɪᴛ ᴀ ᴘʟᴀɴ"),
        BotCommand("deleteplan", "ʜɪᴅᴇ ᴀ ᴘʟᴀɴ"),
        BotCommand("maintenance", "ᴛᴏɢɢʟᴇ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ"),
        BotCommand("broadcast", "sᴇɴᴅ ᴀ ᴍᴇssᴀɢᴇ"),
        BotCommand("ban", "ʙᴀɴ ᴀ ᴜsᴇʀ"),
        BotCommand("unban", "ᴜɴʙᴀɴ ᴀ ᴜsᴇʀ"),
        BotCommand("auth", "ᴀᴜᴛʜᴏʀɪsᴇ ᴀ ᴜsᴇʀ"),
        BotCommand("unauth", "ʀᴇᴍᴏᴠᴇ ᴀᴜᴛʜᴏʀɪsᴀᴛɪᴏɴ"),
        BotCommand("setwelcome", "ᴇᴅɪᴛ ᴡᴇʟᴄᴏᴍᴇ"),
        BotCommand("setcaption", "ᴇᴅɪᴛ ᴄᴀᴘᴛɪᴏɴ"),
        BotCommand("setlimit", "ᴇᴅɪᴛ ᴜᴘʟᴏᴀᴅ ʟɪᴍɪᴛ"),
        BotCommand("tglogin", "ᴄᴏɴɴᴇᴄᴛ ᴍɪɴɪ ᴀᴘᴘ ᴀᴜᴛʜ"),
        BotCommand("tgstatus", "ᴄʜᴇᴄᴋ ᴍɪɴɪ ᴀᴘᴘ ᴀᴜᴛʜ"),
        BotCommand("tglogout", "ʀᴇᴍᴏᴠᴇ ᴍɪɴɪ ᴀᴘᴘ ᴀᴜᴛʜ"),
    ]
    await application.bot.set_my_commands(user_commands)
    for user_id in storage.admin_ids():
        try:
            await application.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(user_id))
        except Exception as exc:
            log.warning("could not register admin commands for %s: %s", user_id, type(exc).__name__)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlsplit(self.path)
        if parsed.path.startswith("/_cap/"):
            webproxy.serve_captcha_api(self, parsed)
            return
        if parsed.path == "/admin":
            webproxy.serve_admin_page(self)
            return
        if parsed.path.startswith("/admin/api/"):
            webproxy.serve_admin_api(self, parsed, "GET")
            return
        if parsed.path.startswith("/go/"):
            webproxy.serve_page(self, parsed)
            return
        if parsed.path.startswith("/media/"):
            webproxy.serve_media(self, parsed)
            return
        body = b'{"ok":true,"service":"teradrop"}'
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlsplit(self.path)
        if parsed.path.startswith("/_cap/"):
            webproxy.serve_captcha_api(self, parsed)
            return
        if parsed.path.startswith("/admin/api/"):
            webproxy.serve_admin_api(self, parsed, "POST")
            return
        self.send_response(404)
        self.end_headers()

    def do_HEAD(self) -> None:  # noqa: N802
        parsed = urlsplit(self.path)
        if parsed.path == "/admin":
            self.send_response(200)
            self.send_header("content-type", "text/html; charset=utf-8")
            self.end_headers()
            return
        if parsed.path.startswith("/media/"):
            webproxy.serve_media(self, parsed, head_only=True)
            return
        self.send_response(200)
        self.end_headers()

    def do_OPTIONS(self) -> None:  # noqa: N802
        parsed = urlsplit(self.path)
        if parsed.path.startswith("/media/") or parsed.path.startswith("/go/"):
            webproxy.serve_media_options(self)
            return
        self.send_response(204)
        self.end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def start_health() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", settings.health_port), HealthHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    log.info("health on %s", settings.health_port)


def validate_bot_api_url() -> None:
    """Fail early with a useful message when a private API hostname is unreachable."""
    raw = (settings.bot_api_url or "").strip()
    if not raw:
        return
    parsed = urlsplit(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise SystemExit(
            "BOT_API_URL is invalid. Use an HTTP URL such as "
            "http://telegram-bot-api:8081 or leave it empty for Telegram's hosted API."
        )
    try:
        socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise SystemExit(
            f"BOT_API_URL host '{parsed.hostname}' cannot be resolved from this deployment. "
            "Leave BOT_API_URL empty for the hosted Telegram API, or use the reachable "
            "private/public URL of a separately running local Bot API server."
        ) from exc


def build_app() -> Application:
    settings.ensure_dirs()
    storage.init()
    saved = storage.kv_get("welcome")
    if saved:
        settings.welcome_text = saved
    builder = (
        Application.builder()
        .token(settings.bot_token)
        .concurrent_updates(max(32, settings.max_concurrent * 8))
        .connection_pool_size(max(32, settings.max_concurrent * 8))
        .pool_timeout(30)
        .connect_timeout(20)
        .read_timeout(30)
        .write_timeout(30)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
    )
    if settings.bot_api_url:
        builder = builder.base_url(settings.telegram_api_root + "/bot").base_file_url(
            settings.telegram_api_root + "/file/bot"
        )
    app = builder.build()
    command_map = {
        "start": start,
        "help": help_cmd,
        "premium": premium_cmd,
        "myplan": myplan_cmd,
        "owner": owner_cmd,
        "tglogin": tglogin_cmd,
        "tgstatus": tgstatus_cmd,
        "tglogout": tglogout_cmd,
        "stats": stats_cmd,
        "users": users_cmd,
        "logs": logs_cmd,
        "ban": ban_cmd,
        "unban": unban_cmd,
        "auth": auth_cmd,
        "unauth": unauth_cmd,
        "maintenance": maintenance_cmd,
        "setwelcome": setwelcome_cmd,
        "setcaption": setcaption_cmd,
        "setlimit": setlimit_cmd,
        "broadcast": broadcast_cmd,
        "addpremium": addpremium_cmd,
        "removepremium": removepremium_cmd,
        "add_admin": add_admin_cmd,
        "remove_admin": remove_admin_cmd,
        "addforcesub": addforcesub_cmd,
        "removeforcesub": removeforcesub_cmd,
        "setstartphoto": setstartphoto_cmd,
        "clearstartphoto": clearstartphoto_cmd,
        "setplan": setplan_cmd,
        "deleteplan": deleteplan_cmd,
    }
    for name, handler in command_map.items():
        app.add_handler(CommandHandler(name, handler, block=False))
    app.add_handler(CallbackQueryHandler(on_callback, block=False))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo, block=False))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text, block=False))
    return app


def main() -> None:
    if not settings.bot_token:
        raise SystemExit("Set BOT_TOKEN as a secure environment variable before starting TeraDrop.")
    validate_bot_api_url()
    start_health()
    log.info(
        "starting %s; large uploads=%s; effective limit=%s MB",
        settings.bot_name,
        settings.bot_api_enabled,
        settings.effective_max_file_mb,
    )
    if settings.max_file_mb > settings.effective_max_file_mb and not settings.bot_api_enabled:
        log.warning(
            "MAX_FILE_MB=%s cannot be used with Telegram's hosted Bot API; "
            "set BOT_API_URL to a reachable local Bot API server for uploads above 49 MB",
            settings.max_file_mb,
        )
    application = build_app()
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
