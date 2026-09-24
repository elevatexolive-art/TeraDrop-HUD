from __future__ import annotations

import asyncio
import html
import json
import os
import re
import secrets
import shutil
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Awaitable, Callable

import httpx
from telegram import (
    BotCommand,
    BotCommandScopeChat,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from app import storage, texts
from app.domains import detect_links
from app.http_client import get_client
from app.job_queue import JOB_QUEUE, USER_GATE, priority_for, slot_limit_for
from app.payments import (
    cancel_verifier,
    make_order_id,
    notify_manual_activation,
    qr_image,
    start_verifier,
)
from app.progress import Meter, format_bytes, render
from app.resolver import FileInfo, resolve
from app.settings import settings
from app.telegram_auth import telegram_auth
from app.user_files import UserJobDir


CACHE_TTL_SECONDS = 30 * 60
ACTIVE_PANELS: dict[int, int] = {}
ACTIVE_USER_PANELS: dict[int, tuple[int, bool]] = {}
ADMIN_INPUTS: dict[int, str] = {}

BTN_PREMIUM = "premium plans"
BTN_HELP = "help"
BTN_MY_PLAN = "my plan"
BTN_ADMIN = "admin panel"


class CachedFile:
    def __init__(self, file: FileInfo, owner_id: int) -> None:
        self.file = file
        self.owner_id = owner_id
        self.expires_at = time.monotonic() + CACHE_TTL_SECONDS


CACHE: dict[str, CachedFile] = {}


def _escape(value: object) -> str:
    return html.escape(str(value or ""), quote=False)


async def _safe_edit(message, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
    try:
        if getattr(message, "photo", None):
            await message.edit_caption(
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
            )
        else:
            await message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    except Exception:
        # Telegram returns an error if an edit repeats the current content or
        # if a progress update races with a finished upload. The job itself
        # should not fail because a cosmetic update was rejected.
        pass


async def _edit_content(
    message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> bool:
    """Edit a text or photo message without creating a second navigation card."""
    try:
        if getattr(message, "photo", None):
            await message.edit_caption(
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
            )
        else:
            await message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        return True
    except Exception:
        return False


def _main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    buttons = [
        [
            KeyboardButton(BTN_PREMIUM, style="primary"),
            KeyboardButton(BTN_HELP, style="primary"),
        ],
        [KeyboardButton(BTN_MY_PLAN, style="success")],
    ]
    if storage.is_admin(user_id):
        buttons.append([KeyboardButton(BTN_ADMIN, style="danger")])
    return ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="choose an action",
    )


async def _edit_active_user_panel(
    bot,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> bool:
    panel = ACTIVE_USER_PANELS.get(chat_id)
    if not panel:
        return False
    message_id, is_photo = panel
    try:
        if is_photo:
            await bot.edit_message_caption(
                chat_id=chat_id,
                message_id=message_id,
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
            )
        else:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
            )
        return True
    except Exception:
        return False


def _allowed(user_id: int) -> tuple[bool, str | None]:
    if storage.kv_get("maintenance") == "on" or settings.maintenance:
        if not settings.is_owner(user_id):
            return False, texts.MAINTENANCE
    if storage.is_banned(user_id):
        return False, texts.BANNED
    bot_public = storage.kv_get("bot_public") or ("true" if settings.bot_public else "false")
    if bot_public == "true" or settings.is_owner(user_id) or storage.is_authorized(user_id):
        return True, None
    return False, texts.PRIVATE


def _require_admin(update: Update) -> bool:
    return bool(update.effective_user and storage.is_admin(update.effective_user.id))


async def _force_sub_status(bot, user_id: int) -> tuple[bool, list[dict[str, str]]]:
    missing: list[dict[str, str]] = []
    for channel in storage.list_force_subs():
        if not channel.get("invite_url"):
            invite = await _create_force_sub_invite(bot, channel["chat_id"])
            if invite:
                channel["invite_url"] = invite
                storage.add_force_sub(channel["chat_id"], invite)
        try:
            member = await bot.get_chat_member(channel["chat_id"], user_id)
            if member.status in {"left", "kicked"} or (
                member.status == "restricted" and not getattr(member, "is_member", False)
            ):
                missing.append(channel)
        except Exception:
            # A bot without channel access should not silently lock everyone out.
            storage.log("warn", f"could not check force-sub channel {channel['chat_id']}")
    return not missing, missing


async def _create_force_sub_invite(bot, chat_id: str) -> str:
    """Create a usable join URL when an admin stored only a channel id."""
    try:
        invite = await bot.create_chat_invite_link(
            chat_id=chat_id,
            name="TeraDrop force subscription",
        )
        if invite.invite_link:
            return str(invite.invite_link)
    except Exception:
        pass
    try:
        exported = await bot.export_chat_invite_link(chat_id)
        if exported:
            return str(exported)
    except Exception as exc:
        storage.log("warn", f"could not create force-sub invite for {chat_id}: {type(exc).__name__}")
    try:
        chat = await bot.get_chat(chat_id)
        username = getattr(chat, "username", "") or ""
        return f"https://t.me/{username}" if username else ""
    except Exception:
        return ""


async def _require_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not user:
        return False
    ok, missing = await _force_sub_status(context.bot, user.id)
    if ok:
        return True
    rows = []
    for index, item in enumerate(missing, 1):
        invite_url = item.get("invite_url") or ""
        if invite_url:
            rows.append([InlineKeyboardButton(f"join channel {index}", url=invite_url)])
        else:
            rows.append(
                [
                    InlineKeyboardButton(
                        f"open channel {index}",
                        url=f"https://t.me/{str(item['chat_id']).lstrip('@')}",
                    )
                ]
            )
    rows.append([InlineKeyboardButton("reload", callback_data="force:reload")])
    await update.effective_message.reply_text(
        "<b>🔒 ᴊᴏɪɴ ʀᴇǫᴜɪʀᴇᴅ</b>\n\n"
        "ᴊᴏɪɴ ᴛʜᴇ ᴄʜᴀɴɴᴇʟs ʙᴇʟᴏᴡ, ᴛʜᴇɴ ᴛᴀᴘ ʀᴇʟᴏᴀᴅ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(rows),
    )
    return False


def _upload_limit_mb() -> int:
    raw = storage.kv_get("limit")
    try:
        configured = int(raw) if raw else settings.max_file_mb
    except ValueError:
        configured = settings.max_file_mb
    return max(1, min(configured, settings.transport_max_file_mb))


def _can_upload(file: FileInfo) -> bool:
    return not file.size or file.size <= _upload_limit_mb() * 1024 * 1024


def resolve_cached_file(token: str) -> FileInfo | None:
    """Look up the FileInfo behind a public link token, used by the tiny
    webpage/proxy in app.webproxy so it can render a title and know which
    upstream URL to fetch without ever handing that URL to the browser."""
    item = CACHE.get(token)
    if not item or item.expires_at <= time.monotonic():
        return None
    return item.file


def resolve_redirect(token: str, kind: str) -> str | None:
    """Real upstream URL behind a token, for server-side use only (the
    proxy in app.webproxy fetches this itself — it is never sent to the
    browser)."""
    file = resolve_cached_file(token)
    if not file:
        return None
    if kind == "stream":
        return file.stream_hd_url or file.stream_url
    if kind == "direct":
        return file.direct_link
    return None


_PENDING_TASKS: set[asyncio.Task] = set()
_TG_LOGIN_STATES: dict[int, str] = {}


def _schedule_expiry_cleanup(msg, token: str, delay: float) -> None:
    """Deletes the 'file ready' message (with its stream/direct/send
    buttons) once our cached copy of the resolved TeraBox link would be
    considered stale, so users never see dead buttons."""

    async def _run() -> None:
        await asyncio.sleep(delay)
        if CACHE.pop(token, None) is not None:
            try:
                await msg.delete()
            except Exception:
                pass

    task = asyncio.create_task(_run())
    _PENDING_TASKS.add(task)
    task.add_done_callback(_PENDING_TASKS.discard)


def _public_link(token: str, kind: str) -> str | None:
    base = settings.public_base_url
    if not base:
        return None
    return f"{base}/go/{token}?t={kind}"


def _file_keyboard(file: FileInfo, token: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    top_row: list[InlineKeyboardButton] = []
    stream_target = file.stream_hd_url or file.stream_url
    if stream_target:
        hidden = _public_link(token, "stream")
        top_row.append(InlineKeyboardButton("stream", url=hidden or stream_target))
    if file.direct_link:
        hidden = _public_link(token, "direct")
        top_row.append(InlineKeyboardButton("direct", url=hidden or file.direct_link))
    if top_row:
        rows.append(top_row)

    if _can_upload(file):
        rows.append(
            [InlineKeyboardButton(f"send file · {file.formatted_size}", callback_data=f"dl:{token}")]
        )
    return InlineKeyboardMarkup(rows)


def _caption(file: FileInfo) -> str:
    tpl = storage.kv_get("caption") or settings.caption_template
    return (
        tpl.replace("{filename}", html.escape(file.file_name))
        .replace("{size}", html.escape(file.formatted_size))
        .replace("{url}", html.escape(file.direct_link or "", quote=True))
        .replace("{host}", "")
    )[:1024]


def _cache(file: FileInfo, owner_id: int) -> str:
    token = secrets.token_urlsafe(9)
    CACHE[token] = CachedFile(file, owner_id)
    if len(CACHE) > 800:
        now = time.monotonic()
        for key, item in list(CACHE.items()):
            if item.expires_at <= now:
                CACHE.pop(key, None)
    return token


def _cached(token: str, user_id: int) -> FileInfo | None:
    item = CACHE.get(token)
    if not item:
        return None
    if item.expires_at <= time.monotonic():
        CACHE.pop(token, None)
        return None
    if item.owner_id != user_id and not settings.is_owner(user_id):
        return None
    return item.file


def _admin_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("stats", callback_data="admin:stats"),
            InlineKeyboardButton("users", callback_data="admin:users"),
        ],
        [
            InlineKeyboardButton("logs", callback_data="admin:logs"),
            InlineKeyboardButton("settings", callback_data="admin:settings"),
        ],
        [
            InlineKeyboardButton("toggle maintenance", callback_data="admin:maintenance"),
            InlineKeyboardButton("refresh", callback_data="admin:home"),
        ],
        [
            InlineKeyboardButton("premium plans", callback_data="admin:plans"),
            InlineKeyboardButton("force-sub", callback_data="admin:forcesub"),
        ],
        [
            InlineKeyboardButton("environment", callback_data="admin:env"),
            InlineKeyboardButton("queue", callback_data="admin:queue"),
        ],
        [
            InlineKeyboardButton("start photo", callback_data="admin:startphoto"),
            InlineKeyboardButton("clear photo", callback_data="admin:clearphoto"),
        ],
    ]
    if settings.public_base_url:
        rows.append(
            [
                InlineKeyboardButton(
                    "open web admin",
                    url=f"{settings.public_base_url}/admin",
                )
            ]
        )
    return InlineKeyboardMarkup(
        rows
    )


def _admin_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("← admin home", callback_data="admin:home")]])


