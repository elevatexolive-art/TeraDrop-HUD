"""UpFiles resolver for upfiles.com / upfilesgo.com.

The live flow (verified against https://upfiles.com/uTNc):

  1. GET share URL. upfiles.com 302s to upfilesgo.com/<id>?auth_token=… then
     the file page. Form ``#free-download-form`` POSTs ``_token`` +
     ``download_type=free``. Button ``#link-button-free`` is disabled until
     the ad/vhit script unlocks it — never click ``text=Free Download``.

  2. Captcha page: form ``#file-captcha`` POSTs ``_token`` + ``action=captcha``
     + ``cf-turnstile-response``. Widget ``#captchaDownload``.
     Sitekey is in ``#app-config`` → ``turnstile_site_key``
     (currently ``0x4AAAAAACOs2qXUfX8e7LFB``). Do NOT use
     ``settings.turnstile_sitekey`` — that is the TeraBox key and is what
     made the Violetics solver 504.

  3. 5s countdown (``counter_value``), then ``.btn-download``. Direct link is
     the button href, a Content-Disposition response, or a CDN redirect.

Solver API (Violetics, ``SOLVER_URL`` / ``UPFILES_SOLVER_URL``)::

    POST {solver}/solve
    {"sitekey": "<upfiles key>", "siteurl": "https://upfilesgo.com/<id>", "timeout": 60}
    → {"token": "0...."}

    The HTTP client timeout must be payload timeout + 25s. Shorter client
    timeouts make Railway's TCP proxy RST the socket and httpx reports
    "Server disconnected without sending a response".
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

from app.resolver import FileInfo, ResolveResult, _fmt
from app.settings import settings
from app.solver import solve_turnstile, solver_bases_for

log = logging.getLogger("teradrop")

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

# Hard fallback if #app-config is missing. Live value as of 2026-09-15.
_UPFILES_SITEKEY = "0x4AAAAAACOs2qXUfX8e7LFB"

_FILE_ID_RE = re.compile(
    r"https?://(?:www\.)?upfiles(?:go)?\.com/([A-Za-z0-9]{3,})(?:[/?#]|$)",
    re.I,
)
_H1_RE = re.compile(
    r"Download:\s*(.+?)\s*\(\s*([\d.]+)\s*(B|KB|MB|GB|TB)\s*\)",
    re.I,
)
_TITLE_RE = re.compile(r"^\s*(.+?)\s*[·|]\s*UpFiles", re.I)
_SIZE_RE = re.compile(r"([\d.]+)\s*(B|KB|MB|GB|TB)\b", re.I)
_TOKEN_RE = re.compile(
    r'(?:name=["\']_token["\']\s+value=["\']|csrf-token"\s+content=["\'])([^"\']+)',
    re.I,
)
_SITEKEY_RE = re.compile(r'turnstile_site_key"\s*:\s*"([^"]+)"', re.I)
_COUNTER_RE = re.compile(r'"counter_value"\s*:\s*(\d+)')
_UNITS = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}


def _fail(url: str, message: str, t0: float) -> ResolveResult:
    kwargs: dict[str, Any] = dict(
        ok=False, message=message, host="upfiles", source_url=url
    )
    try:
        return ResolveResult(
            **kwargs, elapsed_ms=int((time.monotonic() - t0) * 1000)
        )
    except TypeError:
        return ResolveResult(**kwargs)


def _file_id(url: str) -> str:
    m = _FILE_ID_RE.search(url or "")
    return m.group(1) if m else ""


def _origin(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def _parse_size(text: str) -> tuple[int, str]:
    m = _SIZE_RE.search(text or "")
    if not m:
        return 0, "unknown"
    n = float(m.group(1))
    unit = m.group(2).upper()
    raw = int(n * _UNITS.get(unit, 1))
    label = f"{m.group(1)} {unit}"
    try:
        return raw, _fmt(raw) or label
    except Exception:
        return raw, label


def _parse_meta(html: str, fallback_url: str = "") -> dict[str, Any]:
    config: dict[str, Any] = {}
    config_m = re.search(
        r'<script[^>]+id=["\']app-config["\'][^>]*>(.*?)</script>',
        html or "",
        re.I | re.S,
    )
    if config_m:
        try:
            parsed = json.loads(config_m.group(1).strip())
            if isinstance(parsed, dict):
                config = parsed
        except (TypeError, ValueError):
            # Keep the regex fallbacks below for older UpFiles templates.
            pass

    name = ""
    size_text = ""
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html or "", re.I | re.S)
    h1_text = re.sub(r"<[^>]+>", "", h1.group(1)).strip() if h1 else ""
    hm = _H1_RE.search(h1_text)
    if hm:
        name = hm.group(1).strip()
        size_text = f"{hm.group(2)} {hm.group(3)}"
    if not name:
        title = re.search(r"<title[^>]*>(.*?)</title>", html or "", re.I | re.S)
        title_text = re.sub(r"<[^>]+>", "", title.group(1)).strip() if title else ""
        tm = _TITLE_RE.search(title_text)
        name = (tm.group(1) if tm else title_text).strip()
    if not size_text:
        desc = re.search(
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)',
            html or "",
            re.I,
        )
        if desc:
            sm = _SIZE_RE.search(desc.group(1))
            if sm:
                size_text = f"{sm.group(1)} {sm.group(2)}"
    raw, formatted = _parse_size(size_text or h1_text)
    token_m = _TOKEN_RE.search(html or "")
    sitekey_m = _SITEKEY_RE.search(html or "")
    counter_m = _COUNTER_RE.search(html or "")
    csrf = str(config.get("csrf") or (token_m.group(1) if token_m else ""))
    sitekey = str(config.get("turnstile_site_key") or (sitekey_m.group(1) if sitekey_m else ""))
    try:
        counter = int(config.get("counter_value") or (counter_m.group(1) if counter_m else 5))
    except (TypeError, ValueError):
        counter = 5
    return {
        "file_name": name or "download",
        "size": raw,
        "formatted_size": formatted,
        "csrf": csrf,
        "sitekey": sitekey or _fallback_sitekey(),
        "counter": counter,
        "file_id": _file_id(fallback_url),
    }


def _fallback_sitekey() -> str:
    return (
        str(getattr(settings, "upfiles_turnstile_sitekey", "") or "").strip()
        or _UPFILES_SITEKEY
    )


def _cookie_list(client: httpx.AsyncClient, page_url: str) -> list[dict[str, object]]:
    host = urlparse(page_url).hostname or "upfilesgo.com"
    cookies: list[dict[str, object]] = []
    try:
        for cookie in client.cookies.jar:
            domain = cookie.domain or host
            cookies.append(
                {
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": domain if str(domain).startswith(".") else domain,
                    "path": cookie.path or "/",
                    "secure": urlparse(page_url).scheme == "https",
                    "httpOnly": False,
                }
            )
    except Exception:
        for name, value in client.cookies.items():
            cookies.append(
                {
                    "name": name,
                    "value": value,
                    "domain": host,
                    "path": "/",
                    "secure": urlparse(page_url).scheme == "https",
                }
            )
    return cookies


async def _violetics_solve(siteurl: str, sitekey: str) -> str | None:
    """Talk to Violetics with a client timeout that outlives the solve."""
    if not sitekey:
        return None
    bases = solver_bases_for("upfiles_solver_url", "solver_url")
    if not bases:
        log.warning("upfiles solver URL is empty")
        return None
    to = max(45, int(getattr(settings, "solver_timeout", 60) or 60))
    log.info("upfiles violetics solve sitekey=%s siteurl=%s timeout=%s bases=%s", sitekey, siteurl, to, bases)
    return await solve_turnstile(siteurl, sitekey, timeout=to, bases=bases)


async def _playwright_page_token(
    siteurl: str,
    sitekey: str,
    html: str | None,
    cookies: list[dict[str, object]] | None,
) -> str | None:
    """Render the REAL captcha page (not a stub) and harvest the widget token."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            context = await browser.new_context(
                user_agent=_UA,
                locale="en-US",
                viewport={"width": 900, "height": 720},
            )
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )
            if cookies:
                try:
                    await context.add_cookies(cookies)  # type: ignore[arg-type]
                except Exception:
                    pass
            page = await context.new_page()
            if html:
                served = False

                async def _serve(route) -> None:
                    nonlocal served
                    req = route.request
                    if (
                        not served
                        and req.resource_type == "document"
                        and req.method == "GET"
                        and urlparse(req.url).netloc == urlparse(siteurl).netloc
                    ):
                        served = True
                        await route.fulfill(
                            status=200,
                            content_type="text/html; charset=utf-8",
                            body=html,
                        )
                    else:
                        await route.continue_()

                await page.route("**/*", _serve)
                try:
                    await page.goto(siteurl, wait_until="domcontentloaded", timeout=30000)
                finally:
                    try:
                        await page.unroute("**/*", _serve)
                    except Exception:
                        pass
            else:
                await page.goto(siteurl, wait_until="domcontentloaded", timeout=30000)

            try:
                frame = page.frame_locator("iframe[src*='challenges.cloudflare.com']").first
                await frame.locator("body").click(timeout=10000, position={"x": 28, "y": 28})
            except Exception:
                pass
            try:
                token = await page.wait_for_function(
                    """() => {
                      const nodes = document.querySelectorAll(
                        '[name="cf-turnstile-response"], textarea[name="cf-turnstile-response"], #cf-token'
                      );
                      for (const el of nodes) {
                        const v = (el.value || '').trim();
                        if (v.length > 20) return v;
                      }
                      return window.__upfilesToken || null;
                    }""",
                    timeout=28000,
                )
                value = await token.json_value() if token else None
            except PlaywrightTimeout:
                value = await page.evaluate(
                    """() => {
                      const el = document.querySelector('[name="cf-turnstile-response"]');
                      return (el && el.value) || window.__upfilesToken || '';
                    }"""
                )
            await browser.close()
            if isinstance(value, str) and len(value) > 20:
                log.info("upfiles playwright page token len=%s", len(value))
                return value
    except Exception as exc:
        log.warning("upfiles playwright page token error: %s", exc)
    return None


