from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

import httpx

from app.settings import settings

log = logging.getLogger("teradrop")

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

# Violetics (cv3inx/turnstile-solver) aborts at payload_timeout + 15s.
# The HTTP client MUST wait longer than that or the proxy RSTs the socket
# and httpx reports "Server disconnected without sending a response".
_RETRY_STATUS = {429, 502, 503, 504}
_RETRY_CODES = {"browser_error", "solver_error", "timeout", "network"}


@dataclass
class Clearance:
    cookies: dict[str, str] = field(default_factory=dict)
    user_agent: str = DEFAULT_UA
    token: str | None = None


def _unique_bases(*candidates: str) -> list[str]:
    out: list[str] = []
    for raw in candidates:
        val = (raw or "").strip().rstrip("/")
        if val and val not in out:
            out.append(val)
    return out


def solver_bases_for(*prefer: str) -> list[str]:
    """Prefer the given settings attrs, then fall back to SOLVER_URL."""
    found: list[str] = []
    for attr in prefer:
        found.extend(_unique_bases(str(getattr(settings, attr, "") or "")))
    found.extend(_unique_bases(str(getattr(settings, "solver_url", "") or "")))
    return _unique_bases(*found)


def _client(timeout_s: float) -> httpx.AsyncClient:
    # Fresh client, HTTP/1.1, no keep-alive. Railway TCP proxies and
    # aiohttp solvers both drop reused sockets, which is exactly the
    # "Server disconnected without sending a response" seen in UpFiles logs.
    return httpx.AsyncClient(
        timeout=httpx.Timeout(timeout_s, connect=15.0, read=timeout_s, write=30.0, pool=15.0),
        follow_redirects=False,
        http2=False,
        limits=httpx.Limits(max_keepalive_connections=0, max_connections=2),
        headers={
            "User-Agent": DEFAULT_UA,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Connection": "close",
        },
    )


def _pick_token(data: object) -> str | None:
    if isinstance(data, str):
        text = data.strip().strip('"')
        if len(text) > 40 and " " not in text[:40]:
            return text
        return None
    if not isinstance(data, dict):
        return None
    for key in ("token", "value", "code", "cf-turnstile-response", "solution"):
        val = data.get(key)
        if isinstance(val, str) and len(val) > 20:
            return val
        if isinstance(val, dict):
            nested = val.get("token") or val.get("response")
            if isinstance(nested, str) and len(nested) > 20:
                return nested
    return None


async def post_solver(
    path: str,
    payload: dict,
    *,
    bases: list[str] | None = None,
    timeout_s: float = 90.0,
    attempts: int = 4,
) -> dict:
    """POST JSON to the Violetics solver with retries on disconnect/5xx."""
    last: dict = {"error": "solver failed"}
    urls = bases or solver_bases_for("solver_url")
    if not urls:
        return {"error": "SOLVER_URL is empty", "error_code": "bad_request"}

    for base in urls:
        url = f"{base}{path}"
        for attempt in range(1, attempts + 1):
            try:
                async with _client(timeout_s) as client:
                    res = await client.post(url, json=payload)
                try:
                    data = res.json() if res.content else {}
                except Exception:
                    data = {"error": (res.text or "")[:300]}
                if not isinstance(data, dict):
                    data = {"data": data}
                data["_status"] = res.status_code
                data["_base"] = base
                token = _pick_token(data)
                if token:
                    data["token"] = token
                    return data
                code = str(data.get("error_code") or "")
                retryable = res.status_code in _RETRY_STATUS or code in _RETRY_CODES
                last = data
                log.warning(
                    "solver %s status=%s code=%s attempt=%s/%s err=%s",
                    url,
                    res.status_code,
                    code or "-",
                    attempt,
                    attempts,
                    str(data.get("error") or "")[:180],
                )
                if retryable and attempt < attempts:
                    await asyncio.sleep(1.4 * attempt)
                    continue
                if not retryable:
                    break
            except (
                httpx.RemoteProtocolError,
                httpx.ReadError,
                httpx.ConnectError,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.WriteError,
                httpx.PoolTimeout,
                httpx.TimeoutException,
                httpx.TransportError,
            ) as exc:
                last = {
                    "error": f"{type(exc).__name__}: {exc}",
                    "error_code": "network",
                    "_base": base,
                }
                log.warning(
                    "solver %s network attempt=%s/%s: %s",
                    url,
                    attempt,
                    attempts,
                    exc,
                )
                if attempt < attempts:
                    await asyncio.sleep(1.4 * attempt)
                    continue
        # try next base if any
    return last


async def solver_health(base: str | None = None) -> dict:
    url = (base or (solver_bases_for("solver_url")[0] if solver_bases_for("solver_url") else "")).rstrip("/")
    if not url:
        return {"status": "missing"}
    try:
        async with _client(8.0) as client:
            res = await client.get(url + "/health")
            data = res.json() if res.content else {}
            if isinstance(data, dict):
                data["_status"] = res.status_code
                return data
    except Exception as exc:
        return {"status": "down", "error": str(exc)}
    return {"status": "down"}


async def solve_challenge(siteurl: str, attempts: int = 3) -> Clearance:
    payload = {"siteurl": siteurl, "timeout": 70}
    data = await post_solver(
        "/solve-challenge",
        payload,
        bases=solver_bases_for("solver_url"),
        timeout_s=110.0,
        attempts=attempts,
    )
    if data.get("error") and not data.get("cookies"):
        raise RuntimeError(str(data.get("error") or "solver failed"))
    cookies: dict[str, str] = {}
    for item in data.get("cookies") or []:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        value = item.get("value")
        if name and value is not None:
            cookies[str(name)] = str(value)
    return Clearance(
        cookies=cookies,
        user_agent=str(data.get("user_agent") or DEFAULT_UA),
        token=_pick_token(data),
    )


async def solve_turnstile(
    siteurl: str,
    sitekey: str | None = None,
    *,
    timeout: int | None = None,
    bases: list[str] | None = None,
) -> str | None:
    key = (sitekey or settings.turnstile_sitekey or "").strip()
    if not key or not siteurl:
        return None
    to = int(timeout if timeout is not None else getattr(settings, "solver_timeout", 60) or 60)
    to = max(20, min(to, 180))
    payload = {"sitekey": key, "siteurl": siteurl, "timeout": to}
    data = await post_solver(
        "/solve",
        payload,
        bases=bases or solver_bases_for("solver_url"),
        timeout_s=float(to + 25),
        attempts=4,
    )
    token = _pick_token(data)
    if token:
        log.info(
            "solver turnstile ok sitekey=%s elapsed=%s len=%s",
            key,
            data.get("elapsed"),
            len(token),
        )
        return token
    log.warning(
        "solver turnstile miss sitekey=%s status=%s err=%s",
        key,
        data.get("_status"),
        str(data.get("error") or "")[:180],
    )
    return None