def _plans_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for plan in storage.list_plans(True):
        key = str(plan["key"])
        rows.append(
            [
                InlineKeyboardButton(f"edit {key}", callback_data=f"admin:plan_edit:{key}"),
                InlineKeyboardButton(f"delete {key}", callback_data=f"admin:plan_delete:{key}"),
            ]
        )
    rows.append([InlineKeyboardButton("add plan", callback_data="admin:plan_add")])
    rows.append([InlineKeyboardButton("← admin home", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def _premium_text(plans: list[dict] | None = None) -> str:
    plans = storage.list_plans(True) if plans is None else plans
    if not plans:
        return (
            "<b>premium plans</b>\n\n"
            "<blockquote>no plans are available right now. please check again later.</blockquote>"
        )
    details = "\n\n".join(
        (
            f"<b>{_escape(plan['label'])}</b>\n"
            f"<blockquote>price: <b>₹{_escape(plan['price'])}</b>\n"
            f"validity: <b>{_escape(plan['duration_days'])} days</b>\n"
            f"batch limit: <b>{_escape(plan['batch_limit'])} links</b>\n"
            f"total links: <b>{'unlimited' if not plan.get('total_links') else _escape(plan['total_links'])}</b></blockquote>"
        )
        for plan in plans
    )
    return (
        "<b>━━━━━━━━━━━━━━━━━━━━━\n"
        "premium plans\n"
        "━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        "<blockquote>choose a plan below to unlock higher limits and "
        "protected file delivery.</blockquote>\n\n"
        f"{details}\n\n"
        "select a plan to continue to payment."
    )


def _premium_keyboard(plans: list[dict] | None = None) -> InlineKeyboardMarkup:
    plans = storage.list_plans(True) if plans is None else plans
    rows = [
        [InlineKeyboardButton(f"{plan['label']} · ₹{plan['price']}", callback_data=f"buy:{plan['key']}")]
        for plan in plans
    ]
    return InlineKeyboardMarkup(rows or [[InlineKeyboardButton("refresh plans", callback_data="premium")]])


def _payment_text(plan: dict, order_id: str) -> str:
    total = "unlimited" if not plan.get("total_links") else str(plan["total_links"])
    return (
        "<b>━━━━━━━━━━━━━━━━━━━━━\n"
        "payment started\n"
        "━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        f"<blockquote><b>{_escape(plan['label'])}</b>\n"
        f"amount: <b>₹{_escape(plan['price'])}</b>\n"
        f"validity: <b>{_escape(plan['duration_days'])} days</b>\n"
        f"batch limit: <b>{_escape(plan['batch_limit'])} links</b>\n"
        f"total links: <b>{total}</b></blockquote>\n\n"
        f"order id: <code>{_escape(order_id)}</code>\n"
        "scan the qr code below with any upi app. payment verification is automatic.\n\n"
        "keep the qr message open until your plan is activated."
    )


def _payment_keyboard(order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("cancel payment", callback_data=f"paycancel:{order_id}")]]
    )


async def _admin_home(message) -> None:
    summary = storage.stats()
    previous = ACTIVE_PANELS.get(message.chat.id)
    user_id = message.from_user.id if message.from_user else message.chat.id
    saved = storage.kv_get(f"admin_panel:{user_id}")
    try:
        saved_panel = json.loads(saved) if saved else {}
        if saved_panel.get("chat_id") == message.chat.id:
            previous = int(saved_panel["message_id"])
    except (TypeError, ValueError, json.JSONDecodeError):
        pass
    if previous:
        try:
            await message.get_bot().delete_message(message.chat.id, previous)
        except Exception:
            pass
    panel = await message.reply_text(
        texts.ADMIN_PANEL.format(
            users=summary["users"],
            downloads=summary["downloads"],
            premium=summary["premium"],
            maintenance="on" if storage.kv_get("maintenance") == "on" else "off",
            queue=JOB_QUEUE.size(),
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=_admin_keyboard(),
    )
    ACTIVE_PANELS[message.chat.id] = panel.message_id
    storage.kv_set(
        f"admin_panel:{user_id}",
        json.dumps({"chat_id": message.chat.id, "message_id": panel.message_id}),
    )


async def _show_admin_detail(query, section: str) -> None:
    if section == "stats":
        s = storage.stats()
        text = (
            "<b>📊 ᴜsᴀɢᴇ sᴛᴀᴛs</b>\n\n"
            f"<blockquote>users: {s['users']}\n"
            f"completed downloads: {s['downloads']}\n"
            f"banned accounts: {s['bans']}</blockquote>"
        )
    elif section == "users":
        rows = storage.recent_users(18)
        text = "<b>👥 ʀᴇᴄᴇɴᴛ ᴜsᴇʀs</b>\n\n" + (_escape("\n".join(rows)) if rows else "no users yet.")
    elif section == "logs":
        rows = storage.recent_logs(16)
        text = "<b>🧾 ʀᴇᴄᴇɴᴛ ʟᴏɢs</b>\n\n" + (_escape("\n".join(rows)) if rows else "no errors recorded.")
    elif section == "plans":
        lines = []
        for plan in storage.list_plans(True):
            total = "unlimited" if not plan.get("total_links") else str(plan["total_links"])
            lines.append(
                f"<b>{_escape(plan['key'])}</b> · {_escape(plan['label'])} · ₹{plan['price']} · "
                f"{plan['duration_days']} days · batch {plan['batch_limit']} · total {total}"
            )
        text = (
            "<b>premium plans</b>\n\n"
            + ("\n".join(lines) if lines else "no active plans.")
            + "\n\nchoose edit, delete, or add plan below."
        )
    elif section == "forcesub":
        rows = storage.list_force_subs()
        text = "<b>force-sub channels</b>\n\n" + (
            _escape("\n".join(f"{r['chat_id']} · {r['invite_url']}" for r in rows))
            if rows
            else "no channels added."
        )
    elif section == "env":
        from app.env_manager import list_variables

        listing = list_variables(reveal=False)
        live = sum(1 for item in listing["variables"] if not item["restart"])
        restart = sum(1 for item in listing["variables"] if item["restart"])
        text = (
            "<b>environment</b>\n\n"
            f"<blockquote>file: {_escape(listing['file'])}\n"
            f"variables: {len(listing['variables'])}\n"
            f"live-apply: {live} · restart required: {restart}</blockquote>\n\n"
            "open the web control center to view, edit, or add values — including "
            "<code>BOT_TOKEN</code>. live keys apply without a reboot."
        )
        if settings.public_base_url:
            text += f"\n\n{settings.public_base_url}/admin"
    elif section == "queue":
        snap = JOB_QUEUE.snapshot()
        active = snap.get("active") or []
        lines = [
            f"queued: {snap['queued']}",
            f"workers: {snap['workers']}",
            f"completed: {snap['completed']} · failed: {snap['failed']}",
        ]
        if active:
            lines.append("")
            for job in active[:12]:
                lines.append(
                    f"u{job.get('user_id')} · {job.get('kind')} · worker {job.get('worker')}"
                )
        else:
            lines.append("\nno transfers in flight.")
        text = "<b>isolated job queue</b>\n\n<blockquote>" + _escape("\n".join(lines)) + "</blockquote>"
    else:
        api_state = "enabled · up to 2 gb" if settings.bot_api_enabled else "cloud api · 49 mb"
        text = (
            "<b>⚙ ʀᴜɴᴛɪᴍᴇ sᴇᴛᴛɪɴɢs</b>\n\n"
            f"<blockquote>upload transport: {api_state}\n"
            f"effective upload limit: {_upload_limit_mb()} mb\n"
            f"download workers: {settings.max_concurrent}\n"
            f"health port: {settings.health_port}</blockquote>\n\n"
            "use /setlimit &lt;mb&gt; to change the configured ceiling."
        )
    markup = _plans_keyboard() if section == "plans" else _admin_back_keyboard()
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)


async def _handle_admin_callback(query, action: str) -> None:
    if action == "home":
        summary = storage.stats()
        await query.edit_message_text(
            texts.ADMIN_PANEL.format(
                users=summary["users"],
                downloads=summary["downloads"],
                premium=summary["premium"],
                maintenance="on" if storage.kv_get("maintenance") == "on" else "off",
                queue=JOB_QUEUE.size(),
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=_admin_keyboard(),
        )
    elif action == "maintenance":
        current = storage.kv_get("maintenance") == "on"
        storage.kv_set("maintenance", "off" if current else "on")
        await _handle_admin_callback(query, "home")
    elif action == "plans":
        ADMIN_INPUTS.pop(query.from_user.id, None)
        await _show_admin_detail(query, "plans")
    elif action == "plan_add":
        ADMIN_INPUTS[query.from_user.id] = "plan:add"
        await query.edit_message_text(
            "<b>add premium plan</b>\n\n"
            "send one line in this format:\n"
            "<code>key | name | short name | price | days | batch limit | total links</code>\n\n"
            "use <code>0</code> for unlimited total links.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("cancel", callback_data="admin:plans")]]
            ),
        )
    elif action.startswith("plan_edit:"):
        key = action.split(":", 1)[1]
        plan = storage.get_plan(key)
        if not plan:
            await _show_admin_detail(query, "plans")
            return
        ADMIN_INPUTS[query.from_user.id] = f"plan:edit:{key}"
        await query.edit_message_text(
            f"<b>edit { _escape(plan['label']) }</b>\n\n"
            "send the complete updated plan in this format:\n"
            "<code>key | name | short name | price | days | batch limit | total links</code>\n\n"
            "use <code>0</code> for unlimited total links.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("cancel", callback_data="admin:plans")]]
            ),
        )
    elif action.startswith("plan_delete:"):
        key = action.split(":", 1)[1]
        plan = storage.get_plan(key)
        label = _escape(plan["label"]) if plan else key
        await query.edit_message_text(
            f"<b>delete {label}?</b>\n\n"
            "this hides the plan from new purchases. existing subscriptions are not changed.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("delete plan", callback_data=f"admin:plan_delete_confirm:{key}"),
                        InlineKeyboardButton("keep plan", callback_data="admin:plans"),
                    ]
                ]
            ),
        )
    elif action.startswith("plan_delete_confirm:"):
        key = action.split(":", 1)[1]
        storage.delete_plan(key)
        await _show_admin_detail(query, "plans")
    elif action == "forcesub":
        ADMIN_INPUTS[query.from_user.id] = "forcesub"
        await _show_admin_detail(query, "forcesub")
        await query.message.reply_text(
            "ᴜsᴇ <code>/addforcesub channel invite_url</code> ᴏʀ "
            "<code>/removeforcesub channel</code>.",
            parse_mode=ParseMode.HTML,
        )
    elif action == "startphoto":
        ADMIN_INPUTS[query.from_user.id] = "startphoto"
        await query.message.reply_text(
            "sᴇɴᴅ ᴛʜᴇ ɴᴇᴡ sᴛᴀʀᴛ ᴘʜᴏᴛᴏ ɴᴏᴡ. ᴛʜᴇ ᴘʜᴏᴛᴏ ᴡɪʟʟ ʙᴇ ᴜsᴇᴅ ᴡɪᴛʜ /start.",
            parse_mode=ParseMode.HTML,
        )
    elif action == "clearphoto":
        storage.kv_delete("start_photo")
        await _handle_admin_callback(query, "home")
    else:
        await _show_admin_detail(query, action)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user:
        storage.touch_user(user.id, user.username, user.first_name)
    ok, reason = _allowed(user.id if user else 0)
    if not ok and reason:
        await update.message.reply_text(reason, parse_mode=ParseMode.HTML)
        return
    if not await _require_membership(update, context):
        return
    mention = user.mention_html() if user else "there"
    body = texts.welcome(mention)
    photo_id = storage.kv_get("start_photo")
    main_keyboard = _main_keyboard(user.id if user else 0)
    if photo_id:
        panel = await update.message.reply_photo(
            photo=photo_id,
            caption=body,
            parse_mode=ParseMode.HTML,
            reply_markup=main_keyboard,
        )
    else:
        panel = await update.message.reply_text(
            body,
            parse_mode=ParseMode.HTML,
            reply_markup=main_keyboard,
        )
    if panel:
        ACTIVE_USER_PANELS[panel.chat.id] = (panel.message_id, bool(panel.photo))


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if update.callback_query:
        await _edit_content(message, texts.HELP)
        return
    if message and await _edit_active_user_panel(context.bot, message.chat.id, texts.HELP):
        return
    await message.reply_text(texts.HELP, parse_mode=ParseMode.HTML)