async def _get_token(
    siteurl: str,
    sitekey: str,
    *,
    html: str | None = None,
    cookies: list[dict[str, object]] | None = None,
) -> str | None:
    token = await _violetics_solve(siteurl, sitekey)
    if token:
        return token
    log.info("upfiles remote solver missed; trying in-browser widget on the real captcha page")
    return await _playwright_page_token(siteurl, sitekey, html, cookies)


# Content-types that are always site *assets*, never the downloadable file.
# "application/javascript", "application/font-woff", etc. all contain the
# substring "application/", which previously made _looks_like_file_url()
# misidentify UpFiles' own vendor-bootstrap-*.js bundle as the direct link.
_ASSET_CT = (
    "javascript", "ecmascript", "json+", "css", "font", "woff",
    "image/", "text/plain", "text/css", "text/javascript",
)
# URL shapes that are always static assets on the site's own build pipeline.
_ASSET_URL_RE = re.compile(
    r"/build/assets/|/static/|/assets/|\.(?:js|mjs|css|map|woff2?|ttf|eot|svg|png|jpe?g|gif|ico|webp)(?:$|\?)",
    re.I,
)


def _looks_like_file_url(url: str, headers: dict[str, str] | None = None) -> bool:
    headers = {k.lower(): v for k, v in (headers or {}).items()}
    cd = headers.get("content-disposition", "")
    ct = headers.get("content-type", "").lower()
    u = (url or "").lower()

    # Hard exclude: known static-asset URL shapes, regardless of headers.
    if u.startswith("http") and _ASSET_URL_RE.search(u):
        return False
    # Hard exclude: asset content-types, even if content-disposition is odd.
    if ct and any(x in ct for x in _ASSET_CT):
        return False

    if "attachment" in cd.lower():
        return True
    if ct and "text/html" not in ct and "application/json" not in ct:
        if any(
            x in ct
            for x in ("octet-stream", "zip", "x-rar", "x-7z", "video/", "audio/", "application/pdf")
        ):
            return True

    if not u.startswith("http"):
        return False
    host = (urlparse(u).hostname or "")
    on_host = "upfiles" in host
    if on_host and any(p in u for p in ("/download/", "/dl/", "/get/", "/dwn/")):
        if not any(x in u for x in ("/login", "/register", "/pricing", "/get-pro")):
            return True
    if not on_host and re.search(
        r"\.(zip|rar|7z|mp4|mkv|avi|pdf|exe|iso|tar|gz|apk)(?:$|\?)",
        u,
    ):
        return True
    if not on_host and re.search(
        r"/(?:download|downloads|file/download|files/|dl|dwn|get)/",
        urlparse(u).path,
    ):
        return True
    if not on_host and re.search(
        r"(?:[?&](?:download|filename|file|name)=|/download(?:$|\?))",
        u,
    ):
        return True
    return False


