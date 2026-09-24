"""Owner-controlled Telegram user session and WebApp initData refresh.

Telegram WebApp initData is issued by the Mini App launch flow; signing in a
user account alone cannot manufacture a valid token. This module uses the
signed-in account to request each configured Mini App URL, then stores only an
encrypted Telethon StringSession and the short-lived initData in MongoDB.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import os
import time
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

from cryptography.fernet import Fernet, InvalidToken
from telethon import TelegramClient, errors, functions
from telethon.sessions import StringSession

from app import storage
from app.settings import settings

log = logging.getLogger("teradrop.telegram_auth")

_SESSION_KEY = "telegram_user_session"
_SERVICE_KEY = "tg_init_data:{}"
_SERVICE_FETCHED_KEY = "tg_init_data_fetched_at:{}"
_REFRESH_INTERVAL = 5 * 60


@dataclass(frozen=True)
class ServiceConfig:
    name: str
    bot: str
    webapp_url: str


def _services() -> tuple[ServiceConfig, ...]:
    return (
        ServiceConfig("flezen", settings.flezen_tg_bot, settings.flezen_webapp_url),
        ServiceConfig("diskwala", settings.diskwala_tg_bot, settings.diskwala_webapp_url),
        ServiceConfig("vidbunker", settings.vidbunker_tg_bot, settings.vidbunker_webapp_url),
    )


def _fernet() -> Fernet:
    secret = (settings.session_secret or os.environ.get("SESSION_SECRET") or "").strip()
    if len(secret) < 16:
        raise RuntimeError("SESSION_SECRET must be configured before Telegram login.")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def _encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode()).decode()
    except (InvalidToken, ValueError) as exc:
        raise RuntimeError("The stored Telegram session cannot be decrypted.") from exc


def _extract_init_data(web_url: str) -> str | None:
    """Extract the exact Telegram WebApp initData string from a launch URL."""
    parsed = urlsplit(web_url)
    for raw in (parsed.fragment, parsed.query):
        if not raw:
            continue
        value = parse_qs(raw, keep_blank_values=True).get("tgWebAppData", [None])[0]
        if value:
            return value
    return None


class TelegramAuthManager:
    def __init__(self) -> None:
        self._client: TelegramClient | None = None
        self._lock = asyncio.Lock()
        self._refresh_task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._phone = ""
        self._phone_code_hash = ""

    @property
    def has_credentials(self) -> bool:
        return bool(settings.telegram_api_id and settings.telegram_api_hash)

    def _stored_session(self) -> str:
        encrypted = storage.kv_get(_SESSION_KEY)
        return _decrypt(encrypted) if encrypted else ""

    def _stored_init_data(self, service_name: str) -> str:
        encrypted = storage.kv_get(_SERVICE_KEY.format(service_name))
        if not encrypted:
            return ""
        return _decrypt(encrypted)

    def _client_for(self, session: str = "") -> TelegramClient:
        if not self.has_credentials:
            raise RuntimeError("TELEGRAM_API_ID and TELEGRAM_API_HASH are required.")
        return TelegramClient(
            StringSession(session),
            settings.telegram_api_id,
            settings.telegram_api_hash,
            device_model="TeraDrop auth client",
            system_version="1.0",
            app_version="1.0",
        )

    async def _ensure_client(self) -> TelegramClient:
        async with self._lock:
            if self._client is None:
                self._client = self._client_for(self._stored_session())
            if not self._client.is_connected():
                await self._client.connect()
            return self._client

    async def initialize(self) -> None:
        if not self.has_credentials or not storage.kv_get(_SESSION_KEY):
            return
        try:
            client = await self._ensure_client()
            if not await client.is_user_authorized():
                log.warning("Stored Telegram session is no longer authorized.")
        except Exception as exc:
            log.warning("Could not load stored Telegram session: %s", type(exc).__name__)

    async def start_login(self, phone: str) -> str:
        phone = phone.strip()
        if not phone or not phone.startswith("+"):
            raise ValueError("Send the phone number in international format, for example +919876543210.")
        client = await self._ensure_client()
        sent = await client.send_code_request(phone)
        self._phone = phone
        self._phone_code_hash = sent.phone_code_hash
        return "A Telegram login code was sent. Send only that code here."

    async def submit_code(self, code: str) -> str:
        if not self._phone or not self._phone_code_hash:
            raise RuntimeError("Start with /tglogin first.")
        client = await self._ensure_client()
        try:
            await client.sign_in(self._phone, code.strip(), phone_code_hash=self._phone_code_hash)
        except errors.SessionPasswordNeededError:
            return "This account has 2-step verification. Send the 2-step password now."
        await self._save_session(client)
        self._clear_login_state()
        return "Telegram account connected. Configured Mini Apps will refresh automatically."

    async def submit_password(self, password: str) -> str:
        client = await self._ensure_client()
        await client.sign_in(password=password)
        await self._save_session(client)
        self._clear_login_state()
        return "Telegram account connected. Configured Mini Apps will refresh automatically."

    async def _save_session(self, client: TelegramClient) -> None:
        session = client.session.save()
        if not session:
            raise RuntimeError("Telegram did not return a reusable session.")
        storage.kv_set(_SESSION_KEY, _encrypt(session))
        await self.refresh_all(force=True)

    def _clear_login_state(self) -> None:
        self._phone = ""
        self._phone_code_hash = ""

    async def logout(self) -> None:
        if self._client is not None:
            try:
                await self._client.log_out()
            except Exception:
                await self._client.disconnect()
        self._client = None
        storage.kv_set(_SESSION_KEY, "")
        for service in _services():
            storage.kv_set(_SERVICE_KEY.format(service.name), "")
            storage.kv_set(_SERVICE_FETCHED_KEY.format(service.name), "")
        self._clear_login_state()

    async def status(self) -> dict[str, object]:
        connected = False
        authorized = False
        if self.has_credentials and storage.kv_get(_SESSION_KEY):
            try:
                client = await self._ensure_client()
                connected = client.is_connected()
                authorized = await client.is_user_authorized()
            except Exception:
                pass
        services: dict[str, str] = {}
        for service in _services():
            value = self._stored_init_data(service.name)
            fetched = storage.kv_get(_SERVICE_FETCHED_KEY.format(service.name))
            services[service.name] = "ready" if value and fetched else "not configured"
        return {"connected": connected, "authorized": authorized, "services": services}

    async def _refresh_service(self, service: ServiceConfig, force: bool) -> str | None:
        if not service.bot or not service.webapp_url:
            return storage.kv_get(_SERVICE_KEY.format(service.name)) or None
        current = self._stored_init_data(service.name)
        fetched_at = float(storage.kv_get(_SERVICE_FETCHED_KEY.format(service.name), "0") or 0)
        lead_seconds = max(5, settings.telegram_auth_refresh_minutes) * 60
        if current and not force and fetched_at > time.time() - lead_seconds:
            return current
        client = await self._ensure_client()
        if not await client.is_user_authorized():
            return current or None
        try:
            bot = await client.get_entity(service.bot)
            result = await client(
                functions.messages.RequestWebViewRequest(
                    peer=bot,
                    bot=bot,
                    platform="android",
                    url=service.webapp_url,
                    from_bot_menu=False,
                )
            )
            init_data = _extract_init_data(result.url)
            if not init_data:
                raise RuntimeError("Telegram returned a Mini App URL without tgWebAppData.")
            storage.kv_set(_SERVICE_KEY.format(service.name), _encrypt(init_data))
            storage.kv_set(_SERVICE_FETCHED_KEY.format(service.name), str(time.time()))
            return init_data
        except Exception as exc:
            log.warning("Could not refresh %s WebApp auth: %s", service.name, type(exc).__name__)
            return current or None

    async def refresh(self, service_name: str, force: bool = False) -> str | None:
        for service in _services():
            if service.name == service_name:
                value = await self._refresh_service(service, force)
                if value:
                    return value
                break
        env_name = f"{service_name.upper()}_TG_INIT_DATA"
        return (os.environ.get(env_name) or "").strip() or None

    async def refresh_all(self, force: bool = False) -> None:
        if not self.has_credentials or not storage.kv_get(_SESSION_KEY):
            return
        for service in _services():
            await self._refresh_service(service, force)

    async def get_init_data(self, service_name: str) -> str | None:
        value = await self.refresh(service_name, force=False)
        if value:
            return value
        return (os.environ.get(f"{service_name.upper()}_TG_INIT_DATA") or "").strip() or None

    async def refresh_loop(self) -> None:
        self._stop.clear()
        try:
            while not self._stop.is_set():
                try:
                    await self.refresh_all(force=False)
                except Exception as exc:
                    log.warning("Telegram auth refresh loop failed: %s", type(exc).__name__)
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=_REFRESH_INTERVAL)
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            return

    async def shutdown(self) -> None:
        self._stop.set()
        if self._refresh_task:
            self._refresh_task.cancel()
            await asyncio.gather(self._refresh_task, return_exceptions=True)
            self._refresh_task = None
        if self._client:
            await self._client.disconnect()
            self._client = None

    def start_refresh_task(self) -> None:
        if self._refresh_task is None or self._refresh_task.done():
            self._refresh_task = asyncio.create_task(self.refresh_loop())


telegram_auth = TelegramAuthManager()