"""Shared HTTP pool. Per-request headers keep user traffic isolated."""

from __future__ import annotations

import httpx

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(None, connect=20.0, pool=30.0),
            follow_redirects=True,
            limits=httpx.Limits(max_connections=96, max_keepalive_connections=32),
            http2=False,
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None