def _form_action(html: str, form_id: str, base: str) -> str:
    m = re.search(
        rf'<form[^>]+id=["\']{re.escape(form_id)}["\'][^>]*>', html or "", re.I
    )
    if m:
        am = re.search(r'action=["\']([^"\']*)["\']', m.group(0), re.I)
        if am and am.group(1):
            return urljoin(base, am.group(1))
    return base


def _extract_hrefs(html: str, base: str) -> list[str]:
    hrefs: list[str] = []
    for m in re.finditer(
        r"""<(?:a|button)[^>]+(?:href|data-href|data-url)=["']([^"']+)""",
        html or "",
        re.I,
    ):
        hrefs.append(urljoin(base, m.group(1)))
    out: list[str] = []
    seen: set[str] = set()
    for h in hrefs:
        if h in seen or h.startswith("javascript:") or h.rstrip("#") == base.rstrip("/"):
            continue
        seen.add(h)
        out.append(h)
    return out


def _first_file_form(html: str, base: str) -> tuple[str, dict[str, str]]:
    for m in re.finditer(r"<form\b([^>]*)>(.*?)</form>", html or "", re.I | re.S):
        attrs, body = m.group(1), m.group(2)
        fid = re.search(r'id=["\']([^"\']+)', attrs, re.I)
        if fid and fid.group(1) in ("foot-news", "newsletter", "free-download-form", "file-captcha"):
            continue
        if 'name="email"' in body and "download" not in body.lower():
            continue
        action_m = re.search(r'action=["\']([^"\']*)["\']', attrs, re.I)
        action = urljoin(base, action_m.group(1)) if action_m and action_m.group(1) else base
        fields: dict[str, str] = {}
        for inp in re.finditer(r"<input\b([^>]*)>", body, re.I):
            a = inp.group(1)
            nm = re.search(r'name=["\']([^"\']+)', a, re.I)
            if not nm:
                continue
            vm = re.search(r'value=["\']([^"\']*)', a, re.I)
            fields[nm.group(1)] = vm.group(1) if vm else ""
        if fields:
            return action, fields
    return "", {}


