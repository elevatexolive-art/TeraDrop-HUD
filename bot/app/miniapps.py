"""Live Mini App catalog.

Fetches each Mini App's current JS bundle, extracts API URLs / AES keys /
bot ids, and hot-applies them into Settings + .env so the admin panel always
shows the values the bot is actually using. The logged-in Telegram account
is used to read the real WebView origin if it moves.

Resolvers never hard-code a single path: they read this catalog, and a 404
triggers an immediate re-sync + retry.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

from app import env_manager, storage
from app.settings import settings

log = logging.getLogger("teradrop.miniapps")

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
_KV_KEY = "miniapp_catalog"
_SCRIPT_SRC = re.compile(
    r"""(?:src|href)\s*=\s*["']([^"']+\.js[^"']*)["']""",
    re.I,
)
_MODULEPRELOAD = re.compile(
    r"""<link[^>]+rel=["'](?:modulepreload|preload)["'][^>]+href=["']([^"']+)["']""",
    re.I,
)
_CHUNK_JS = re.compile(r"""["'](/assets/[^"' ]+\.js)["']""")
_QUOTED_URL = re.compile(r"""[`"'](https://[a-zA-Z0-9._~:/?#@!$&*+,;=%\-]+)[`"']""")
_HEX64 = re.compile(r"""[`"']([0-9a-fA-F]{64})[`"']""")
_BOT_ID = re.compile(
    r"""X-Bot-Id[`"']?\s*[:=]\s*[`"']([A-Za-z0-9_\-]+)[`"']""",
    re.I,
)
_TME = re.compile(r"""t\.me/([A-Za-z0-9_]{3,32})""", re.I)
_SKIP_HOSTS = (
    "telegram.org",
    "t.me",
    "adsgram",
    "richinfo",
    "libtl.com",
    "tgads.space",
    "cloudflareinsights",
    "whephiwums",
    "google",
    "gstatic",
    "facebook",
    "doubleclick",
)
_MAX_BUNDLES = 8
_MAX_BUNDLE_BYTES = 3_000_000
_SYNC_LOCK_TIMEOUT = 60.0

_DEFAULTS: dict[str, dict[str, str]] = {
    "flezen": {
        "webapp_url": "https://flezen-downloader.pages.dev/",
        "origin": "https://flezen-downloader.pages.dev",
        "bot_id": "flezen",
        "download_url": "https://api2.diskwala.net/api/flezen/downloadw",
        "status_url": "https://api2.diskwala.net/api/flezen/statusw",
        "download_method": "POST",
        "status_method": "GET",
        "aes_key_hex": "e7109544dab612bd5b80b8a427ac474ba5541b9efff7a4ca1c8ef85df2489c23",
        "tg_bot": "",
    },
    "diskwala": {
        "webapp_url": "https://miniapp.diskwala.net/",
        "origin": "https://miniapp.diskwala.net",
        "bot_id": "diskwala",
        "download_url": "https://api2.diskwala.net/api/diskwala/download1",
        "status_url": "https://api2.diskwala.net/api/diskwala/status1",
        "download_method": "POST",
        "status_method": "GET",
        "aes_key_hex": "e7109544dab612bd5b80b8a427ac474ba5541b9efff7a4ca1c8ef85df2489c23",
        "tg_bot": "",
    },
    "vidbunker": {
        "webapp_url": "https://vidbunker-ma.pages.dev/",
        "origin": "https://vidbunker-ma.pages.dev",
        "bot_id": "vidbunker",
        "download_url": "https://vidbunker-backend.dailyweb577.workers.dev/api/download",
        "status_url": "",
        "download_method": "POST",
        "status_method": "GET",
        "aes_key_hex": "",
        "tg_bot": "vidbunkerbot",
    },
}

_ENV_MAP = {
    "flezen": {
        "download_url": "FLEZEN_API_DOWNLOAD",
        "status_url": "FLEZEN_API_STATUS",
        "bot_id": "FLEZEN_BOT_ID",
        "aes_key_hex": "FLEZEN_AES_KEY",
        "webapp_url": "FLEZEN_WEBAPP_URL",
        "tg_bot": "FLEZEN_TG_BOT",
    },
    "diskwala": {
        "download_url": "DISKWALA_API_DOWNLOAD",
        "status_url": "DISKWALA_API_STATUS",
        "bot_id": "DISKWALA_BOT_ID",
        "aes_key_hex": "DISKWALA_AES_KEY",
        "webapp_url": "DISKWALA_WEBAPP_URL",
        "tg_bot": "DISKWALA_TG_BOT",
    },
    "vidbunker": {
        "download_url": "VIDBUNKER_API_URL",
        "bot_id": "VIDBUNKER_BOT_ID",
        "webapp_url": "VIDBUNKER_WEBAPP_URL",
        "tg_bot": "VIDBUNKER_TG_BOT",
    },
}


