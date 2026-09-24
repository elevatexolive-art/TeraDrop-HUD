from __future__ import annotations

import asyncio
import html
import io
import logging
import secrets
import string
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import httpx
import qrcode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app import storage
from app.settings import settings

log = logging.getLogger("teradrop.payments")
_active: dict[str, asyncio.Task] = {}


def make_order_id(user_id: int) -> str:
    suffix = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(5))
    return f"ORD-{user_id}-{suffix}"


def _upi_uri(order_id: str, amount: float) -> str:
    return (
        "upi://pay?pa="
        + quote(settings.upi_id, safe="@._-")
        + "&pn="
        + quote(settings.upi_payee_name)
        + f"&am={amount:.2f}&cu=INR&tr={quote(order_id)}"
    )


def qr_image(order_id: str, amount: float) -> io.BytesIO:
    image = qrcode.make(_upi_uri(order_id, amount))
    output = io.BytesIO()
    output.name = f"{order_id}.png"
    image.save(output, format="PNG")
    output.seek(0)
    return output


async def verify_payment_once(order_id: str, expected_amount: float) -> dict | None:
    if not settings.paytm_mid:
        log.error("PAYTM_MID is not configured")
        return None
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15, connect=8)) as client:
            response = await client.get(
                settings.payment_api_url,
                params={"mid": settings.paytm_mid, "oid": order_id},
            )
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        log.warning("payment check failed for %s: %s", order_id, type(exc).__name__)
        return None
    if str(data.get("STATUS", "")).upper() != "TXN_SUCCESS":
        return None
    if str(data.get("ORDERID", "")) != order_id:
        log.warning("payment order mismatch for %s", order_id)
        return None
    try:
        paid = float(data.get("TXNAMOUNT", 0))
    except (TypeError, ValueError):
        return None
    if abs(paid - expected_amount) > settings.amount_tolerance:
        log.warning("payment amount mismatch for %s: expected=%s paid=%s", order_id, expected_amount, paid)
        return None
    txn_id = str(data.get("TXNID") or "")
    if not storage.claim_transaction(txn_id):
        return None
    return {
        "txn_id": txn_id,
        "bank_txn_id": data.get("BANKTXNID"),
        "txn_date": data.get("TXNDATE"),
        "amount": paid,
    }


async def _notify_success(bot, order: dict, transaction: dict) -> None:
    plan = storage.get_plan(order["plan_key"]) or {}
    expiry = storage.activate_plan(order["user_id"], order["plan_key"], int(order["days"]))
    expiry_text = expiry.astimezone(timezone.utc).strftime("%d %b %Y, %I:%M %p UTC")
    plan_label = html.escape(str(plan.get("label", order["plan_key"])))
    text = (
        "<b>✅ ᴘᴀʏᴍᴇɴᴛ ᴠᴇʀɪꜰɪᴇᴅ</b>\n\n"
        f"<blockquote>ʏᴏᴜʀ <b>{plan_label}</b> ɪs ɴᴏᴡ ᴀᴄᴛɪᴠᴇ.\n"
        f"ᴇxᴘɪʀᴇs: <code>{expiry_text}</code>\n"
        "ᴄᴏᴘʏ/ꜰᴏʀᴡᴀʀᴅ ɪs ᴇɴᴀʙʟᴇᴅ ᴡʜɪʟᴇ ᴛʜɪs ᴘʟᴀɴ ɪs ᴀᴄᴛɪᴠᴇ.</blockquote>"
    )
    # Always send a fresh private notification. Editing the plans message is
    # only a visual convenience and is not reliable when the source message
    # was deleted, moved, or sent from a different chat.
    try:
        await bot.send_message(order["user_id"], text, parse_mode="HTML")
    except Exception:
        log.warning("could not notify paid user %s", order["user_id"])

    try:
        if order.get("source_chat_id") and order.get("source_message_id"):
            if order.get("source_is_photo"):
                await bot.edit_message_caption(
                    chat_id=order["source_chat_id"],
                    message_id=order["source_message_id"],
                    caption=text,
                    parse_mode="HTML",
                )
            else:
                await bot.edit_message_text(
                    chat_id=order["source_chat_id"],
                    message_id=order["source_message_id"],
                    text=text,
                    parse_mode="HTML",
                )
        else:
            raise RuntimeError("payment source message is missing")
    except Exception:
        pass
    log_text = (
        "<b>💰 ɴᴇᴡ ᴘʀᴇᴍɪᴜᴍ ᴘᴀʏᴍᴇɴᴛ</b>\n\n"
        f"ᴜsᴇʀ: <code>{order['user_id']}</code>\n"
        f"ᴘʟᴀɴ: <b>{plan_label}</b>\n"
        f"ᴀᴍᴏᴜɴᴛ: <b>₹{order['amount']}</b>\n"
        f"ᴏʀᴅᴇʀ: <code>{order['order_id']}</code>\n"
        f"ᴛʀᴀɴsᴀᴄᴛɪᴏɴ: <code>{transaction.get('txn_id', 'n/a')}</code>\n"
        f"ᴇxᴘɪʀᴇs: <code>{expiry_text}</code>"
    )
    await _fanout_activation(
        bot,
        user_id=int(order["user_id"]),
        log_text=log_text,
        source="automatic payment",
    )