def _result(url: str, meta: dict[str, Any], direct: str, t0: float) -> ResolveResult:
    # Last line of defense: never hand back a link that is obviously a site
    # asset (JS/CSS/image/font bundle) even if something upstream slipped up.
    if _ASSET_URL_RE.search((direct or "").lower()):
        return _fail(
            url,
            "UpFiles: resolver picked up a site asset instead of the real "
            "file link. Please try again.",
            t0,
        )
    info = FileInfo(
        file_name=meta.get("file_name") or "download",
        size=int(meta.get("size") or 0),
        formatted_size=meta.get("formatted_size") or "unknown",
        fs_id=meta.get("file_id") or _file_id(url),
        direct_link=direct,
        stream_url=None,
        stream_hd_url=None,
    )
    return ResolveResult(
        ok=True,
        title=info.file_name,
        host="upfiles",
        source_url=url,
        files=[info],
        elapsed_ms=int((time.monotonic() - t0) * 1000),
        used_solver=True,
    )



def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={
            "User-Agent": _UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
        follow_redirects=True,
        timeout=httpx.Timeout(30.0, connect=15.0),
    )


def _headers(page_url: str) -> dict[str, str]:
    return {
        "Origin": _origin(page_url),
        "Referer": page_url,
        "Content-Type": "application/x-www-form-urlencoded",
    }


