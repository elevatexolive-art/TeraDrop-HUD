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
  bounded priority queue. See `bot/`.

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