async def myplan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    access = storage.entitlement(update.effective_user.id)
    if access["premium"]:
        expiry = access["expires_at"].astimezone(timezone.utc).strftime("%d %b %Y, %I:%M %p UTC")
        remaining = "unlimited" if access["remaining_links"] is None else str(access["remaining_links"])
        text = (
            f"<b>💎 ʏᴏᴜʀ {access['plan']['label']}</b>\n\n"
            f"ʙᴀᴛᴄʜ ʟɪᴍɪᴛ: <b>{access['batch_limit']}</b> ʟɪɴᴋs\n"
            f"ʀᴇᴍᴀɪɴɪɴɢ ʟɪɴᴋs: <b>{remaining}</b>\n"
            f"ᴇxᴘɪʀᴇs: <code>{expiry}</code>"
        )
    else:
        text = (
            "<b>🆓 ғʀᴇᴇ ᴘʟᴀɴ</b>\n\n"
            f"ʟɪɴᴋs ʟᴇғᴛ ɪɴ 24 ʜᴏᴜʀs: <b>{access['remaining_links']}</b>\n"
            f"sᴇɴᴅ ғɪʟᴇ ᴛᴏ ᴛᴇʟᴇɢʀᴀᴍ ʟᴇғᴛ: <b>{access['send_file_remaining']}</b>\n"
            "ᴜᴘɢʀᴀᴅᴇ ᴛᴏ ʀᴇᴍᴏᴠᴇ ᴛʜᴇsᴇ ʟɪᴍɪᴛs."
        )
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("upgrade", callback_data="premium")]])
    if update.callback_query:
        await _edit_content(update.effective_message, text, markup)
    elif not await _edit_active_user_panel(context.bot, update.effective_chat.id, text, markup):
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)


async def premium_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    plans = storage.list_plans(True)
    text = _premium_text(plans)
    markup = _premium_keyboard(plans)
    message = update.effective_message
    if update.callback_query:
        await _edit_content(message, text, markup)
        return
    if message and await _edit_active_user_panel(context.bot, message.chat.id, text, markup):
        return
    await message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)


async def owner_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _require_owner(update):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    await _admin_home(update.message)


async def tglogin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _require_owner(update):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    if update.effective_chat.type != "private":
        await update.message.reply_text("Use /tglogin in the bot's private chat.")
        return
    _TG_LOGIN_STATES[update.effective_user.id] = "phone"
    await update.message.reply_text(
        "Send the Telegram phone number in international format.\n"
        "Your next message will be deleted immediately after it is received.",
    )


async def tgstatus_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _require_owner(update):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    state = await telegram_auth.status()
    services = "\n".join(f"{name}: {value}" for name, value in state["services"].items())
    await update.message.reply_text(
        "<b>Telegram auth</b>\n"
        f"session: {'connected' if state['authorized'] else 'not connected'}\n"
        f"{_escape(services)}",
        parse_mode=ParseMode.HTML,
    )