async def resolve(url: str) -> ResolveResult:
    t0 = time.monotonic()
    url = (url or "").strip().replace("\n", "").replace("\r", "")
    if not url:
        return _fail(url, "UpFiles: empty URL.", t0)
    if not _FILE_ID_RE.search(url) and "upfiles" not in url.lower():
        return _fail(url, "UpFiles: not an upfiles.com / upfilesgo.com link.", t0)

    async with _client() as client:
        try:
            r = await client.get(url)
        except Exception as exc:
            return _fail(url, f"UpFiles: could not load the share page ({exc}).", t0)
        if r.status_code >= 400:
            return _fail(url, f"UpFiles: HTTP {r.status_code} loading the share page.", t0)
        html = r.text
        page_url = str(r.url)
        if "Just a moment" in html or "cf-challenge" in html.lower():
            return _fail(
                url,
                "UpFiles: Cloudflare challenge on the share page. Retry in a moment.",
                t0,
            )
        if re.search(r"file (?:not found|was deleted|has been deleted|expired)", html, re.I):
            return _fail(url, "UpFiles: file not found or has been deleted.", t0)

        meta = _parse_meta(html, page_url)

        # Step 1 — free download form (skip the disabled button, POST directly)
        if 'id="free-download-form"' in html or 'name="download_type"' in html:
            action = _form_action(html, "free-download-form", page_url)
            r = await client.post(
                action,
                data={"_token": meta.get("csrf") or "", "download_type": "free"},
                headers=_headers(page_url),
            )
            if r.status_code == 419 or "Page Expired" in (r.text or ""):
                return _fail(url, "UpFiles: CSRF token expired. Try the link again.", t0)
            html = r.text
            page_url = str(r.url)
            if _looks_like_file_url(page_url, dict(r.headers)):
                return _result(url, meta, page_url, t0)
            meta = {**meta, **_parse_meta(html, page_url)}

        # Step 2 — Turnstile
        if 'id="file-captcha"' in html or 'id="captchaDownload"' in html:
            sitekey = meta.get("sitekey") or _fallback_sitekey()
            token = await _get_token(
                page_url,
                sitekey,
                html=html,
                cookies=_cookie_list(client, page_url),
            )
            if not token:
                bases = solver_bases_for("upfiles_solver_url", "solver_url")
                return _fail(
                    url,
                    "UpFiles: Turnstile solver did not return a token. "
                    "Check UPFILES_SOLVER_URL / SOLVER_URL is reachable "
                    f"({', '.join(bases) or 'unset'}) and give it ~60s. "
                    f"Sitekey in use: {sitekey}.",
                    t0,
                )
            action = _form_action(html, "file-captcha", page_url)
            r = await client.post(
                action,
                data={
                    "_token": meta.get("csrf") or "",
                    "action": "captcha",
                    "cf-turnstile-response": token,
                },
                headers=_headers(page_url),
            )
            if _looks_like_file_url(str(r.url), dict(r.headers)):
                return _result(url, meta, str(r.url), t0)
            html = r.text
            page_url = str(r.url)
            meta = {**meta, **_parse_meta(html, page_url)}
            if 'id="file-captcha"' in html or 'id="captchaDownload"' in html:
                return _fail(
                    url,
                    "UpFiles: captcha was rejected. The Turnstile token was invalid for this origin.",
                    t0,
                )

        # Keep the page returned by the captcha POST.  UpFiles' final form is
        # client-side countdown state, while the HTTP form submission to
        # /file/go redirects back to the plain share page.  Losing this HTML
        # is what made the old Playwright fallback miss #link-button.
        countdown_html = html

        for href in _extract_hrefs(html, page_url):
            if _looks_like_file_url(href):
                return _result(url, meta, href, t0)

        # Step 3 — countdown then download.
        #
        # UpFiles' final "/file/go" submit is gated by a client-side ad/vhit
        # script (see module docstring), not a plain form POST. Submitting
        # it ourselves over httpx bounces back to the plain share page 100%
        # of the time in production traces, and since the download looks
        # like a one-shot per-session action, that wasted POST very likely
        # burns the session before Playwright ever gets a turn. So we no
        # longer submit it over httpx here — we hand the already
        # captcha-passed page straight to Playwright, which can run the
        # real unlock script and click the button itself.
        wait_s = int(meta.get("counter") or 5) + 1

        # Last resort: open the already-authed session in Playwright and click Download
        direct = await _playwright_finish(
            page_url,
            client,
            meta,
            wait_s,
            countdown_html=countdown_html,
        )
        if direct:
            return _result(url, meta, direct, t0)

        return _fail(
            url,
            "UpFiles: could not extract the final download link after the countdown.",
            t0,
        )


