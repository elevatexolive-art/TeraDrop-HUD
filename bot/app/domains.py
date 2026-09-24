from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

TERABOX_HOSTS = {
    "terabox.com", "terabox.app", "terabox.fun", "teraboxapp.com",
    "1024tera.com", "1024terabox.com", "nephobox.com", "freeterabox.com",
    "4funbox.com", "4funbox.co", "mirrobox.com", "momerybox.com",
    "tibibox.com", "terasharelink.com", "teraboxshare.com", "teraboxlink.com",
    "dubox.com", "teraboxcdn.com", "terafileshare.com",
}

DISKWALA_HOSTS = {"diskwala.com", "www.diskwala.com"}
FLEZEN_HOSTS = {"flezen-downloader.pages.dev", "flezen.com"}

LINK_RE = re.compile(
    r"https?://(?:www\.)?(?:terabox(?:app|cdn|share|link)?|1024tera(?:box)?|"
    r"nephobox|freeterabox|4funbox|mirrobox|momerybox|tibibox|"
    r"terasharelink|terafileshare|dubox)\.(?:com|app|fun|co)(?:/[^\s<>\"')]+)?",
    re.I,
)
DISKWALA_RE = re.compile(r"https?://(?:www\.)?diskwala\.com/app/[^\s<>\"')]+", re.I)
FLEZEN_RE = re.compile(r"https?://(?:flezen-downloader\.pages\.dev|flezen\.com/s)/[^\s<>\"')]+", re.I)
VIDBUNKER_RE = re.compile(
    r"https?://(?:www\.)?vidbunker\.(?:in|com)/watch/[A-Za-z0-9_-]+",
    re.I,
)
UPFILES_RE = re.compile(
    r"https?://(?:www\.)?(?:upfiles\.com|upfilesgo\.com)/[A-Za-z0-9_-]+",
    re.I,
)


def _host(value: str) -> str:
    return value.lower().removeprefix("www.")


def is_terabox_host(host: str) -> bool:
    return _host(host) in TERABOX_HOSTS


def extract_surl(url: str) -> str | None:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "surl" in qs and qs["surl"]:
        return qs["surl"][0]
    parts = [p for p in parsed.path.split("/") if p]
    for key in ("s", "share", "filelist"):
        if key in parts:
            i = parts.index(key)
            if i + 1 < len(parts):
                return parts[i + 1]
    if parts:
        return parts[-1]
    return None


def detect_links(text: str) -> list[dict[str, str | None]]:
    found: list[dict[str, str | None]] = []
    seen: set[str] = set()

    for match in LINK_RE.findall(text or ""):
        url = re.sub(r"[).,;]+$", "", match)
        parsed = urlparse(url)
        if not is_terabox_host(parsed.hostname or ""):
            continue
        if url in seen:
            continue
        seen.add(url)
        found.append({"url": url, "host": _host(parsed.hostname or ""), "surl": extract_surl(url)})

    for match in DISKWALA_RE.findall(text or ""):
        url = re.sub(r"[).,;]+$", "", match)
        if url in seen:
            continue
        seen.add(url)
        found.append({"url": url, "host": "diskwala", "surl": url.rstrip("/").split("/")[-1]})

    for match in FLEZEN_RE.findall(text or ""):
        url = re.sub(r"[).,;]+$", "", match)
        if url in seen:
            continue
        seen.add(url)
        found.append({"url": url, "host": "flezen", "surl": None})

    for match in VIDBUNKER_RE.findall(text or ""):
        url = re.sub(r"[).,;]+$", "", match)
        if url in seen:
            continue
        seen.add(url)
        found.append({"url": url, "host": "vidbunker", "surl": url.rstrip("/").split("/")[-1]})

    for match in UPFILES_RE.findall(text or ""):
        url = re.sub(r"[).,;]+$", "", match)
        if url in seen:
            continue
        seen.add(url)
        found.append({"url": url, "host": "upfiles", "surl": url.rstrip("/").split("/")[-1]})

    return found