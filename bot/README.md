# TeraDrop — multi-user Telegram downloader

TeraDrop accepts public links from Flezen, DiskWala, VidBunker, TeraBox, and
UpFiles. It resolves the available file options and lets a user stream, open a
direct link, or send the file into the chat.

MongoDB stores the durable state. A bounded priority queue prevents an
unbounded task fan-out when many users send links together; VIP, Super, and
Regular Premium tasks run ahead of free tasks.

## What changed

- **Large uploads:** Docker Compose now includes Telegram's local Bot API
  server. It removes the hosted Bot API's ~50 MB ceiling and supports files up
  to 2,000 MB, subject to disk space, bandwidth, and the configured limit.
- **Real upload progress:** files are sent as a streamed multipart request;
  the whole file is not read into memory.
- **Safer concurrency:** every handler is non-blocking. A bounded priority
  queue with per-user gates stops one account from starving others. VIP, Super,
  and Regular jobs still run ahead of free jobs.
- **Strict file isolation:** each download/upload owns
  `DOWNLOAD_DIR/u<user_id>/<job_id>/`. Parallel range writes use `pwrite` on
  that job's file only. Directories are deleted when the job ends, and a reaper
  clears leftovers. Two users can never share a path or a file handle.
- **Faster transfers:** a shared HTTP pool, off-thread disk I/O, atomic Mongo
  counters, and a larger Telegram connection pool keep the event loop moving
  while many users are in flight.
- **Admin controls:** `/owner` still opens the Telegram admin panel, and
  `/admin` opens the web control center protected by `ADMIN_PANEL_PASSWORD`.
  It manages plan prices, feature flags, limits, users, force-sub channels,
  log/dump destinations, Mini App status, **and the `.env` file**.
- **Live environment editor:** view, edit, and add any environment variable
  (including `BOT_TOKEN`) from the control center. Live keys such as
  `MAX_CONCURRENT`, `WELCOME_TEXT`, `MAINTENANCE`, and `ADMIN_PANEL_PASSWORD`
  apply without a reboot. Restart-required keys are written immediately; use
  **Restart process** when you change `BOT_TOKEN`, MongoDB, or the Bot API URL.
  Compose mounts `./.env` so edits persist on the host.
- **Automatic payments:** each premium plan creates a unique UPI QR order,
  verifies it through the Paytm proxy, activates the plan, and logs the sale to
  every configured log/dump channel while notifying the buyer and all admins.
- **Cleaner user experience:** compact headings, blockquotes, clearer errors,
  native styled navigation buttons, edited-in-place premium/payment screens,
  QR cleanup on cancellation, expired button protection, and per-user cached
  file actions.

## VPS Docker setup

1. Create the environment file:

   ```bash
   cp .env.example .env
   ```

2. Install dependencies before starting the bot:

   ```bash
   python -m pip install -r requirements.txt
   ```

   The package also includes `pyproject.toml` for deployment platforms that
   install Python dependencies from project metadata.

3. Add:

   - `BOT_TOKEN` from BotFather
   - `OWNER_IDS` with your numeric Telegram user id
   - `MONGODB_URI` for the database
   - `PAYTM_MID` and `UPI_ID` for automatic premium payments
   - `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` from `my.telegram.org`
    - `ADMIN_PANEL_PASSWORD` as the password for the web admin panel. Quote it
      in `.env` when it contains `#`, for example:

      ```env
      ADMIN_PANEL_PASSWORD="your-password#123"
      ```

4. Start the complete VPS stack:

   ```bash
   docker compose up -d --build
   ```

If the bot is started directly instead of through Docker, run it from the
directory containing both `app/` and `requirements.txt`:

```bash
python -m pip install -r requirements.txt
python -m app
```

Do not copy only the `app/` directory; the dependency files and `.env.example`
are part of the deployment package.

The stack starts three private/public components:

- `teradrop` — the bot and media/health server
- `telegram-bot-api` — the local Bot API used for uploads up to 2 GB
- `https` — Caddy, exposed publicly on port `6969`

The public endpoint is the value configured by `PUBLIC_HOST` and `PUBLIC_PORT`
(for example, `https://your-domain.example:6969`):

```text
https://your-domain.example:6969
```

Open `https://your-domain.example:6969/admin` and enter the value of
`ADMIN_PANEL_PASSWORD` to use the web control center. The password is kept only
for the current browser session and is sent over the configured HTTPS connection.
Never put it in a public repository or share it in a screenshot.

### Environment editor

The **Environment** tab lists every known variable, grouped and searchable.

- Secrets are masked until you reveal them.
- **live** badges apply to the running process as soon as you press Apply.
- **restart** badges (bot token, MongoDB, Bot API URL, download directory)
  are written to `.env` immediately. Use **Restart process** to pick them up;
  Docker `restart: unless-stopped` brings the container back with the new file.
- **Add variable** writes any custom `KEY=value` pair.

`MAX_CONCURRENT` resizes the worker pool without dropping in-flight jobs.

The bot itself listens on port `8080` only inside the Docker network. The local
Bot API listens on port `8081` only inside the Docker network, so the old
Railway-only `telegram-bot-api.railway.internal` URL is not used.

The existing `SOLVER_URL` is a separate resolver dependency and is not part of
the Telegram Bot API. Keep it pointed at a reachable solver service or replace
it with your own solver endpoint; `localhost:42271` inside the bot container
will not work unless a solver is running in that same container.

Open the VPS firewall/security group for TCP port `6969`:

```bash
sudo ufw allow 6969/tcp
```

### HTTPS certificate note

