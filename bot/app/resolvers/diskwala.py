"""DiskWala resolver — POST /download to queue, then poll /status.
Handles the AES-256-GCM envelope (`_x`) the mini-app uses."""
from __future__ import annotations

import asyncio
import json
import time

import httpx

from app.resolver import FileInfo, ResolveResult, _fmt, _num
from app.telegram_auth import telegram_auth

_API = "https://api2.diskwala.net/api/diskwala"
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

# Hard-coded AES-256-GCM key from the DiskWala mini-app bundle.
_AES_KEY_HEX = "e7109544dab612bd5b80b8a427ac474ba5541b9efff7a4ca1c8ef85df2489c23"

_POLL_INTERVAL = 2.5
_POLL_TIMEOUT = 90.0


def _headers(init_data: str) -> dict:
    return {
        "user-agent": _UA,
        "origin": "https://miniapp.diskwala.net",
        "referer": "https://miniapp.diskwala.net/",
        "authorization": f"Bearer {init_data}",
        "x-bot-id": "diskwala",
    }


def _decrypt(payload: dict) -> dict:
    """Decrypt `{_x,s,h,p}` using AES-256-GCM (WebCrypto-compatible layout:
    IV = `s`, ciphertext = `p`, auth tag = `h`)."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:
        raise RuntimeError(
            "cryptography is required for DiskWala decryption. "
            "Add `cryptography==43.0.3` to requirements.txt."
        ) from exc
    key = bytes.fromhex(_AES_KEY_HEX)
    iv = bytes.fromhex(payload["s"])
    tag = bytes.fromhex(payload["h"])
    ct = bytes.fromhex(payload["p"])
    aes = AESGCM(key)
    plaintext = aes.decrypt(iv, ct + tag, None)
    return json.loads(plaintext.decode("utf-8"))


def _to_result(file: dict, url: str, t0: float) -> ResolveResult:
    name = str(file.get("name") or file.get("filename") or "video.mp4")
    size = _num(file.get("size"))
    direct = file.get("downloadUrl") or file.get("download_url") or file.get("url")
    stream = (file.get("streamUrl") or file.get("stream_url")
              or file.get("url") or direct)
    if not (direct or stream):
        return ResolveResult(ok=False, message="DiskWala returned no file URL.",
                             host="diskwala", source_url=url)
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
        ok=True, title=info.file_name, host="diskwala", source_url=url,
        files=[info], elapsed_ms=int((time.monotonic() - t0) * 1000),
    )


async def resolve(url: str) -> ResolveResult:
    t0 = time.monotonic()
    url = url.strip().replace("\n", "").replace("\r", "")
    init_data = await telegram_auth.get_init_data("diskwala")
    if not init_data:
        return ResolveResult(
            ok=False,
            message=("DiskWala Telegram auth is not configured. Use /tglogin from "
                     "the owner account and configure DISKWALA_TG_BOT."),
            host="diskwala", source_url=url,
        )
    headers = _headers(init_data)
    auth_retried = False
    async with httpx.AsyncClient(timeout=httpx.Timeout(45.0, connect=15.0),
                                 follow_redirects=True) as client:
        try:
            res = await client.post(
                f"{_API}/download",
                json={"link": url},
                headers={**headers, "content-type": "application/json"},
            )
            if res.status_code == 401:
                if not auth_retried:
                    fresh = await telegram_auth.refresh("diskwala", force=True)
                    if fresh:
                        headers = _headers(fresh)
                        auth_retried = True
                        res = await client.post(
                            f"{_API}/download",
                            json={"link": url},
                            headers={**headers, "content-type": "application/json"},
                        )
                    else:
                        return ResolveResult(ok=False, message="DiskWala Telegram auth expired. Use /tgstatus.",
                                             host="diskwala", source_url=url)
                if res.status_code == 401:
                    return ResolveResult(ok=False, message="DiskWala Telegram auth was rejected after refresh.",
                                         host="diskwala", source_url=url)
            res.raise_for_status()
            start = res.json()
        except httpx.HTTPStatusError as exc:
            return ResolveResult(ok=False, message=f"DiskWala queue failed: HTTP {exc.response.status_code}.",
                                 host="diskwala", source_url=url)
        except Exception as exc:
            return ResolveResult(ok=False, message=f"DiskWala queue error: {exc}",
                                 host="diskwala", source_url=url)

        if not start.get("ok"):
            return ResolveResult(
                ok=False,
                message=start.get("error") or "DiskWala refused the link.",
                host="diskwala", source_url=url,
            )

        deadline = time.monotonic() + _POLL_TIMEOUT
        while time.monotonic() < deadline:
            await asyncio.sleep(_POLL_INTERVAL)
            try:
                res = await client.get(f"{_API}/status",
                                       params={"link": url}, headers=headers)
                if res.status_code == 401:
                    if not auth_retried:
                        fresh = await telegram_auth.refresh("diskwala", force=True)
                        if fresh:
                            headers = _headers(fresh)
                            auth_retried = True
                            continue
                    return ResolveResult(ok=False, message="DiskWala Telegram auth expired. Use /tgstatus.",
                                         host="diskwala", source_url=url)
                res.raise_for_status()
                data = res.json()
            except Exception:
                continue

            if data.get("ok") and data.get("status") == "done":
                file = data.get("file") or {}
                if file.get("_x"):
                    try:
                        file = _decrypt(file)
                    except Exception as exc:
                        return ResolveResult(
                            ok=False,
                            message=f"DiskWala decrypt failed: {exc}",
                            host="diskwala", source_url=url,
                        )
                return _to_result(file, url, t0)
            if data.get("ok") and data.get("status") == "error":
                return ResolveResult(ok=False, message="DiskWala could not fetch the link.",
                                     host="diskwala", source_url=url)
        return ResolveResult(ok=False, message="DiskWala timed out after 90s.",
                             host="diskwala", source_url=url)
