"""Flezen resolver — live Mini App catalog drives queue/status URLs."""
from __future__ import annotations

import asyncio
import time

import httpx

from app.miniapps import catalog, poll_link, queue_link, unwrap_file
from app.resolver import FileInfo, ResolveResult, _fmt, _num
from app.telegram_auth import telegram_auth

_POLL_INTERVAL = 2.5
_POLL_TIMEOUT = 90.0


def _to_result(file: dict, url: str, t0: float) -> ResolveResult:
    name = str(file.get("name") or file.get("filename") or file.get("fileName") or "video.mp4")
    size = _num(file.get("size") or file.get("fileSize"))
    direct = (
        file.get("url")
        or file.get("downloadUrl")
        or file.get("download_url")
        or file.get("downloadLink")
    )
    stream = (
        file.get("streamUrl")
        or file.get("stream_url")
        or file.get("url")
        or direct
    )
    if not (direct or stream):
        return ResolveResult(ok=False, message="Flezen returned no file URL.",
                             host="flezen", source_url=url)
    info = FileInfo(
        file_name=name,
        size=size,
        formatted_size=_fmt(size) if size else "unknown",
        fs_id=str(file.get("fsId") or file.get("fs_id") or ""),
        direct_link=str(direct) if direct else None,
        stream_url=str(stream or direct) if (stream or direct) else None,
        stream_hd_url=str(stream or direct) if (stream or direct) else None,
        thumb=file.get("thumb") or file.get("thumbnail") or None,
    )
    return ResolveResult(
        ok=True, title=info.file_name, host="flezen", source_url=url,
        files=[info], elapsed_ms=int((time.monotonic() - t0) * 1000),
    )


async def resolve(url: str) -> ResolveResult:
    t0 = time.monotonic()
    url = url.strip().replace("\n", "").replace("\r", "")
    init_data = await telegram_auth.get_init_data("flezen")
    if not init_data:
        return ResolveResult(
            ok=False,
            message=("Flezen Telegram auth is not configured. Use /tglogin from "
                     "the owner account and configure FLEZEN_TG_BOT."),
            host="flezen", source_url=url,
        )
    spec = catalog.spec("flezen")
    headers = spec.headers(init_data)
    auth_retried = False
    synced = False
    async with httpx.AsyncClient(timeout=httpx.Timeout(45.0, connect=15.0),
                                 follow_redirects=True) as client:
        try:
            res = await queue_link(client, spec, url, headers)
            if res.status_code == 404 and not synced:
                spec = await catalog.refresh("flezen", force=True)
                headers = spec.headers(init_data)
                synced = True
                res = await queue_link(client, spec, url, headers)
            if res.status_code == 401:
                if not auth_retried:
                    fresh = await telegram_auth.refresh("flezen", force=True)
                    if fresh:
                        headers = spec.headers(fresh)
                        auth_retried = True
                        res = await queue_link(client, spec, url, headers)
                    else:
                        return ResolveResult(ok=False, message="Flezen Telegram auth expired. Use /tgstatus.",
                                             host="flezen", source_url=url)
                if res.status_code == 401:
                    return ResolveResult(ok=False, message="Flezen Telegram auth was rejected after refresh.",
                                         host="flezen", source_url=url)
            res.raise_for_status()
            start = res.json()
        except httpx.HTTPStatusError as exc:
            return ResolveResult(ok=False, message=f"Flezen queue failed: HTTP {exc.response.status_code}.",
                                 host="flezen", source_url=url)
        except Exception as exc:
            return ResolveResult(ok=False, message=f"Flezen queue error: {exc}",
                                 host="flezen", source_url=url)

        if not start.get("ok"):
            return ResolveResult(
                ok=False,
                message=start.get("error") or "Flezen refused the link.",
                host="flezen", source_url=url,
            )

        deadline = time.monotonic() + _POLL_TIMEOUT
        while time.monotonic() < deadline:
            await asyncio.sleep(_POLL_INTERVAL)
            try:
                res = await poll_link(client, spec, url, headers)
                if res.status_code == 404 and not synced:
                    spec = await catalog.refresh("flezen", force=True)
                    headers = spec.headers(init_data)
                    synced = True
                    continue
                if res.status_code == 401:
                    if not auth_retried:
                        fresh = await telegram_auth.refresh("flezen", force=True)
                        if fresh:
                            headers = spec.headers(fresh)
                            auth_retried = True
                            continue
                    return ResolveResult(ok=False, message="Flezen Telegram auth expired. Use /tgstatus.",
                                         host="flezen", source_url=url)
                res.raise_for_status()
                data = res.json()
            except Exception:
                continue

            if data.get("ok") and data.get("status") == "done":
                try:
                    file = unwrap_file(data.get("file") or {}, spec.aes_key_hex)
                except Exception as exc:
                    return ResolveResult(ok=False, message=f"Flezen decrypt failed: {exc}",
                                         host="flezen", source_url=url)
                return _to_result(file, url, t0)
            if data.get("ok") and data.get("status") == "error":
                return ResolveResult(ok=False, message="Flezen could not fetch the link.",
                                     host="flezen", source_url=url)
        return ResolveResult(ok=False, message="Flezen timed out after 90s.",
                             host="flezen", source_url=url)