Because this deployment uses a bare IP address, the included `Caddyfile` uses
Caddy's internal certificate authority. Traffic is encrypted, but browsers and
Telegram may show a certificate warning because the certificate is not publicly
trusted. For a warning-free public WebApp, point a domain name at the VPS and
replace the Caddy site address with that domain so Caddy can obtain a trusted
certificate automatically. You can also replace `tls internal` with a
CA-issued certificate configuration.

This VPS package is intentionally deployed with Docker Compose because the
local Bot API must run beside the bot. Do not set
`BOT_API_URL` to `telegram-bot-api.railway.internal`; use the private Compose
address `http://telegram-bot-api:8081`.

## Important upload limitation

The local Bot API server is required for files above the hosted Bot API limit.
A normal Telegram user account's 2 GB upload allowance does not automatically
apply to bots. If `BOT_API_URL` is empty, TeraDrop deliberately keeps the
send-to-chat option at 49 MB and still exposes Stream and Direct.

`MAX_FILE_MB` can be set from `1` to `2000`. The owner can also use:

```text
/setlimit 2000
```

The effective value is always capped by the active Telegram transport.

## Owner controls

`/owner` opens the dashboard. The command equivalents remain available:

| Command | Action |
|---|---|
| `/stats` | Usage overview |
| `/users` | Recent users |
| `/logs` | Recent errors |
| `/broadcast <text>` | Message known users |
| `/ban <user_id>` / `/unban <user_id>` | Block or restore a user |
| `/auth <user_id>` / `/unauth <user_id>` | Manage private allow-list |
| `/maintenance on\|off` | Pause public processing |
| `/setwelcome` | Set or reply with a welcome message |
| `/setcaption <template>` | Set `{filename}`, `{size}`, `{url}` caption |
| `/setlimit <mb>` | Set the maximum send size |
| `/addpremium r\|s\|v <user_id> <days>` | Grant a premium plan manually |
| `/removepremium <user_id>` | Remove a premium plan |
| `/add_admin <user_id>` / `/remove_admin <user_id>` | Manage admins |
| `/addforcesub <channel> [invite_url]` / `/removeforcesub <channel>` | Manage force-sub channels; the bot auto-creates an invite when omitted |
| `/setstartphoto` / `/clearstartphoto` | Manage the `/start` photo |
| `/setplan <key> <price> <days> <batch> <total>` | Edit a plan; use `0` for unlimited total links |
| `/deleteplan <key>` | Hide a plan from new purchases |

From the **premium plans** section in `/owner`, use **add plan**, **edit**, or
**delete**. Add/edit expects one line in this format:

```text
key | name | short name | price | days | batch limit | total links
```

Use `0` for unlimited total links. The main user actions use Telegram's native
reply-button styles (`primary`, `success`, and `danger`), which require a recent
Telegram client; older clients show the same buttons without color styling.

## User limits

- Free: one link at a time, five links in a rolling 24-hour window, and five
  lifetime send-to-Telegram credits.
- Regular Premium: five links together, fifty total links, 14 days, ₹69.
- Super Premium: ten links together, 150 total links, 30 days, ₹149.
- VIP Premium: twenty links together, unlimited total links, 30 days, ₹249.
- Uploaded files use Telegram content protection and are deleted after 45
  minutes by default for every plan.

## Configuration

See `.env.example`. `MAX_CONCURRENT=3` is a safe starting point; increase it
only when the server has enough CPU, memory, disk throughput, and upstream
bandwidth for concurrent multi-hundred-megabyte transfers.

## Automatic Telegram WebApp auth

Flezen and DiskWala use Telegram Mini App `initData`, which is short-lived and
cannot be renewed by copying the old string or by signing in a bot account.
TeraDrop now supports an owner-controlled Telegram user session:

1. Set `SESSION_SECRET`, `TELEGRAM_API_ID`, and `TELEGRAM_API_HASH`.
2. Set `FLEZEN_TG_BOT` and `DISKWALA_TG_BOT` to the Telegram bot usernames that
   launch the two Mini Apps. The corresponding `*_WEBAPP_URL` values are in
   `.env.example`.
3. In the bot's private chat, run `/tglogin`.
4. Send the phone number, login code, and—if requested—the Telegram 2-step
   password. Each sensitive message is deleted immediately after receipt.
5. Use `/tgstatus` to check the connection and `/tglogout` to remove the
   encrypted session and cached initData.

The reusable Telethon session and refreshed initData are encrypted with
`SESSION_SECRET` before they are stored in MongoDB.
TeraDrop refreshes auth before expiry and retries a request once after a 401.
If a service changes its bot username or Mini App URL, update the matching
environment variables and restart the bot.

The public stream/direct page keeps its proof-of-work abuse check, but now has a
responsive dark delivery page, a poster-backed player, a direct-download
fallback when a source cannot be transcoded, and a visible error state instead
of a browser broken-player icon.

### Web player (HLS / TeraBox streams)

TeraBox HD links are often an `m3u8` playlist (HLS + MPEG-TS), not a raw MP4.
Chrome, Firefox, Android, and Telegram's in-app browser cannot play that in a
plain `<video type="video/mp4">` tag, which is why some Stream buttons showed a
broken player.

The delivery page now:

- detects HLS vs MP4 / WebM / MKV automatically
- plays HLS with **hls.js** (Safari/iOS uses native HLS)
- rewrites playlist segments through the bot so cookies, referers, and CORS
  stay valid inside Telegram WebView
- falls back to ffmpeg remux (`/media/<token>?t=transmux`) if the browser
  still cannot decode the source
- keeps a direct-download button on the same page

