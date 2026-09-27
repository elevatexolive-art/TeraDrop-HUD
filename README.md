# TeraDrop HUD

Live 3D operations console for TeraDrop. Not a static dashboard — a HUD with a
free-floating particle field (no connecting lines), orbital rings, scanlines,
and live telemetry.

## What you get

- **React control center** — sign in, overview, environment editor, runtime,
  plans, users, channels, Mini Apps, logs.
- **Particle field** — 3D projected points that drift and pulse independently.
  Nothing is joined with lines. Pauses when the tab is hidden, fewer particles
  on phones, respects reduced motion.
- **Live environment** — view, edit, and add `.env` keys including `BOT_TOKEN`.
- **Python bot** — isolated per-user download lanes, non-blocking handlers,
  bounded priority queue. Mini App APIs (Flezen / DiskWala / VidBunker) are
  scraped from the live JS bundles on a timer and on 404, then written into
  `.env` so the admin panel always shows the current endpoints. See `bot/`.

Preview password: `teradrop`.

## Fonts

Oxanium (display / readouts) + Rajdhani (body). Ice-cyan on void black.

## Deploy the HUD

This is a TanStack Start + Vite app. Platform deploy uses the existing
`npm run build` pipeline.

## Deploy the bot

```bash
cd bot
cp .env.example .env
docker compose up -d --build
```

Open `/admin` on the public host with `ADMIN_PANEL_PASSWORD`.

## Railway (Python bot)

This repo’s Railway config (`railway.json`) builds `Dockerfile.railway` — a
Python 3.12 image — so the container is not a Node HUD and `python` exists.

Railway exposes **one public HTTPS port (443)** on the generated domain and
forwards it to the container’s `PORT` (usually 8080):

| Where | Port | What |
| --- | --- | --- |
| Railway public URL | **443** | HTTPS in front of the bot |
| Container `PORT` / `HEALTH_PORT` | **8080** | `/` health, `/admin` panel, `/media/` streams, `/go/` links |
| Telegram | none inbound | Long-poll outbound to `api.telegram.org` |
| Solver (separate service) | **42271** | Turnstile solver only (`SOLVER_URL`) |

Do **not** generate a public domain on a Node/Nitro service for this bot.
After deploy, `/admin` is `https://<your-railway-domain>/admin`.

## VPS Docker Compose

| Port | What |
| --- | --- |
| **6969** | Public HTTPS via Caddy (admin, player, downloads) |
| **8080** | Bot HTTP, internal only |
| **8081** | Local Telegram Bot API, internal only |