async def tglogout_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _require_owner(update):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    _TG_LOGIN_STATES.pop(update.effective_user.id, None)
    await telegram_auth.logout()
    await update.message.reply_text("Telegram user session removed and cached WebApp auth cleared.")


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.text:
        return
    user = update.effective_user
    if user and _require_owner(update) and message.chat.type == "private":
        state = _TG_LOGIN_STATES.get(user.id)
        if state:
            await _handle_telegram_login_input(message, user.id, state)
            return
    if user and storage.is_admin(user.id) and ADMIN_INPUTS.get(user.id):
        if await _handle_admin_input(message, user.id, context.bot):
            return
    action = message.text.strip().casefold()
    if action == BTN_PREMIUM:
        await premium_cmd(update, context)
        return
    if action == BTN_HELP:
        await help_cmd(update, context)
        return
    if action == BTN_MY_PLAN:
        await myplan_cmd(update, context)
        return
    if action == BTN_ADMIN:
        if _require_owner(update):
            await _admin_home(message)
        else:
            await message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    storage.touch_user(user.id, user.username, user.first_name)
    ok, reason = _allowed(user.id)
    if not ok:
        await message.reply_text(reason or texts.PRIVATE, parse_mode=ParseMode.HTML)
        return
    if not await _require_membership(update, context):
        return

    found = detect_links(message.text)
    if not found:
        if message.chat.type == "private":
            await message.reply_text(texts.NO_LINK, parse_mode=ParseMode.HTML)
        return
    access = storage.entitlement(user.id)
    slots = slot_limit_for(access)
    if not await USER_GATE.try_enter(user.id, slots):
        await message.reply_text(
            "<b>⏳ ʏᴏᴜʀ ᴘʀᴇᴠɪᴏᴜs ʀᴇǫᴜᴇsᴛ ɪs sᴛɪʟʟ ʀᴜɴɴɪɴɢ</b>\n\n"
            "ᴡᴀɪᴛ ᴜɴᴛɪʟ ɪᴛ ᴄᴏᴍᴘʟᴇᴛᴇs, ᴏʀ ᴜsᴇ ᴀ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴ ꜰᴏʀ ʜɪɢʜᴇʀ ᴄᴏɴᴄᴜʀʀᴇɴᴄʏ.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("💎 ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ", callback_data="premium")]]
            ),
        )
        return
    allowed_count = max(1, access["batch_limit"])
    selected = found[:allowed_count]
    if len(found) > allowed_count:
        await message.reply_text(
            f"<b>ℹ️ ᴏɴʟʏ {allowed_count} ʟɪɴᴋs ᴄᴀɴ ʙᴇ ᴘʀᴏᴄᴇssᴇᴅ ᴀᴛ ᴏɴᴄᴇ ᴏɴ ʏᴏᴜʀ ᴄᴜʀʀᴇɴᴛ ᴘʟᴀɴ.</b>\n\n"
            "ᴛʜᴇ ʀᴇsᴛ ᴡᴇʀᴇ ɪɢɴᴏʀᴇᴅ. ᴡᴀɪᴛ ꜰᴏʀ ᴛʜɪs ʀᴇǫᴜᴇsᴛ ᴛᴏ ғɪɴɪsʜ ᴏʀ ᴜᴘɢʀᴀᴅᴇ ᴛᴏ ᴘʀᴏᴄᴇss ᴍᴏʀᴇ ᴀᴛ ᴏɴᴄᴇ.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("💎 ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ", callback_data="premium")]]
            ),
        )
    if len(selected) == 1 and not access["premium"] and len(found) > 1:
        await message.reply_text(
            "<b>ℹ️ ʏᴏᴜʀ ғʀᴇᴇ ᴘʟᴀɴ ᴘʀᴏᴄᴇssᴇs ᴏɴᴇ ʟɪɴᴋ ᴀᴛ ᴀ ᴛɪᴍᴇ.</b>\n"
            "ᴏɴʟʏ ᴛʜᴇ ғɪʀsᴛ ʟɪɴᴋ ᴡɪʟʟ ʙᴇ ᴘʀᴏᴄᴇssᴇᴅ; ᴛʜᴇ ʀᴇsᴛ ᴡᴇʀᴇ ʀᴇᴊᴇᴄᴛᴇᴅ.\n\n"
            "ᴜᴘɢʀᴀᴅ ᴛᴏ ᴘʀᴇᴍɪᴜᴍ ᴛᴏ ᴘʀᴏᴄᴇss ᴍᴜʟᴛɪᴘʟᴇ ʟɪɴᴋs ᴛᴏɢᴇᴛʜᴇʀ.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("💎 ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ", callback_data="premium")]]
            ),
        )
    if not selected:
        return
    if not storage.try_reserve_links(user.id, len(selected))[0]:
        await message.reply_text(
            "<b>🛑 ʏᴏᴜʀ ғʀᴇᴇ ʟɪɴᴋ ʟɪᴍɪᴛ ɪs ᴜsᴇᴅ ᴜᴘ</b>\n\n"
            "ʏᴏᴜ ᴄᴀɴ ᴘʀᴏᴄᴇss ᴍᴏʀᴇ ʟɪɴᴋs ᴀғᴛᴇʀ 24 ʜᴏᴜʀs ᴏʀ ᴜᴘɢʀᴀᴅᴇ ɴᴏᴡ.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("💎 ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ", callback_data="premium")]]
            ),
        )
        return
    if not access["premium"]:
        pass
    try:
        await asyncio.gather(
            *(
                process_link(message, item["url"].strip().replace("\n", "").replace("\r", ""), item, user.id, access)
                for item in selected
            )
        )
    finally:
        await USER_GATE.exit(user.id)


async def _delete_sensitive_message(message) -> None:
    try:
        await message.delete()
    except Exception:
        pass


async def _handle_telegram_login_input(message, user_id: int, state: str) -> None:
    value = (message.text or "").strip()
    await _delete_sensitive_message(message)
    try:
        if state == "phone":
            reply = await telegram_auth.start_login(value)
            _TG_LOGIN_STATES[user_id] = "code"
        elif state == "code":
            reply = await telegram_auth.submit_code(value)
            if "2-step" in reply:
                _TG_LOGIN_STATES[user_id] = "password"
            else:
                _TG_LOGIN_STATES.pop(user_id, None)
        else:
            reply = await telegram_auth.submit_password(value)
            _TG_LOGIN_STATES.pop(user_id, None)
    except Exception as exc:
        _TG_LOGIN_STATES.pop(user_id, None)
        reply = f"Telegram login failed: {_escape(str(exc))}"
    await message.reply_text(reply, parse_mode=ParseMode.HTML)


