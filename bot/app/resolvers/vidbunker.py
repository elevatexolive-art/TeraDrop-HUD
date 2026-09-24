"""VidBunker resolver — single-request direct video link."""
from __future__ import annotations

import time
from urllib.parse import quote

import httpx

from app.resolver import FileInfo, ResolveResult, _fmt, _num
from app.settings import settings
from app.telegram_auth import telegram_auth

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


def _headers(init_data: str) -> dict:
    return {
        "user-agent": _UA,
        "origin": "https://vidbunker-ma.pages.dev",
        "referer": "https://vidbunker-ma.pages.dev/",
        "authorization": f"Bearer {init_data}",
        "x-bot-id": "vidbunker",
    }


async def resolve(url: str) -> ResolveResult:
    t0 = time.monotonic()
    url = url.strip().replace("\n", "").replace("\r", "")

    init_data = await telegram_auth.get_init_data("vidbunker")
    if not init_data:
        return ResolveResult(
            ok=False,
            message=(
                "VidBunker Telegram auth is not configured. "
                "Use /tglogin and set VIDBUNKER_TG_BOT."
            ),
            host="vidbunker",
            source_url=url,
        )

    headers = _headers(init_data)
    auth_retried = False

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(45.0, connect=15.0), follow_redirects=True
    ) as client:
        # Request the direct download URL
        params = {"url": url}
        try:
            res = await client.get(
                settings.vidbunker_api_url, params=params, headers=headers
            )
            if res.status_code == 401:
                if not auth_retried:
                    fresh = await telegram_auth.refresh("vidbunker", force=True)
                    if fresh:
                        headers = _headers(fresh)
                        auth_retried = True
                        res = await client.get(
                            settings.vidbunker_api_url,
                            params=params,
                            headers=headers,
                        )
                    else:
                        return ResolveResult(
                            ok=False,
                            message="VidBunker auth expired. Use /tgstatus.",
                            host="vidbunker",
                            source_url=url,
                        )
                if res.status_code == 401:
                    return ResolveResult(
                        ok=False,
                        message="VidBunker auth rejected after refresh.",
                        host="vidbunker",
                        source_url=url,
                    )
            res.raise_for_status()
            
            # ---- NEW: content-type aware parsing ----
            content_type = (res.headers.get("content-type") or "").lower()
            if "application/json" in content_type:
                try:
                    data = res.json()
                except Exception:
                    data = {"url": str(res.url)}
            elif res.status_code in (301, 302, 303, 307, 308):
                # Redirect to the CDN
                direct = res.headers.get("location") or str(res.url)
                data = {"url": direct}
            else:
                # Binary video/octet-stream — the API URL itself is the direct link.
                # The webproxy will stream it server-side with auth headers.
                data = {"url": str(res.url)}
                
        except httpx.HTTPStatusError as exc:
            return ResolveResult(
                ok=False,
                message=f"VidBunker API returned {exc.response.status_code}.",
                host="vidbunker",
                source_url=url,
            )
        except Exception as exc:
            return ResolveResult(
                ok=False,
                message=f"VidBunker request failed: {exc}",
                host="vidbunker",
                source_url=url,
            )

    # The API may return a JSON object, a redirect, or binary video.
    if isinstance(data, str):
        direct = data
        file_name = "video.mp4"
        size = 0
    else:
        direct = (
            data.get("url")
            or data.get("download_url")
            or data.get("downloadUrl")
            or data.get("stream_url")
            or data.get("streamUrl")
        )
        file_name = str(
            data.get("name") or data.get("filename") or "video.mp4"
        )
        size = _num(data.get("size") or data.get("sizebytes") or 0)
        
    if not direct:
        return ResolveResult(
            ok=False,
            message="VidBunker returned no download URL.",
            host="vidbunker",
            source_url=url,
        )

    info = FileInfo(
        file_name=file_name,
        size=size,
        formatted_size=_fmt(size) if size else "unknown",
        fs_id="",
        direct_link=str(direct),
        stream_url=str(direct),
        stream_hd_url=str(direct),
    )
    return ResolveResult(
        ok=True,
        title=info.file_name,
        host="vidbunker",
        source_url=url,
        files=[info],
        elapsed_ms=int((time.monotonic() - t0) * 1000),
    )