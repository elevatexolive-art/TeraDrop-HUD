"""Flezen resolver — POST /download to queue, then poll /status."""
from __future__ import annotations

import asyncio
import time

import httpx

from app.resolver import FileInfo, ResolveResult, _fmt, _num
from app.telegram_auth import telegram_auth

_API = "https://api2.diskwala.net/api/flezen"
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

_POLL_INTERVAL = 2.5
_POLL_TIMEOUT = 90.0


def _headers(init_data: str) -> dict:
    return {
        "user-agent": _UA,
        "origin": "https://flezen-downloader.pages.dev",
        "referer": "https://flezen-downloader.pages.dev/",
        "authorization": f"Bearer {init_data}",
        "x-bot-id": "flezen",
    }


def _to_result(file: dict, url: str, t0: float) -> ResolveResult:
    name = str(file.get("name") or file.get("filename") or "video.mp4")
    size = _num(file.get("size"))
    direct = file.get("url") or file.get("downloadUrl") or file.get("download_url")
    stream = (file.get("streamUrl") or file.get("stream_url")
              or file.get("url") or direct)
    if not (direct or stream):
        return ResolveResult(ok=False, message="Flezen returned no file URL.",
                             host="flezen", source_url=url)
    info = FileInfo(
        file_name=name,
        size=size,
        formatted_size=_fmt(size) if size else "unknown",
        fs_id="",
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
    headers = _headers(init_data)
    auth_retried = False
    async with httpx.AsyncClient(timeout=httpx.Timeout(45.0, connect=15.0),
                                 follow_redirects=True) as client:
        # 1) Queue the job
        try:
            res = await client.post(
                f"{_API}/download",
                json={"link": url},
                headers={**headers, "content-type": "application/json"},
            )
            if res.status_code == 401:
                if not auth_retried:
                    fresh = await telegram_auth.refresh("flezen", force=True)
                    if fresh:
                        headers = _headers(fresh)
                        auth_retried = True
                        res = await client.post(
                            f"{_API}/download",
                            json={"link": url},
                            headers={**headers, "content-type": "application/json"},
                        )
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

        # 2) Poll /status
        deadline = time.monotonic() + _POLL_TIMEOUT
        while time.monotonic() < deadline:
            await asyncio.sleep(_POLL_INTERVAL)
            try:
                res = await client.get(f"{_API}/status",
                                       params={"link": url}, headers=headers)
                if res.status_code == 401:
                    if not auth_retried:
                        fresh = await telegram_auth.refresh("flezen", force=True)
                        if fresh:
                            headers = _headers(fresh)
                            auth_retried = True
                            continue
                    return ResolveResult(ok=False, message="Flezen Telegram auth expired. Use /tgstatus.",
                                         host="flezen", source_url=url)
                res.raise_for_status()
                data = res.json()
            except Exception:
                continue

            if data.get("ok") and data.get("status") == "done":
                return _to_result(data.get("file") or {}, url, t0)
            if data.get("ok") and data.get("status") == "error":
                return ResolveResult(ok=False, message="Flezen could not fetch the link.",
                                     host="flezen", source_url=url)
        return ResolveResult(ok=False, message="Flezen timed out after 90s.",
                             host="flezen", source_url=url)