async def process_link(
    message,
    url: str,
    meta: dict,
    owner_id: int,
    access: dict,
) -> None:
    status = await message.reply_text(texts.DETECTING, parse_mode=ParseMode.HTML)
    await _safe_edit(
        status,
        texts.ANALYSING.format(
            domain=_escape(meta.get("host") or "terabox"),
            surl=_escape(meta.get("surl") or "unknown"),
        ),
    )
    await _safe_edit(status, texts.RETRIEVING)
    result = None
    last_exc: Exception | None = None

    async def resolve_with_retries():
        nonlocal last_exc
        attempts = 3
        output = None
        for attempt in range(1, attempts + 1):
            try:
                output = await resolve(url)
                last_exc = None
                if output.ok:
                    return output
            except Exception as exc:
                last_exc = exc
                output = None
            if attempt < attempts:
                await asyncio.sleep(2.5)
        return output

    try:
        result = await JOB_QUEUE.submit(
            priority_for(access),
            resolve_with_retries,
            user_id=owner_id,
            kind="resolve",
        )
    except Exception as exc:
        last_exc = exc
    if last_exc is not None:
        storage.log("error", str(last_exc))
        await _safe_edit(status, texts.FAILED.format(reason=_escape(last_exc)))
        return
    if result is None or not result.ok:
        reason = result.message if result else "unknown error"
        storage.log("warn", reason)
        await _safe_edit(status, texts.FAILED.format(reason=_escape(reason)))
        return
    await _safe_edit(status, texts.RESOLVING)
    file = result.files[0]
    kind = (
        "ғᴏʟᴅᴇʀ"
        if len(result.files) > 1
        else ("ᴠɪᴅᴇᴏ" if file.file_name.lower().endswith((".mp4", ".mkv", ".mov", ".webm")) else "ғɪʟᴇ")
    )
    if len(result.files) > 1:
        buttons: list[list[InlineKeyboardButton]] = []
        for item in result.files[:40]:
            token = _cache(item, owner_id)
            buttons.append(
                [
                    InlineKeyboardButton(
                        f"{item.file_name[:38]} · {item.formatted_size}",
                        callback_data=f"pick:{token}",
                    )
                ]
            )
        body = texts.FOLDER.format(
            title=_escape(result.title),
            count=len(result.files),
            size=_escape(format_bytes(sum(item.size for item in result.files))),
        )
        await _safe_edit(status, body, InlineKeyboardMarkup(buttons))
        return

    token = _cache(file, owner_id)
    body = texts.READY.format(
        filename=_escape(file.file_name),
        size=_escape(file.formatted_size),
        kind=kind,
    )
    if not _can_upload(file):
        if settings.bot_api_enabled:
            body += "\n\n<i>send file is above the configured owner limit.</i>"
        else:
            body += "\n\n" + texts.LARGE_UPLOAD_UNAVAILABLE
    await _safe_edit(status, body, _file_keyboard(file, token))
    _schedule_expiry_cleanup(status, token, CACHE_TTL_SECONDS)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()
    user = update.effective_user
    if query.data in {"premium", "help"}:
        if query.data == "premium":
            await premium_cmd(update, context)
        else:
            await help_cmd(update, context)
        return
    if query.data == "force:reload":
        if await _require_membership(update, context):
            await _edit_content(
                query.message,
                "<b>✅ ᴍᴇᴍʙᴇʀsʜɪᴘ ᴠᴇʀɪꜰɪᴇᴅ</b>\n\nsᴇɴᴅ ʏᴏᴜʀ ʟɪɴᴋ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ.",
            )
        return
    if query.data.startswith("admin:"):
        if not _require_owner(update):
            await query.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
            return
        await _handle_admin_callback(query, query.data.split(":", 1)[1])
        return
    if query.data.startswith("buy:"):
        plan_key = query.data.split(":", 1)[1]
        plan = storage.get_plan(plan_key)
        if not plan:
            await query.message.reply_text("ᴛʜɪs ᴘʟᴀɴ ɪs ɴᴏ ʟᴏɴɢᴇʀ ᴀᴠᴀɪʟᴀʙʟᴇ.")
            return
        order_id = make_order_id(user.id)
        storage.create_order(
            {
                "order_id": order_id,
                "user_id": user.id,
                "plan_key": plan_key,
                "amount": float(plan["price"]),
                "days": int(plan["duration_days"]),
                "status": "pending",
                "created_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc)
                + timedelta(minutes=settings.payment_max_minutes),
                "source_chat_id": query.message.chat.id,
                "source_message_id": query.message.message_id,
                "source_is_photo": bool(query.message.photo),
            }
        )
        await _edit_content(
            query.message,
            _payment_text(plan, order_id),
            _payment_keyboard(order_id),
        )
        qr = await query.message.reply_photo(
            photo=qr_image(order_id, float(plan["price"])),
            caption=_payment_text(plan, order_id),
            parse_mode=ParseMode.HTML,
            reply_markup=_payment_keyboard(order_id),
        )
        start_verifier(context.bot, order_id, qr)
        return
    if query.data.startswith("paycancel:"):
        order_id = query.data.split(":", 1)[1]
        order = storage.get_order(order_id)
        if not order or int(order.get("user_id", 0)) != user.id:
            await query.answer("this payment session is not yours", show_alert=True)
            return
        storage.update_order_status(order_id, "cancelled")
        cancel_verifier(order_id)
        try:
            await query.message.delete()
        except Exception:
            pass
        restored = False
        if order.get("source_chat_id") and order.get("source_message_id"):
            if order.get("source_is_photo"):
                try:
                    await context.bot.edit_message_caption(
                        chat_id=order["source_chat_id"],
                        message_id=order["source_message_id"],
                        caption=_premium_text(),
                        parse_mode=ParseMode.HTML,
                        reply_markup=_premium_keyboard(),
                    )
                    restored = True
                except Exception:
                    pass
            else:
                restored = await _edit_active_user_panel(
                    context.bot,
                    int(order["source_chat_id"]),
                    _premium_text(),
                    _premium_keyboard(),
                )
                if not restored:
                    try:
                        await context.bot.edit_message_text(
                            chat_id=order["source_chat_id"],
                            message_id=order["source_message_id"],
                            text=_premium_text(),
                            parse_mode=ParseMode.HTML,
                            reply_markup=_premium_keyboard(),
                        )
                        restored = True
                    except Exception:
                        pass
        if not restored:
            await query.message.chat.send_message(
                _premium_text(),
                parse_mode=ParseMode.HTML,
                reply_markup=_premium_keyboard(),
            )
        return

    ok, reason = _allowed(user.id)
    if not ok:
        await query.message.reply_text(reason or texts.PRIVATE, parse_mode=ParseMode.HTML)
        return
    if not await _require_membership(update, context):
        return
    data = query.data
    if data.startswith("pick:"):
        file = _cached(data.split(":", 1)[1], user.id)
        if not file:
            await query.message.reply_text(
                "that file selection expired. send the link again.",
                parse_mode=ParseMode.HTML,
            )
            return
        new_token = _cache(file, user.id)
        sent = await query.message.reply_text(
            texts.READY.format(
                filename=_escape(file.file_name),
                size=_escape(file.formatted_size),
                kind="ғɪʟᴇ",
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=_file_keyboard(file, new_token),
        )
        _schedule_expiry_cleanup(sent, new_token, CACHE_TTL_SECONDS)
        return
    if data.startswith("dl:"):
        file = _cached(data.split(":", 1)[1], user.id)
        if not file:
            await query.message.reply_text(
                "that download expired. send the link again.",
                parse_mode=ParseMode.HTML,
            )
            return
        await download_and_send(query.message, file, user.id, context.bot)


async def download_and_send(message, file: FileInfo, user_id: int, bot) -> None:
    if not file.direct_link and not file.stream_url:
        await message.reply_text("no download URL was returned for this file.")
        return
    limit = _upload_limit_mb()
    limit_bytes = limit * 1024 * 1024
    if file.size and file.size > limit_bytes:
        await message.reply_text(
            _too_large_text(file, limit),
            parse_mode=ParseMode.HTML,
            reply_markup=_file_keyboard(file, _cache(file, user_id)),
        )
        return
    can_send, access = storage.reserve_send_file(user_id)
    if not can_send:
        await message.reply_text(
            "<b>🛑 ғʀᴇᴇ sᴇɴᴅ-ғɪʟᴇ ʟɪᴍɪᴛ ʀᴇᴀᴄʜᴇᴅ</b>\n\n"
            "ʏᴏᴜ ʜᴀᴠᴇ ᴜsᴇᴅ ʏᴏᴜʀ 5 ʟɪғᴇᴛɪᴍᴇ sᴇɴᴅ-ғɪʟᴇ ᴄʀᴇᴅɪᴛs. "
            "ᴜᴘɢʀᴀᴅ ᴛᴏ ᴘʀᴇᴍɪᴜᴍ ᴛᴏ ᴇɴᴀʙʟᴇ sᴇɴᴅ-ғɪʟᴇ ᴀɴᴅ ᴄᴏᴘʏ/ғᴏʀᴡᴀʀᴅ.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("💎 ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ", callback_data="premium")]]
            ),
        )
        return

    url = file.direct_link or file.stream_url
    job_dir = UserJobDir(user_id)

    async def run_download():
        status = await message.reply_text(
            render("download", _escape(file.file_name), 0, file.size, 0, 0),
            parse_mode=ParseMode.HTML,
        )
        dest = job_dir.path_for(file.file_name)
        try:
            await _download_file(status, url or "", dest, file)
            if file.file_name.lower().endswith((".mp4", ".mov", ".m4v")):
                await _safe_edit(status, f"optimizing <b>{_escape(file.file_name)}</b> for streaming…")
                await _remux_faststart(status, dest, file)
            size = dest.stat().st_size if dest.exists() else file.size
            if size > limit_bytes:
                await _safe_edit(
                    status,
                    _too_large_text(file, limit, actual_size=size),
                    _file_keyboard(file, _cache(file, user_id)),
                )
                return
            await message.chat.send_action(
                ChatAction.UPLOAD_VIDEO
                if file.file_name.lower().endswith((".mp4", ".mov", ".webm"))
                else ChatAction.UPLOAD_DOCUMENT
            )
            await _safe_edit(status, render("upload", _escape(file.file_name), 0, size, 0, 0))
            sent_message_id = await _upload_to_telegram(
                status,
                message.chat.id,
                dest,
                file,
                size,
                protect_content=not access["premium"],
            )
            storage.bump_download(user_id)
            asyncio.create_task(_delete_message_later(bot, message.chat.id, sent_message_id))
            for stale in (status, message):
                try:
                    await stale.delete()
                except Exception:
                    pass
        except Exception as exc:
            storage.log("error", str(exc))
            await _safe_edit(status, texts.FAILED.format(reason=_escape(exc)))
        finally:
            job_dir.cleanup()

    await JOB_QUEUE.submit(priority_for(access), run_download, user_id=user_id, kind="transfer")


def _too_large_text(file: FileInfo, limit: int, actual_size: int | None = None) -> str:
    size = format_bytes(actual_size) if actual_size else file.formatted_size
    if settings.bot_api_enabled:
        hint = "lower the owner limit with /setlimit or use stream/direct."
    else:
        hint = (
            "stream or direct are ready below. to send larger files in chat, "
            "run a local telegram bot api server and set <code>BOT_API_URL</code>."
        )
    return texts.TOO_LARGE.format(size=_escape(size), limit=limit, hint=hint)


_DL_HEADERS = {
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "referer": "https://www.teraboxdl.site/",
}
PROGRESS_EDIT_INTERVAL = 7.0
PARALLEL_SEGMENTS = 6
PARALLEL_MIN_BYTES = 12 * 1024 * 1024