async def _playwright_finish(
    page_url: str,
    client: httpx.AsyncClient,
    meta: dict[str, Any],
    wait_s: int,
    countdown_html: str | None = None,
) -> str | None:
    cookies = _cookie_list(client, page_url)
    try:
        timeout_s = max(30, int(getattr(settings, "upfiles_playwright_timeout", 90) or 90))
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            )
            context = await browser.new_context(user_agent=_UA, locale="en-US")
            if cookies:
                try:
                    await context.add_cookies(cookies)
                except Exception:
                    pass
            captured: dict[str, str] = {}

            def on_download(d) -> None:
                if d.url:
                    captured["url"] = d.url
                try:
                    asyncio.create_task(d.cancel())
                except Exception:
                    pass

            def on_response(resp) -> None:
                try:
                    # A successful form submit can be a document navigation,
                    # a download, or a CDN redirect.  Let the response
                    # headers decide instead of discarding all document
                    # responses (the old code discarded the useful one).
                    if _looks_like_file_url(resp.url, dict(resp.headers)):
                        captured.setdefault("url", resp.url)
                except Exception:
                    pass

            page = await context.new_page()
            page.on("download", on_download)
            page.on("response", on_response)

            if countdown_html:
                # Serve the HTML captured right after the Turnstile captcha
                # was accepted — complete with its still-valid CSRF token
                # and countdown state — as the response to the page's OWN
                # first navigation, instead of first making a real GET to
                # page_url and then overwriting the DOM with set_content().
                # That previous approach fired a second live request to the
                # gated endpoint before swapping in the snapshot, which is
                # exactly the kind of extra request that bounces UpFiles'
                # one-shot download session back to the plain share page
                # (see the httpx /file/go behaviour this replaced above).
                # Faking only the document response keeps every other
                # request — JS bundles, ad/vhit scripts, XHRs — going out
                # over the real network with matching cookies, so the
                # site's own unlock script runs normally and the origin
                # still lines up for relative URLs.
                served = False

                async def _serve_snapshot(route):
                    nonlocal served
                    request = route.request
                    if (
                        not served
                        and request.resource_type == "document"
                        and request.method == "GET"
                        and request.url.rstrip("/") == page_url.rstrip("/")
                    ):
                        served = True
                        await route.fulfill(
                            status=200,
                            content_type="text/html; charset=utf-8",
                            body=countdown_html,
                        )
                    else:
                        await route.continue_()

                await page.route("**/*", _serve_snapshot)
                try:
                    await page.goto(
                        page_url,
                        wait_until="domcontentloaded",
                        timeout=timeout_s * 1000,
                    )
                finally:
                    await page.unroute("**/*", _serve_snapshot)
            else:
                await page.goto(
                    page_url,
                    wait_until="domcontentloaded",
                    timeout=timeout_s * 1000,
                )

            # The counter is rendered by UpFiles' frontend bundle.  Waiting
            # here also gives that bundle time to attach its submit handler.
            await page.wait_for_timeout(max(1, wait_s) * 1000)
            try:
                await page.wait_for_selector(
                    "#link-button:not(.disabled), "
                    ".get-link-ready:not(.d-none), "
                    ".btn-download.is-ready, "
                    ".countdown.is-done, "
                    "a.btn-download[href^='http']",
                    timeout=min(timeout_s, wait_s + 25) * 1000,
                )
            except PlaywrightTimeout:
                # Some UpFiles revisions only remove the CSS disabled class
                # and leave the HTML disabled attribute in place.  Enable the
                # final download control only, never every page button.
                await page.evaluate(
                    """() => {
                      document.querySelectorAll('#link-button, .btn-download').forEach((el) => {
                        el.disabled = false;
                        el.removeAttribute('disabled');
                        el.classList.remove('disabled');
                      });
                    }"""
                )

            href = await page.evaluate(
                """() => {
                  const nodes = document.querySelectorAll(
                    'a.btn-download[href], a#link-button[href], ' +
                    '[data-url], [data-href]'
                  );
                  for (const node of nodes) {
                    const value = node.href || node.dataset.url || node.dataset.href || '';
                    if (value && value.startsWith('http')) return value;
                  }
                  return '';
                }"""
            )
            if href and _looks_like_file_url(href) and href.rstrip("/") != page_url.rstrip("/"):
                await browser.close()
                return href

            for sel in ("#link-button", "button.btn-download", "a.btn-download[href]"):
                loc = page.locator(sel).first
                try:
                    if await loc.count() > 0:
                        async with page.expect_download(timeout=15000) as info:
                            await loc.click(force=True)
                        dl = await info.value
                        url = dl.url
                        try:
                            await dl.cancel()
                        except Exception:
                            pass
                        await browser.close()
                        return url or captured.get("url")
                except Exception:
                    # The submit may navigate to a direct response without
                    # raising a Playwright download event.  Inspect both the
                    # captured response and the resulting page URL below.
                    pass
                await page.wait_for_timeout(1500)
                if captured.get("url"):
                    await browser.close()
                    return captured["url"]
                current = page.url
                if current and current.rstrip("/") != page_url.rstrip("/") and _looks_like_file_url(current):
                    await browser.close()
                    return current

            # A final DOM check covers versions that turn the button into an
            # anchor only after the click handler completes.
            href = await page.evaluate(
                """() => {
                  const nodes = document.querySelectorAll('a[href], [data-url], [data-href]');
                  for (const node of nodes) {
                    const value = node.href || node.dataset.url || node.dataset.href || '';
                    if (value && value.startsWith('http')) return value;
                  }
                  return '';
                }"""
            )
            if href and _looks_like_file_url(href):
                await browser.close()
                return href
            await browser.close()
            return captured.get("url")
    except Exception as exc:
        log.warning("upfiles playwright finish error: %s", exc)
        return None


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "https://upfiles.com/uTNc"

    async def _main() -> None:
        res = await resolve(target)
        print(json.dumps(getattr(res, "__dict__", res), default=str, indent=2))

    asyncio.run(_main())