def _channel_ids() -> list[int | str]:
    """Return configured log destinations, retaining the legacy payment id."""
    values: list[int | str] = [
        storage.kv_get("log_channel") or settings.log_channel,
        storage.kv_get("dump_channel") or settings.dump_channel,
        settings.payment_log_channel_id,
    ]
    out: list[int | str] = []
    seen: set[str] = set()
    for value in values:
        if value in (None, "", 0, "0"):
            continue
        target: int | str = value
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                continue
            target = int(stripped) if stripped.lstrip("-").isdigit() else stripped
        marker = str(target)
        if marker not in seen:
            seen.add(marker)
            out.append(target)
    return out


async def _fanout_activation(bot, user_id: int, log_text: str, source: str) -> None:
    storage.log("info", f"{source}: premium activated for user {user_id}")
    destinations = _channel_ids()
    admin_text = (
        "🔔 <b>premium activation</b>\n\n"
        f"user: <code>{user_id}</code>\n"
        f"source: <b>{source}</b>\n\n"
        + log_text
    )
    for admin_id in storage.admin_ids():
        try:
            await bot.send_message(admin_id, admin_text, parse_mode="HTML")
        except Exception:
            log.warning("could not notify admin %s", admin_id)
    for channel_id in destinations:
        try:
            await bot.send_message(channel_id, log_text, parse_mode="HTML")
        except Exception:
            log.warning("could not send activation log to %s", channel_id)


async def notify_manual_activation(
    bot,
    user_id: int,
    plan: dict,
    expiry: datetime,
    source_admin_id: int,
) -> None:
    """Notify a manually granted subscriber and all configured destinations."""
    expiry_text = expiry.astimezone(timezone.utc).strftime("%d %b %Y, %I:%M %p UTC")
    plan_label = html.escape(str(plan.get("label", plan.get("key", "premium"))))
    user_text = (
        "<b>✅ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴛɪᴠᴀᴛᴇᴅ</b>\n\n"
        f"ʏᴏᴜʀ <b>{plan_label}</b> ɪs ɴᴏᴡ ᴀᴄᴛɪᴠᴇ.\n"
        f"ᴇxᴘɪʀᴇs: <code>{expiry_text}</code>"
    )
    try:
        await bot.send_message(user_id, user_text, parse_mode="HTML")
    except Exception:
        log.warning("could not notify manually activated user %s", user_id)
    log_text = (
        "<b>🛠 ᴍᴀɴᴜᴀʟ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴛɪᴠᴀᴛɪᴏɴ</b>\n\n"
        f"ᴜsᴇʀ: <code>{user_id}</code>\n"
        f"ᴘʟᴀɴ: <b>{plan_label}</b>\n"
        f"ɢʀᴀɴᴛᴇᴅ ʙʏ: <code>{source_admin_id}</code>\n"
        f"ᴇxᴘɪʀᴇs: <code>{expiry_text}</code>"
    )
    await _fanout_activation(bot, user_id, log_text, "manual admin grant")


async def _verify_loop(bot, order_id: str, qr_message) -> None:
    try:
        deadline = datetime.now(timezone.utc) + timedelta(minutes=settings.payment_max_minutes)
        while datetime.now(timezone.utc) < deadline:
            order = storage.get_order(order_id)
            if not order or order.get("status") != "pending":
                return
            result = await verify_payment_once(order_id, float(order["amount"]))
            if result:
                if storage.mark_order_success(order_id, result["txn_id"]):
                    await _notify_success(bot, order, result)
                try:
                    await qr_message.delete()
                except Exception:
                    pass
                return
            await asyncio.sleep(max(15, settings.payment_verify_interval))
        storage.update_order_status(order_id, "expired")
        try:
            await qr_message.edit_caption(
                caption=(
                    "<b>⏰ ᴘᴀʏᴍᴇɴᴛ sᴇssɪᴏɴ ᴇxᴘɪʀᴇᴅ</b>\n\n"
                    "ᴛʜɪs ǫʀ ᴄᴏᴅᴇ ɪs ɴᴏ ʟᴏɴɢᴇʀ ᴠᴀʟɪᴅ. ᴘʟᴇᴀsᴇ sᴛᴀʀᴛ ᴀ ɴᴇᴡ ᴘᴜʀᴄʜᴀsᴇ."
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("view plans", callback_data="premium")]]
                ),
            )
        except Exception:
            pass
    finally:
        _active.pop(order_id, None)


def start_verifier(bot, order_id: str, qr_message) -> None:
    if order_id not in _active:
        _active[order_id] = asyncio.create_task(_verify_loop(bot, order_id, qr_message))


def cancel_verifier(order_id: str) -> None:
    task = _active.pop(order_id, None)
    if task and not task.done():
        task.cancel()