@dataclass
class MiniAppSpec:
    name: str
    webapp_url: str
    origin: str
    bot_id: str
    download_url: str
    status_url: str = ""
    download_method: str = "POST"
    status_method: str = "GET"
    aes_key_hex: str = ""
    tg_bot: str = ""
    bundle: str = ""
    fallbacks: list[str] = field(default_factory=list)
    synced_at: float = 0.0
    source: str = "default"
    error: str = ""

    def headers(self, init_data: str) -> dict[str, str]:
        origin = (self.origin or self.webapp_url or "").rstrip("/")
        return {
            "user-agent": _UA,
            "origin": origin,
            "referer": origin + "/",
            "authorization": f"Bearer {init_data}",
            "x-bot-id": self.bot_id or self.name,
        }

    def snapshot(self) -> dict[str, Any]:
        data = asdict(self)
        if self.aes_key_hex:
            data["aes_key_hex"] = env_manager.mask_value("DISKWALA_AES_KEY", self.aes_key_hex)
        data["synced_ago"] = _ago(self.synced_at)
        return data


def _ago(ts: float) -> str:
    if not ts:
        return "never"
    delta = max(0, int(time.time() - ts))
    if delta < 60:
        return f"{delta}s ago"
    if delta < 3600:
        return f"{delta // 60}m ago"
    return f"{delta // 3600}h ago"


def _origin_of(url: str) -> str:
    parsed = urlsplit(url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def _same_host(url: str, origin: str) -> bool:
    a = (urlsplit(url).netloc or "").lower()
    b = (urlsplit(origin).netloc or "").lower()
    return bool(a) and a == b


def _skip_host(url: str) -> bool:
    host = (urlsplit(url).netloc or "").lower()
    return any(part in host for part in _SKIP_HOSTS)


def _clean_url(url: str) -> str:
    url = (url or "").strip().rstrip("\\")
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))


def _service_match(url: str, name: str) -> bool:
    blob = url.lower()
    if name == "flezen":
        return "/api/flezen/" in blob or "flezen" in blob
    if name == "diskwala":
        return "/api/diskwala/" in blob
    if name == "vidbunker":
        return "vidbunker" in blob
    return name in blob


def _looks_download(url: str) -> bool:
    path = urlsplit(url).path.lower()
    return "download" in path and "status" not in path


def _looks_status(url: str) -> bool:
    return "status" in urlsplit(url).path.lower()


def _guess_bot(name: str, usernames: list[str]) -> str:
    needle = name.lower()
    for user in usernames:
        if needle in user.lower():
            return user
    return ""


def _script_urls(html: str, base: str) -> list[str]:
    found: list[str] = []
    for match in _SCRIPT_SRC.findall(html):
        found.append(urljoin(base, match))
    for match in _MODULEPRELOAD.findall(html):
        found.append(urljoin(base, match))
    out: list[str] = []
    seen: set[str] = set()
    origin = _origin_of(base)
    for url in found:
        if url in seen or _skip_host(url):
            continue
        if not _same_host(url, origin):
            continue
        seen.add(url)
        out.append(url)
    out.sort(key=lambda u: (0 if "/assets/index-" in u else 1, u))
    return out


