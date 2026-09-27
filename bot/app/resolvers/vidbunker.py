"""VidBunker resolver — live Mini App catalog drives the download API."""
from __future__ import annotations

import time

import httpx

from app.miniapps import catalog
from app.resolver import FileInfo, ResolveResult, _fmt, _num
from app.telegram_auth import telegram_auth


async def _request(client: httpx.AsyncClient, spec, url: str, headers: dict) -> httpx.Response:
    payload = {"url": url}
    hdrs = {**headers, "content-type": "application/json"}
    targets = [spec.download_url, *list(spec.fallbacks)]
    last: httpx.Response | None = None
    seen: set[str] = set()
    for target in targets:
        if not target or target in seen:
            continue
        seen.add(target)
        method = (spec.download_method or "POST").upper()
        attempts = [method, "GET" if method != "GET" else "POST"]
        for verb in attempts:
            if verb == "GET":
                res = await client.get(target, params={"url": url, "link": url}, headers=headers)
            else:
                res = await client.post(target, json=payload, headers=hdrs)
            last = res
            if res.status_code not in {404, 405}:
                spec.download_url = target
                spec.download_method = verb
                return res
    if last is None:
        raise RuntimeError("VidBunker has no download URL configured")
    return last


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

    spec = catalog.spec("vidbunker")
    headers = spec.headers(init_data)
    auth_retried = False
    synced = False

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(45.0, connect=15.0), follow_redirects=True
    ) as client:
        try:
            res = await _request(client, spec, url, headers)
            if res.status_code == 404 and not synced:
                spec = await catalog.refresh("vidbunker", force=True)
                headers = spec.headers(init_data)
                synced = True
                res = await _request(client, spec, url, headers)
            if res.status_code == 401:
                if not auth_retried:
                    fresh = await telegram_auth.refresh("vidbunker", force=True)
                    if fresh:
                        headers = spec.headers(fresh)
                        auth_retried = True
                        res = await _request(client, spec, url, headers)
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

            content_type = (res.headers.get("content-type") or "").lower()
            if "application/json" in content_type:
                try:
                    data = res.json()
                except Exception:
                    data = {"url": str(res.url)}
            elif res.status_code in (301, 302, 303, 307, 308):
                direct = res.headers.get("location") or str(res.url)
                data = {"url": direct}
            else:
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

    if isinstance(data, str):
        direct = data
        file_name = "video.mp4"
        size = 0
    else:
        direct = (
            data.get("url")
            or data.get("link")
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
