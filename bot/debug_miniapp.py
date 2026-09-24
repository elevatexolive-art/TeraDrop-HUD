"""Run this once locally to discover the real mini-app API."""
import asyncio
import json
import httpx

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

# ---- Edit these two values ----
FLEZEN_SHARE = "dajli19bjlnnuflkshs0k4ocfdp8lqu"
DISKWALA_SHARE = "6a96dfc106ba7ea03d969b9b"
# -------------------------------


def init_data() -> str:
    user = {"id": 6713514592, "first_name": "User", "last_name": "",
            "language_code": "en", "allows_write_to_pm": True, "photo_url": ""}
    return (f"user={json.dumps(user, separators=(',', ':'))}"
            f"&chat_instance=-6225860959919145804&chat_type=sender"
            f"&auth_date=1789391632")


async def probe(client, method, url, headers=None, params=None, data=None):
    try:
        r = await client.request(method, url, headers=headers, params=params, json=data)
        ct = r.headers.get("content-type", "")
        body_preview = r.text[:200].replace("\n", " ")
        return f"{r.status_code}  {ct[:40]:40}  {body_preview}"
    except Exception as e:
        return f"ERR  {type(e).__name__}: {e}"


async def main():
    h = {"user-agent": UA}
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
        print("=" * 80)
        print("FLEZEN probes")
        print("=" * 80)
        urls = [
            ("GET", f"https://flezen.com/s/{FLEZEN_SHARE}", None, None),
            ("GET", f"https://flezen.com/api/s/{FLEZEN_SHARE}", None, None),
            ("GET", f"https://flezen.com/api/share/{FLEZEN_SHARE}", None, None),
            ("GET", f"https://flezen.com/api/file/{FLEZEN_SHARE}", None, None),
            ("GET", f"https://flezen.com/api/download/{FLEZEN_SHARE}", None, None),
            ("GET", "https://flezen-downloader.pages.dev/api/download",
             {"url": f"https://flezen.com/s/{FLEZEN_SHARE}"}, None),
            ("GET", "https://flezen-downloader.pages.dev/api/resolve",
             {"url": f"https://flezen.com/s/{FLEZEN_SHARE}"}, None),
        ]
        for method, url, params, data in urls:
            out = await probe(c, method, url, headers=h, params=params, data=data)
            print(f"{method:5} {url[:70]:70}  ->  {out}")

        print()
        print("=" * 80)
        print("DISKWALA probes")
        print("=" * 80)
        urls = [
            ("GET", f"https://www.diskwala.com/app/{DISKWALA_SHARE}", None, None),
            ("GET", f"https://miniapp.diskwala.net/api/resolve",
             {"url": f"https://www.diskwala.com/app/{DISKWALA_SHARE}"}, None),
            ("GET", f"https://miniapp.diskwala.net/api/file/{DISKWALA_SHARE}", None, None),
            ("GET", f"https://miniapp.diskwala.net/api/get/{DISKWALA_SHARE}", None, None),
            ("POST", f"https://miniapp.diskwala.net/api/resolve", None,
             {"url": f"https://www.diskwala.com/app/{DISKWALA_SHARE}"}),
            ("POST", f"https://miniapp.diskwala.net/api/file", None,
             {"share_id": DISKWALA_SHARE}),
        ]
        for method, url, params, data in urls:
            out = await probe(c, method, url, headers=h, params=params, data=data)
            print(f"{method:5} {url[:70]:70}  ->  {out}")

        # Also try to fetch the SPA JS bundle to look for /api/ routes
        print()
        print("=" * 80)
        print("Looking for /api/ URLs in Flezen SPA bundle")
        print("=" * 80)
        r = await c.get("https://flezen-downloader.pages.dev/", headers=h)
        print("index.html status:", r.status_code)
        # find script src
        import re
        scripts = re.findall(r'<script[^>]+src="([^"]+)"', r.text)
        print("scripts found:", scripts[:5])
        for s in scripts[:3]:
            if s.startswith("/"):
                s = "https://flezen-downloader.pages.dev" + s
            js = await c.get(s, headers=h)
            api_urls = set(re.findall(r'["\'](/api/[^"\']+)["\']', js.text))
            api_urls |= set(re.findall(r'["\'](https?://[^"\']*api[^"\']*)["\']', js.text))
            if api_urls:
                print(f"  {s} -> API paths:")
                for u in sorted(api_urls):
                    print(f"     {u}")
            else:
                print(f"  {s} -> no /api/ paths found (size: {len(js.text)})")


if __name__ == "__main__":
    asyncio.run(main())