def _headers_for_file(file: FileInfo, extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = dict(_DL_HEADERS)
    for key, value in (file.request_headers or {}).items():
        if value:
            headers[str(key).lower()] = str(value)
    if extra:
        headers.update(extra)
    return headers


async def _probe_range_support(client: httpx.AsyncClient, url: str, headers: dict[str, str]) -> int:
    try:
        probe = {**headers, "range": "bytes=0-0"}
        async with client.stream("GET", url, headers=probe) as res:
            if res.status_code != 206:
                return 0
            content_range = res.headers.get("content-range", "")
            total = int(content_range.split("/")[-1]) if "/" in content_range else 0
            return total
    except Exception:
        return 0


async def _download_file(status, url: str, dest: Path, file: FileInfo) -> None:
    meter = Meter()
    last_edit = [0.0]
    lock = asyncio.Lock()
    done_ref = [0]
    headers = _headers_for_file(file)

    async def report(total: int) -> None:
        now = time.monotonic()
        if now - last_edit[0] < PROGRESS_EDIT_INTERVAL and done_ref[0] < total:
            return
        last_edit[0] = now
        speed, elapsed = meter.update(done_ref[0])
        await _safe_edit(
            status,
            render("download", _escape(file.file_name), done_ref[0], total or done_ref[0], speed, elapsed),
        )

    client = get_client()
    total = await _probe_range_support(client, url, headers)
    if total >= PARALLEL_MIN_BYTES:
        try:
            await _download_parallel(client, url, dest, total, lock, done_ref, report, headers)
            return
        except Exception:
            done_ref[0] = 0
            meter.reset()
            dest.unlink(missing_ok=True)

    async with client.stream("GET", url, headers=headers) as res:
        res.raise_for_status()
        total = int(res.headers.get("content-length") or file.size or 0)
        dest.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(dest), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            async for chunk in res.aiter_bytes(256 * 1024):
                await asyncio.to_thread(os.write, fd, chunk)
                done_ref[0] += len(chunk)
                await report(total)
        finally:
            os.close(fd)


async def _download_parallel(
    client: httpx.AsyncClient,
    url: str,
    dest: Path,
    total: int,
    lock: asyncio.Lock,
    done_ref: list[int],
    report: Callable[[int], Awaitable[None]],
    headers: dict[str, str],
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(dest), os.O_RDWR | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.ftruncate(fd, total)
        segment_size = -(-total // PARALLEL_SEGMENTS)
        ranges: list[tuple[int, int]] = []
        start = 0
        while start < total:
            end = min(start + segment_size, total) - 1
            ranges.append((start, end))
            start = end + 1

        async def fetch(rng: tuple[int, int]) -> None:
            seg_start, seg_end = rng
            req_headers = {**headers, "range": f"bytes={seg_start}-{seg_end}"}
            async with client.stream("GET", url, headers=req_headers) as res:
                res.raise_for_status()
                offset = seg_start
                async for chunk in res.aiter_bytes(256 * 1024):
                    await asyncio.to_thread(os.pwrite, fd, chunk, offset)
                    offset += len(chunk)
                    async with lock:
                        done_ref[0] += len(chunk)
                    await report(total)

        await asyncio.gather(*(fetch(r) for r in ranges))
    finally:
        os.close(fd)

class _MultipartUpload(httpx.AsyncByteStream):
    def __init__(
        self,
        fields: dict[str, str],
        file_field: str,
        file_path: Path,
        filename: str,
        content_type: str,
        on_progress: Callable[[int], Awaitable[None]],
        thumbnail: bytes | None = None,
    ) -> None:
        self.boundary = f"----teradrop-{secrets.token_hex(12)}"
        self.file_path = file_path
        self.on_progress = on_progress
        self.sent = 0
        self.file_size = file_path.stat().st_size
        prefix = b"".join(self._field_part(name, value) for name, value in fields.items())
        if thumbnail:
            prefix += self._file_prefix("thumbnail", "thumb.jpg", "image/jpeg") + thumbnail + b"\r\n"
        self.prefix = prefix + self._file_prefix(file_field, filename, content_type)
        self.suffix = f"\r\n--{self.boundary}--\r\n".encode()
        self.content_length = len(self.prefix) + self.file_size + len(self.suffix)

    def _field_part(self, name: str, value: str) -> bytes:
        return (
            f"--{self.boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        ).encode()

    def _file_prefix(self, field: str, filename: str, content_type: str) -> bytes:
        clean_name = filename.replace("\\", "_").replace('"', "'")
        return (
            f"--{self.boundary}\r\n"
            f'Content-Disposition: form-data; name="{field}"; filename="{clean_name}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode()

    async def __aiter__(self):
        yield self.prefix
        with self.file_path.open("rb") as handle:
            while True:
                chunk = await asyncio.to_thread(handle.read, 256 * 1024)
                if not chunk:
                    break
                self.sent += len(chunk)
                yield chunk
                await self.on_progress(self.sent)
        yield self.suffix

    async def aclose(self) -> None:
        return


async def _fetch_thumbnail(url: str | None) -> bytes | None:
    if not url:
        return None
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=8.0)) as client:
            res = await client.get(url)
            res.raise_for_status()
            data = res.content
            return data[: 200 * 1024] if data else None
    except Exception:
        return None

async def _make_thumbnail(path: Path) -> bytes | None:
    """Extract a small JPEG thumbnail from a local video with ffmpeg."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None
    out = path.with_suffix(".thumb.jpg")
    try:
        proc = await asyncio.create_subprocess_exec(
            ffmpeg, "-y", "-ss", "1", "-i", str(path),
            "-vframes", "1", "-vf", "scale=320:-2",
            "-q:v", "5", str(out),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=15)
        if out.exists() and out.stat().st_size > 0:
            data = out.read_bytes()
            return data[:200 * 1024]  # Telegram thumbnail limit
    except Exception:
        return None
    finally:
        try:
            out.unlink(missing_ok=True)
        except Exception:
            pass
    return None

async def _remux_faststart(status, dest: Path, file: FileInfo) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return
    tmp_out = dest.with_suffix(dest.suffix + ".faststart.mp4")
    try:
        proc = await asyncio.create_subprocess_exec(
            ffmpeg,
            "-y",
            "-i",
            str(dest),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(tmp_out),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=180)
        if proc.returncode == 0 and tmp_out.exists() and tmp_out.stat().st_size > 0:
            tmp_out.replace(dest)
        else:
            tmp_out.unlink(missing_ok=True)
    except Exception:
        tmp_out.unlink(missing_ok=True)


async def _upload_to_telegram(
    status,
    chat_id: int,
    path: Path,
    file: FileInfo,
    size: int,
    protect_content: bool = True,
) -> int:
    is_video = file.file_name.lower().endswith((".mp4", ".mov", ".webm", ".m4v"))
    method = "sendVideo" if is_video else "sendDocument"
    field = "video" if is_video else "document"
    content_type = "video/mp4" if is_video else "application/octet-stream"
    thumbnail = await _fetch_thumbnail(file.thumb)
    if not thumbnail:
        thumbnail = await _make_thumbnail(path)
    meter = Meter()
    last_edit = 0.0

    async def progress(done: int) -> None:
        nonlocal last_edit
        now = time.monotonic()
        if now - last_edit < PROGRESS_EDIT_INTERVAL and done < size:
            return
        last_edit = now
        speed, elapsed = meter.update(done)
        await _safe_edit(status, render("upload", _escape(file.file_name), done, size, speed, elapsed))

    fields = {
        "chat_id": str(chat_id),
        "caption": _caption(file),
        "parse_mode": "HTML",
        "protect_content": "true" if protect_content else "false",
    }
    if is_video:
        fields["supports_streaming"] = "true"
    if thumbnail:
        fields["thumbnail"] = "attach://thumbnail"
    stream = _MultipartUpload(fields, field, path, file.file_name, content_type, progress, thumbnail=thumbnail)
    headers = {
        "content-type": f"multipart/form-data; boundary={stream.boundary}",
        "content-length": str(stream.content_length),
    }
    timeout = httpx.Timeout(None, connect=30.0, pool=30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            settings.telegram_method_url(method),
            headers=headers,
            content=stream,
        )
    try:
        payload = response.json()
    except Exception:
        payload = {}
    if response.status_code >= 400 or not payload.get("ok"):
        description = payload.get("description") or response.text[:500] or "telegram rejected the upload"
        raise RuntimeError(f"telegram upload failed: {description}")
    await progress(size)
    result = payload.get("result") or {}
    return int(result.get("message_id", 0))


async def _delete_message_later(bot, chat_id: int, message_id: int) -> None:
    if not message_id:
        return
    await asyncio.sleep(max(1, settings.auto_delete_minutes) * 60)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as exc:
        storage.log("debug", f"auto-delete failed for {chat_id}/{message_id}: {type(exc).__name__}")


def _require_owner(update: Update) -> bool:
    return bool(update.effective_user and storage.is_admin(update.effective_user.id))


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _require_owner(update):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    await _admin_home(update.message)


async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _require_owner(update):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    rows = storage.recent_users()
    await update.message.reply_text(
        "<b>👥 ʀᴇᴄᴇɴᴛ ᴜsᴇʀs</b>\n\n" + (_escape("\n".join(rows)) if rows else "no users yet."),
        parse_mode=ParseMode.HTML,
    )


async def logs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _require_owner(update):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    rows = storage.recent_logs()
    await update.message.reply_text(
        "<b>🧾 ʀᴇᴄᴇɴᴛ ʟᴏɢs</b>\n\n" + (_escape("\n".join(rows)) if rows else "no errors recorded."),
        parse_mode=ParseMode.HTML,
    )


async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _require_owner(update):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    if not context.args:
        await update.message.reply_text("usage: /ban &lt;user_id&gt;", parse_mode=ParseMode.HTML)
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("user id must be numeric.")
        return
    storage.ban(uid)
    await update.message.reply_text(f"banned <code>{uid}</code>.", parse_mode=ParseMode.HTML)


async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _require_owner(update):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    if not context.args:
        await update.message.reply_text("usage: /unban &lt;user_id&gt;", parse_mode=ParseMode.HTML)
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("user id must be numeric.")
        return
    storage.unban(uid)
    await update.message.reply_text(f"unbanned <code>{uid}</code>.", parse_mode=ParseMode.HTML)


async def auth_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _require_owner(update):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    if not context.args:
        await update.message.reply_text("usage: /auth &lt;user_id&gt;", parse_mode=ParseMode.HTML)
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("user id must be numeric.")
        return
    storage.authorize(uid)
    await update.message.reply_text(f"authorised <code>{uid}</code>.", parse_mode=ParseMode.HTML)


async def unauth_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _require_owner(update):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    if not context.args:
        await update.message.reply_text("usage: /unauth &lt;user_id&gt;", parse_mode=ParseMode.HTML)
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("user id must be numeric.")
        return
    storage.unauthorize(uid)
    await update.message.reply_text(f"removed <code>{uid}</code> from the allow-list.", parse_mode=ParseMode.HTML)


async def maintenance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _require_owner(update):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    flag = (context.args[0] if context.args else "on").lower()
    storage.kv_set("maintenance", "on" if flag in {"on", "1", "true"} else "off")
    await update.message.reply_text(
        f"maintenance is now <b>{storage.kv_get('maintenance')}</b>.",
        parse_mode=ParseMode.HTML,
    )


async def setwelcome_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _require_owner(update):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    text = " ".join(context.args).strip()
    if update.message.reply_to_message and update.message.reply_to_message.text:
        text = update.message.reply_to_message.text
    if not text:
        await update.message.reply_text("reply to a message or pass the new welcome text.")
        return
    storage.kv_set("welcome", text)
    settings.welcome_text = text
    await update.message.reply_text("welcome text updated.")


async def setcaption_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _require_owner(update):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    text = " ".join(context.args).strip() or "{filename}\\n{size}"
    storage.kv_set("caption", text.replace("\\n", "\n"))
    await update.message.reply_text("caption template updated.")


async def setlimit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _require_owner(update):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    if not context.args:
        await update.message.reply_text("usage: /setlimit &lt;mb&gt;", parse_mode=ParseMode.HTML)
        return
    try:
        requested = int(context.args[0])
    except ValueError:
        await update.message.reply_text("the limit must be a whole number of megabytes.")
        return
    if requested < 1 or requested > 2000:
        await update.message.reply_text("choose a limit between 1 and 2000 mb.")
        return
    storage.kv_set("limit", str(requested))
    await update.message.reply_text(
        f"configured upload limit: <b>{_upload_limit_mb()} mb</b>.",
        parse_mode=ParseMode.HTML,
    )


async def addpremium_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _require_owner(update):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    if len(context.args) != 3 or context.args[0].lower() not in {"r", "s", "v"}:
        await update.message.reply_text(
            "ᴜsᴀɢᴇ: <code>/addpremium r|s|v user_id days</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    try:
        key, user_id, days = context.args[0].lower(), int(context.args[1]), int(context.args[2])
    except ValueError:
        await update.message.reply_text("ᴜsᴇʀ ɪᴅ ᴀɴᴅ ᴅᴀʏs ᴍᴜsᴛ ʙᴇ ɴᴜᴍʙᴇʀs.")
        return
    plan = storage.get_plan(key)
    if not plan:
        await update.message.reply_text("ᴛʜᴀᴛ ᴘʟᴀɴ ᴅᴏᴇs ɴᴏᴛ ᴇxɪsᴛ.")
        return
    expiry = storage.activate_plan(user_id, key, days)
    await notify_manual_activation(
        context.bot,
        user_id=user_id,
        plan=plan,
        expiry=expiry,
        source_admin_id=update.effective_user.id,
    )
    await update.message.reply_text(
        f"✅ <b>{plan['label']}</b> ᴀᴄᴛɪᴠᴀᴛᴇᴅ ꜰᴏʀ <code>{user_id}</code> "
        f"ᴜɴᴛɪʟ <code>{expiry.strftime('%d %b %Y, %I:%M %p UTC')}</code>.",
        parse_mode=ParseMode.HTML,
    )


async def removepremium_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _require_owner(update):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    if len(context.args) != 1:
        await update.message.reply_text("ᴜsᴀɢᴇ: <code>/removepremium user_id</code>", parse_mode=ParseMode.HTML)
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ᴜsᴇʀ ɪᴅ ᴍᴜsᴛ ʙᴇ ɴᴜᴍᴇʀɪᴄ.")
        return
    storage.remove_premium(user_id)
    await update.message.reply_text(f"✅ ᴘʀᴇᴍɪᴜᴍ ʀᴇᴍᴏᴠᴇᴅ ꜰʀᴏᴍ <code>{user_id}</code>.", parse_mode=ParseMode.HTML)


async def add_admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not settings.is_owner(update.effective_user.id):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    if len(context.args) != 1:
        await update.message.reply_text("ᴜsᴀɢᴇ: <code>/add_admin user_id</code>", parse_mode=ParseMode.HTML)
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ᴜsᴇʀ ɪᴅ ᴍᴜsᴛ ʙᴇ ɴᴜᴍᴇʀɪᴄ.")
        return
    storage.add_admin(user_id)
    await update.get_bot().set_my_commands(
        [
            BotCommand("start", "ᴏᴘᴇɴ ᴛʜᴇ ʙᴏᴛ"),
            BotCommand("help", "sʜᴏᴡ ʜᴇʟᴘ"),
            BotCommand("premium", "ᴠɪᴇᴡ ᴘʟᴀɴs"),
            BotCommand("myplan", "ᴠɪᴇᴡ ʏᴏᴜʀ ʟɪᴍɪᴛs"),
            BotCommand("owner", "ᴏᴘᴇɴ ᴄᴏɴᴛʀᴏʟ ᴘᴀɴᴇʟ"),
            BotCommand("addpremium", "ᴀᴅᴅ ᴘʀᴇᴍɪᴜᴍ"),
            BotCommand("removepremium", "ʀᴇᴍᴏᴠᴇ ᴘʀᴇᴍɪᴜᴍ"),
            BotCommand("addforcesub", "ᴀᴅᴅ ғᴏʀᴄᴇ-sᴜʙ"),
            BotCommand("removeforcesub", "ʀᴇᴍᴏᴠᴇ ғᴏʀᴄᴇ-sᴜʙ"),
            BotCommand("setplan", "ᴇᴅɪᴛ ᴘʟᴀɴ"),
            BotCommand("deleteplan", "ʜɪᴅᴇ ᴘʟᴀɴ"),
        ],
        scope=BotCommandScopeChat(user_id),
    )
    await update.message.reply_text(f"✅ <code>{user_id}</code> ɪs ɴᴏᴡ ᴀɴ ᴀᴅᴍɪɴ.", parse_mode=ParseMode.HTML)


async def remove_admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not settings.is_owner(update.effective_user.id):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    if len(context.args) != 1:
        await update.message.reply_text("ᴜsᴀɢᴇ: <code>/remove_admin user_id</code>", parse_mode=ParseMode.HTML)
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ᴜsᴇʀ ɪᴅ ᴍᴜsᴛ ʙᴇ ɴᴜᴍᴇʀɪᴄ.")
        return
    storage.remove_admin(user_id)
    await update.get_bot().set_my_commands(
        [
            BotCommand("start", "ᴏᴘᴇɴ ᴛʜᴇ ʙᴏᴛ"),
            BotCommand("help", "sʜᴏᴡ ʜᴇʟᴘ"),
            BotCommand("premium", "ᴠɪᴇᴡ ᴘʟᴀɴs"),
            BotCommand("myplan", "ᴠɪᴇᴡ ʏᴏᴜʀ ʟɪᴍɪᴛs"),
        ],
        scope=BotCommandScopeChat(user_id),
    )
    await update.message.reply_text(f"✅ ᴀᴅᴍɪɴ ʀᴇᴍᴏᴠᴇᴅ ꜰʀᴏᴍ <code>{user_id}</code>.", parse_mode=ParseMode.HTML)


async def addforcesub_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _require_owner(update):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    if not context.args:
        await update.message.reply_text(
            "ᴜsᴀɢᴇ: <code>/addforcesub channel_id_or_username [invite_url]</code>\n"
            "ᴛʜᴇ ʙᴏᴛ ᴡɪʟʟ ᴛʀʏ ᴛᴏ ɢᴇɴᴇʀᴀᴛᴇ ᴛʜᴇ ʟɪɴᴋ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ.",
            parse_mode=ParseMode.HTML,
        )
        return
    channel = context.args[0]
    invite = context.args[1] if len(context.args) > 1 else ""
    if not invite:
        invite = await _create_force_sub_invite(context.bot, channel)
    storage.add_force_sub(channel, invite)
    if invite:
        await update.message.reply_text(
            f"✅ ғᴏʀᴄᴇ-sᴜʙ ᴄʜᴀɴɴᴇʟ sᴀᴠᴇᴅ.\n\nᴊᴏɪɴ ʟɪɴᴋ: {html.escape(invite)}",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(
            "⚠️ ᴄʜᴀɴɴᴇʟ sᴀᴠᴇᴅ, ʙᴜᴛ ᴛᴇʟᴇɢʀᴀᴍ ᴅɪᴅ ɴᴏᴛ ʀᴇᴛᴜʀɴ ᴀɴ ɪɴᴠɪᴛᴇ. "
            "ᴀᴅᴅ ᴛʜᴇ ʙᴏᴛ ᴀs ᴀᴅᴍɪɴ ᴡɪᴛʜ ɪɴᴠɪᴛᴇ ᴘᴇʀᴍɪssɪᴏɴs."
        )


async def removeforcesub_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _require_owner(update):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    if len(context.args) != 1:
        await update.message.reply_text("ᴜsᴀɢᴇ: <code>/removeforcesub channel</code>", parse_mode=ParseMode.HTML)
        return
    storage.remove_force_sub(context.args[0])
    await update.message.reply_text("✅ ғᴏʀᴄᴇ-sᴜʙ ᴄʜᴀɴɴᴇʟ ʀᴇᴍᴏᴠᴇᴅ.")


async def setstartphoto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _require_owner(update):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    photo = update.message.reply_to_message.photo[-1] if update.message.reply_to_message and update.message.reply_to_message.photo else None
    if photo:
        storage.kv_set("start_photo", photo.file_id)
        await update.message.reply_text("✅ sᴛᴀʀᴛ ᴘʜᴏᴛᴏ ᴜᴘᴅᴀᴛᴇᴅ.")
        return
    ADMIN_INPUTS[update.effective_user.id] = "startphoto"
    await update.message.reply_text("sᴇɴᴅ ᴛʜᴇ ɴᴇᴡ sᴛᴀʀᴛ ᴘʜᴏᴛᴏ ɴᴏᴡ.")


async def clearstartphoto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _require_owner(update):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    storage.kv_delete("start_photo")
    await update.message.reply_text("✅ sᴛᴀʀᴛ ᴘʜᴏᴛᴏ ᴄʟᴇᴀʀᴇᴅ.")


async def setplan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _require_owner(update):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    if len(context.args) != 5:
        await update.message.reply_text(
            "ᴜsᴀɢᴇ: <code>/setplan key price days batch total_links</code>\n"
            "ᴜsᴇ 0 ꜰᴏʀ ᴜɴʟɪᴍɪᴛᴇᴅ ᴛᴏᴛᴀʟ ʟɪɴᴋs.",
            parse_mode=ParseMode.HTML,
        )
        return
    try:
        key, price, days, batch, total = context.args[0].lower(), float(context.args[1]), int(context.args[2]), int(context.args[3]), int(context.args[4])
    except ValueError:
        await update.message.reply_text("ᴘʀɪᴄᴇ, ᴅᴀʏs, ʙᴀᴛᴄʜ ᴀɴᴅ ᴛᴏᴛᴀʟ ᴍᴜsᴛ ʙᴇ ɴᴜᴍʙᴇʀs.")
        return
    if price <= 0 or days <= 0 or batch <= 0 or total < 0:
        await update.message.reply_text("ᴜsᴇ ᴘᴏsɪᴛɪᴠᴇ ᴠᴀʟᴜᴇs; ᴛᴏᴛᴀʟ ᴄᴀɴ ʙᴇ 0 ꜰᴏʀ ᴜɴʟɪᴍɪᴛᴇᴅ.")
        return
    if not re.fullmatch(r"[a-z0-9_-]{1,16}", key):
        await update.message.reply_text("the plan key must contain only lowercase letters, numbers, _ or -.")
        return
    labels = {"r": ("regular premium", "regular"), "s": ("super premium", "super"), "v": ("vip premium", "vip")}
    label, short_label = labels.get(key, (f"{key} premium", key))
    storage.upsert_plan(
        {
            "key": key,
            "label": label,
            "short_label": short_label,
            "price": price,
            "duration_days": days,
            "batch_limit": batch,
            "total_links": total,
            "active": True,
        }
    )
    await update.message.reply_text(f"✅ ᴘʟᴀɴ <b>{key}</b> ᴜᴘᴅᴀᴛᴇᴅ.", parse_mode=ParseMode.HTML)


async def deleteplan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _require_owner(update):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    if len(context.args) != 1:
        await update.message.reply_text("ᴜsᴀɢᴇ: <code>/deleteplan key</code>", parse_mode=ParseMode.HTML)
        return
    storage.delete_plan(context.args[0].lower())
    await update.message.reply_text("✅ ᴘʟᴀɴ ʜɪᴅᴅᴇɴ ꜰʀᴏᴍ ᴜsᴇʀs.")


async def _handle_admin_input(message, user_id: int, bot=None) -> bool:
    state = ADMIN_INPUTS.get(user_id)
    if state and state.startswith("plan:"):
        values = [value.strip() for value in (message.text or "").split("|")]
        if len(values) != 7:
            await message.reply_text(
                "send exactly 7 values separated by <code>|</code>:\n"
                "<code>key | name | short name | price | days | batch limit | total links</code>",
                parse_mode=ParseMode.HTML,
            )
            return True
        original_key = state.split(":")[-1] if state.startswith("plan:edit:") else None
        key, label, short_label = values[:3]
        key = (original_key or key).lower()
        try:
            price = float(values[3])
            days = int(values[4])
            batch = int(values[5])
            total = int(values[6])
        except ValueError:
            await message.reply_text(
                "price, days, batch limit and total links must be numbers.",
                parse_mode=ParseMode.HTML,
            )
            return True
        if (
            not re.fullmatch(r"[a-z0-9_-]{1,16}", key)
            or not label
            or not short_label
            or price <= 0
            or days <= 0
            or batch <= 0
            or total < 0
        ):
            await message.reply_text(
                "check the values: key must be lowercase, price/days/batch must be positive, "
                "and total links must be 0 or higher.",
                parse_mode=ParseMode.HTML,
            )
            return True
        storage.upsert_plan(
            {
                "key": key,
                "label": label,
                "short_label": short_label,
                "price": price,
                "duration_days": days,
                "batch_limit": batch,
                "total_links": total,
                "active": True,
            }
        )
        ADMIN_INPUTS.pop(user_id, None)
        panel_id = ACTIVE_PANELS.get(message.chat.id)
        if panel_id:
            rows = storage.list_plans(True)
            lines = []
            for plan in rows:
                total_text = "unlimited" if not plan.get("total_links") else str(plan["total_links"])
                lines.append(
                    f"<b>{_escape(plan['key'])}</b> · {_escape(plan['label'])} · "
                    f"₹{_escape(plan['price'])} · {plan['duration_days']} days · "
                    f"batch {plan['batch_limit']} · total {total_text}"
                )
            text = (
                "<b>premium plans</b>\n\n"
                + ("\n".join(lines) if lines else "no active plans.")
                + f"\n\n<b>saved:</b> {_escape(label)}"
            )
            try:
                await message.get_bot().edit_message_text(
                    chat_id=message.chat.id,
                    message_id=panel_id,
                    text=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=_plans_keyboard(),
                )
            except Exception:
                pass
        return True
    if state == "forcesub":
        parts = (message.text or "").split()
        if len(parts) >= 1 and parts[0].startswith(("/", "http")) is False:
            invite = parts[1] if len(parts) > 1 else ""
            if not invite and bot is not None:
                invite = await _create_force_sub_invite(bot, parts[0])
            storage.add_force_sub(parts[0], invite)
            ADMIN_INPUTS.pop(user_id, None)
            suffix = f"\n\nᴊᴏɪɴ ʟɪɴᴋ: {html.escape(invite)}" if invite else ""
            await message.reply_text(
                f"✅ ғᴏʀᴄᴇ-sᴜʙ ᴄʜᴀɴɴᴇʟ sᴀᴠᴇᴅ.{suffix}",
                parse_mode=ParseMode.HTML,
            )
            return True
    return False


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not storage.is_admin(user.id) or ADMIN_INPUTS.get(user.id) != "startphoto":
        return
    photo = update.message.photo[-1]
    storage.kv_set("start_photo", photo.file_id)
    ADMIN_INPUTS.pop(user.id, None)
    await update.message.reply_text("✅ sᴛᴀʀᴛ ᴘʜᴏᴛᴏ sᴀᴠᴇᴅ. ᴛʀʏ /start ᴛᴏ ᴘʀᴇᴠɪᴇᴡ ɪᴛ.")


async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _require_owner(update):
        await update.message.reply_text(texts.NOT_OWNER, parse_mode=ParseMode.HTML)
        return
    text = " ".join(context.args).strip()
    if update.message.reply_to_message and update.message.reply_to_message.text:
        text = update.message.reply_to_message.text
    if not text:
        await update.message.reply_text("usage: /broadcast &lt;text&gt;", parse_mode=ParseMode.HTML)
        return
    sent = 0
    for uid in storage.user_ids():
        try:
            await context.bot.send_message(uid, text, parse_mode=ParseMode.HTML)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            continue
    await update.message.reply_text(f"broadcast sent to <b>{sent}</b> users.", parse_mode=ParseMode.HTML)