def extract_from_js(js: str) -> dict[str, Any]:
    """Pull Mini App API facts out of a bundled JS file."""
    urls = [_clean_url(u) for u in _QUOTED_URL.findall(js)]
    urls = [u for u in urls if u]
    keys = [k.lower() for k in _HEX64.findall(js)]
    bot_ids = [b.lower() for b in _BOT_ID.findall(js)]
    bots = list(dict.fromkeys(_TME.findall(js)))
    facts: dict[str, Any] = {
        "urls": urls,
        "aes_keys": keys,
        "bot_ids": list(dict.fromkeys(bot_ids)),
        "tg_bots": bots,
        "by_service": {},
    }
    for name in _DEFAULTS:
        downloads = [u for u in urls if _service_match(u, name) and _looks_download(u)]
        statuses = [u for u in urls if _service_match(u, name) and _looks_status(u)]
        extras = [u for u in urls if _service_match(u, name) and u not in downloads and u not in statuses]
        bot_id = next((b for b in bot_ids if name in b), name)
        facts["by_service"][name] = {
            "download_urls": list(dict.fromkeys(downloads)),
            "status_urls": list(dict.fromkeys(statuses)),
            "extra_urls": list(dict.fromkeys(extras)),
            "bot_id": bot_id,
            "tg_bot": _guess_bot(name, bots),
        }
        # VidBunker often stores only the backend origin as a constant.
        if name == "vidbunker" and not downloads:
            origins = [u for u in urls if "vidbunker" in u.lower() and "workers.dev" in u.lower()]
            for origin in origins:
                joined = origin.rstrip("/") + "/api/download"
                facts["by_service"][name]["download_urls"].append(joined)
    # AES-GCM key: prefer the one sitting next to download/status constants.
    aes = ""
    if keys:
        window = js
        best = ""
        for key in keys:
            idx = js.lower().find(key.lower())
            ctx = js[max(0, idx - 400) : idx + 80].lower()
            if any(token in ctx for token in ("aes-gcm", "download", "diskwala", "flezen", "status")):
                best = key
                break
        aes = best or keys[0]
    facts["aes_key_hex"] = aes
    return facts


def _seed_spec(name: str) -> MiniAppSpec:
    base = dict(_DEFAULTS[name])
    env_download = {
        "flezen": settings.flezen_api_download,
        "diskwala": settings.diskwala_api_download,
        "vidbunker": settings.vidbunker_api_url,
    }.get(name) or ""
    env_status = {
        "flezen": settings.flezen_api_status,
        "diskwala": settings.diskwala_api_status,
        "vidbunker": "",
    }.get(name) or ""
    webapp = {
        "flezen": settings.flezen_webapp_url,
        "diskwala": settings.diskwala_webapp_url,
        "vidbunker": settings.vidbunker_webapp_url,
    }.get(name) or base["webapp_url"]
    tg_bot = {
        "flezen": settings.flezen_tg_bot,
        "diskwala": settings.diskwala_tg_bot,
        "vidbunker": settings.vidbunker_tg_bot,
    }.get(name) or base["tg_bot"]
    aes = {
        "flezen": settings.flezen_aes_key,
        "diskwala": settings.diskwala_aes_key,
        "vidbunker": "",
    }.get(name) or base["aes_key_hex"]
    bot_id = {
        "flezen": settings.flezen_bot_id,
        "diskwala": settings.diskwala_bot_id,
        "vidbunker": settings.vidbunker_bot_id,
    }.get(name) or base["bot_id"]
    if env_download:
        base["download_url"] = env_download
    if env_status:
        base["status_url"] = env_status
    base["webapp_url"] = webapp or base["webapp_url"]
    base["origin"] = _origin_of(base["webapp_url"]) or base["origin"]
    base["tg_bot"] = tg_bot
    base["aes_key_hex"] = aes
    base["bot_id"] = bot_id
    return MiniAppSpec(name=name, source="settings", **base)


class MiniAppCatalog:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._specs: dict[str, MiniAppSpec] = {name: _seed_spec(name) for name in _DEFAULTS}
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._last_sync = 0.0
        self._last_error = ""

    def spec(self, name: str) -> MiniAppSpec:
        return self._specs.get(name) or _seed_spec(name)

    def snapshot(self) -> dict[str, Any]:
        return {
            "last_sync": self._last_sync,
            "last_sync_ago": _ago(self._last_sync),
            "last_error": self._last_error,
            "auto": bool(settings.miniapp_auto_sync),
            "interval_minutes": int(settings.miniapp_sync_interval_minutes or 15),
            "apps": {name: spec.snapshot() for name, spec in self._specs.items()},
        }

    def load_cached(self) -> None:
        raw = storage.kv_get(_KV_KEY)
        if not raw:
            return
        try:
            payload = json.loads(raw)
        except Exception:
            return
        apps = payload.get("apps") or {}
        for name, data in apps.items():
            if name not in _DEFAULTS or not isinstance(data, dict):
                continue
            try:
                self._specs[name] = MiniAppSpec(
                    name=name,
                    webapp_url=str(data.get("webapp_url") or _DEFAULTS[name]["webapp_url"]),
                    origin=str(data.get("origin") or _DEFAULTS[name]["origin"]),
                    bot_id=str(data.get("bot_id") or name),
                    download_url=str(data.get("download_url") or _DEFAULTS[name]["download_url"]),
                    status_url=str(data.get("status_url") or _DEFAULTS[name].get("status_url") or ""),
                    download_method=str(data.get("download_method") or "POST"),
                    status_method=str(data.get("status_method") or "GET"),
                    aes_key_hex=str(data.get("aes_key_hex") or _DEFAULTS[name].get("aes_key_hex") or ""),
                    tg_bot=str(data.get("tg_bot") or ""),
                    bundle=str(data.get("bundle") or ""),
                    fallbacks=list(data.get("fallbacks") or []),
                    synced_at=float(data.get("synced_at") or 0),
                    source=str(data.get("source") or "cache"),
                    error=str(data.get("error") or ""),
                )
            except Exception:
                continue
        self._last_sync = float(payload.get("last_sync") or 0)
        self._last_error = str(payload.get("last_error") or "")

    async def start(self) -> None:
        try:
            self.load_cached()
        except Exception as exc:
            log.warning("could not load mini-app catalog: %s", type(exc).__name__)
        if self._task is None or self._task.done():
            self._stop.clear()
            self._task = asyncio.create_task(self._loop(), name="miniapp-sync")
        if settings.miniapp_auto_sync:
            asyncio.create_task(self.refresh_all(force=False))

    async def shutdown(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None

    async def _loop(self) -> None:
        try:
            while not self._stop.is_set():
                minutes = max(5, int(settings.miniapp_sync_interval_minutes or 15))
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=minutes * 60)
                    return
                except asyncio.TimeoutError:
                    if settings.miniapp_auto_sync:
                        try:
                            await self.refresh_all(force=False)
                        except Exception as exc:
                            log.warning("mini-app auto-sync failed: %s", type(exc).__name__)
        except asyncio.CancelledError:
            return

    async def refresh_all(self, force: bool = False) -> dict[str, Any]:
        async with self._lock:
            errors: list[str] = []
            merged: dict[str, dict[str, Any]] = {name: {} for name in _DEFAULTS}
            for name in _DEFAULTS:
                try:
                    facts = await self._scrape_app(name)
                    for svc, payload in (facts.get("by_service") or {}).items():
                        bucket = merged.setdefault(svc, {})
                        for key in ("download_urls", "status_urls", "extra_urls"):
                            bucket.setdefault(key, [])
                            for item in payload.get(key) or []:
                                if item not in bucket[key]:
                                    bucket[key].append(item)
                        if payload.get("bot_id"):
                            bucket["bot_id"] = payload["bot_id"]
                        if payload.get("tg_bot"):
                            bucket["tg_bot"] = payload["tg_bot"]
                        if svc == name:
                            if facts.get("bundle"):
                                bucket.setdefault("bundles", []).append(facts["bundle"])
                            if facts.get("origin"):
                                bucket["origin"] = facts["origin"]
                            if facts.get("webapp_url"):
                                bucket["webapp_url"] = facts["webapp_url"]
                    if facts.get("aes_key_hex"):
                        for svc in ("flezen", "diskwala"):
                            merged.setdefault(svc, {})["aes_key_hex"] = facts["aes_key_hex"]
                except Exception as exc:
                    errors.append(f"{name}: {type(exc).__name__}: {exc}")
                    log.warning("mini-app scrape %s failed: %s", name, exc)
            now = time.time()
            for name, payload in merged.items():
                if name not in self._specs:
                    continue
                current = self._specs[name]
                downloads = payload.get("download_urls") or []
                statuses = payload.get("status_urls") or []
                changed = bool(downloads or statuses or payload.get("aes_key_hex") or payload.get("webapp_url"))
                if downloads:
                    current.download_url = downloads[0]
                    current.fallbacks = downloads[1:]
                if statuses:
                    current.status_url = statuses[0]
                    for extra in statuses[1:]:
                        if extra not in current.fallbacks:
                            current.fallbacks.append(extra)
                if payload.get("bot_id"):
                    current.bot_id = str(payload["bot_id"])
                if payload.get("aes_key_hex"):
                    current.aes_key_hex = str(payload["aes_key_hex"])
                if payload.get("tg_bot") and not current.tg_bot:
                    current.tg_bot = str(payload["tg_bot"])
                if payload.get("origin"):
                    current.origin = str(payload["origin"])
                if payload.get("webapp_url"):
                    current.webapp_url = str(payload["webapp_url"])
                bundles = payload.get("bundles") or []
                if bundles:
                    current.bundle = str(bundles[0])
                if changed or force:
                    current.synced_at = now
                    current.source = "live-js"
                    current.error = ""
                self._specs[name] = current
            self._last_sync = now
            self._last_error = "; ".join(errors)
            self._persist()
            try:
                if errors:
                    storage.log("warn", f"mini-app sync completed with errors: {self._last_error}")
                else:
                    storage.log("info", "mini-app catalog synced from live JS")
            except Exception:
                log.info("mini-app catalog synced (log store unavailable)")
            return self.snapshot()

    async def refresh(self, name: str, force: bool = True) -> MiniAppSpec:
        await self.refresh_all(force=force)
        return self.spec(name)

    async def _scrape_app(self, name: str) -> dict[str, Any]:
        current = self.spec(name)
        sources = await self._html_sources(name, current)
        combined: dict[str, Any] = {
            "by_service": {},
            "aes_key_hex": "",
            "bundle": "",
            "origin": current.origin,
            "webapp_url": current.webapp_url,
        }
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(25.0, connect=12.0),
            follow_redirects=True,
            headers={"user-agent": _UA, "accept": "*/*"},
        ) as client:
            for html_url in sources:
                try:
                    res = await client.get(html_url)
                    res.raise_for_status()
                except Exception as exc:
                    log.info("mini-app html %s failed: %s", html_url, type(exc).__name__)
                    continue
                final = str(res.url)
                origin = _origin_of(final)
                combined["origin"] = origin or combined["origin"]
                combined["webapp_url"] = origin + "/" if origin else combined["webapp_url"]
                html = res.text
                scripts = _script_urls(html, final)
                for script in scripts[:_MAX_BUNDLES]:
                    try:
                        js_res = await client.get(script)
                        if js_res.status_code != 200:
                            continue
                        if len(js_res.content) > _MAX_BUNDLE_BYTES:
                            continue
                        js = js_res.text
                    except Exception:
                        continue
                    facts = extract_from_js(js)
                    if not combined["bundle"]:
                        combined["bundle"] = script
                    if facts.get("aes_key_hex") and not combined["aes_key_hex"]:
                        combined["aes_key_hex"] = facts["aes_key_hex"]
                    for svc, payload in (facts.get("by_service") or {}).items():
                        bucket = combined["by_service"].setdefault(
                            svc,
                            {"download_urls": [], "status_urls": [], "extra_urls": [], "bot_id": svc, "tg_bot": ""},
                        )
                        for key in ("download_urls", "status_urls", "extra_urls"):
                            for item in payload.get(key) or []:
                                if item not in bucket[key]:
                                    bucket[key].append(item)
                        if payload.get("bot_id"):
                            bucket["bot_id"] = payload["bot_id"]
                        if payload.get("tg_bot"):
                            bucket["tg_bot"] = payload["tg_bot"]
                    # Follow same-origin chunk URLs mentioned in the bundle.
                    for chunk in _CHUNK_JS.findall(js)[:4]:
                        extra = urljoin(final, chunk)
                        if extra not in scripts and _same_host(extra, origin):
                            scripts.append(extra)
                if combined["by_service"]:
                    break
        return combined

    async def _html_sources(self, name: str, current: MiniAppSpec) -> list[str]:
        urls: list[str] = []
        webapp = (current.webapp_url or "").strip()
        if webapp:
            urls.append(webapp)
        try:
            from app.telegram_auth import telegram_auth

            launch = await telegram_auth.request_webview_url(name)
        except Exception:
            launch = None
        if launch:
            parsed = urlsplit(launch)
            origin = _origin_of(launch)
            clean = urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", "", ""))
            for candidate in (clean, origin + "/" if origin else ""):
                if candidate and candidate not in urls:
                    urls.insert(0, candidate)
            if origin and origin.rstrip("/") != _origin_of(webapp).rstrip("/"):
                log.info("mini-app %s webview origin moved to %s", name, origin)
        return list(dict.fromkeys(u for u in urls if u))

    def _persist(self) -> None:
        payload = {
            "last_sync": self._last_sync,
            "last_error": self._last_error,
            "apps": {name: asdict(spec) for name, spec in self._specs.items()},
        }
        try:
            storage.kv_set(_KV_KEY, json.dumps(payload))
        except Exception:
            log.exception("could not persist mini-app catalog")
        stamp = datetime.fromtimestamp(self._last_sync, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        updates: dict[str, str] = {"MINIAPP_LAST_SYNC": stamp}
        for name, spec in self._specs.items():
            mapping = _ENV_MAP.get(name) or {}
            data = asdict(spec)
            for field_name, env_key in mapping.items():
                value = data.get(field_name)
                if value in (None, "", []):
                    continue
                if field_name == "tg_bot":
                    current = {
                        "flezen": settings.flezen_tg_bot,
                        "diskwala": settings.diskwala_tg_bot,
                        "vidbunker": settings.vidbunker_tg_bot,
                    }.get(name) or ""
                    if current:
                        continue
                updates[env_key] = str(value)
        try:
            env_manager.set_many(updates)
        except Exception:
            log.exception("could not write mini-app values to .env")


def unwrap_file(file: dict, aes_key_hex: str | None = None) -> dict:
    """Decrypt `{_x,s,h,p}` AES-256-GCM envelopes used by DiskWala/Flezen."""
    if not file.get("_x"):
        return file
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:
        raise RuntimeError("cryptography is required for Mini App decryption.") from exc
    key_hex = (aes_key_hex or catalog.spec("diskwala").aes_key_hex or _DEFAULTS["diskwala"]["aes_key_hex"]).strip()
    key = bytes.fromhex(key_hex)
    iv = bytes.fromhex(file["s"])
    tag = bytes.fromhex(file["h"])
    ct = bytes.fromhex(file["p"])
    plaintext = AESGCM(key).decrypt(iv, ct + tag, None)
    return json.loads(plaintext.decode("utf-8"))


catalog = MiniAppCatalog()


def _legacy_twins(url: str) -> list[str]:
    """If a versioned path 404s, also try the unversioned sibling."""
    if not url:
        return []
    parsed = urlsplit(url)
    path = parsed.path
    twins: list[str] = []
    for suffix in ("w", "1", "2", "v2"):
        if path.endswith(suffix) and ("download" in path or "status" in path):
            stripped = path[: -len(suffix)]
            twins.append(urlunsplit((parsed.scheme, parsed.netloc, stripped, parsed.query, "")))
    if path.endswith("/download"):
        twins.extend(
            urlunsplit((parsed.scheme, parsed.netloc, path + extra, parsed.query, ""))
            for extra in ("w", "1")
        )
    if path.endswith("/status"):
        twins.extend(
            urlunsplit((parsed.scheme, parsed.netloc, path + extra, parsed.query, ""))
            for extra in ("w", "1")
        )
    return [u for u in twins if u and u != url]


async def queue_link(client: httpx.AsyncClient, spec: MiniAppSpec, link: str, headers: dict) -> httpx.Response:
    payload = {"link": link}
    hdrs = {**headers, "content-type": "application/json"}
    seen: set[str] = set()
    last: httpx.Response | None = None
    targets = [spec.download_url, *list(spec.fallbacks), *_legacy_twins(spec.download_url)]
    for target in targets:
        if not target or target in seen or _looks_status(target):
            continue
        seen.add(target)
        method = (spec.download_method or "POST").upper()
        if method == "GET":
            res = await client.get(target, params={"link": link, "url": link}, headers=headers)
        else:
            res = await client.post(target, json=payload, headers=hdrs)
        last = res
        if res.status_code != 404:
            spec.download_url = target
            return res
    if last is None:
        raise RuntimeError(f"{spec.name} has no download URL configured")
    return last


async def poll_link(client: httpx.AsyncClient, spec: MiniAppSpec, link: str, headers: dict) -> httpx.Response:
    seen: set[str] = set()
    last: httpx.Response | None = None
    targets = [spec.status_url, *list(spec.fallbacks), *_legacy_twins(spec.status_url)]
    for target in targets:
        if not target or target in seen or _looks_download(target):
            continue
        seen.add(target)
        res = await client.get(target, params={"link": link}, headers=headers)
        last = res
        if res.status_code != 404:
            spec.status_url = target
            return res
    if last is None:
        raise RuntimeError(f"{spec.name} has no status URL configured")
    return last
