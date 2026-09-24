from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _ids(raw: str) -> set[int]:
    out: set[int] = set()
    for part in (raw or "").replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(int(part))
        except ValueError:
            continue
    return out


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    bot_token: str = Field(default="", alias="BOT_TOKEN")
    owner_ids_raw: str = Field(default="", alias="OWNER_IDS")
    bot_public: bool = Field(default=True, alias="BOT_PUBLIC")
    authorized_ids_raw: str = Field(default="", alias="AUTHORIZED_IDS")
    force_sub_channel: str = Field(default="", alias="FORCE_SUB_CHANNEL")
    log_channel: str = Field(default="", alias="LOG_CHANNEL")
    dump_channel: str = Field(default="", alias="DUMP_CHANNEL")
    maintenance: bool = Field(default=False, alias="MAINTENANCE")
    # The local Bot API server supports uploads up to 2 GB.  Without it,
    # Telegram's hosted Bot API remains limited to roughly 50 MB.
    max_file_mb: int = Field(default=2000, alias="MAX_FILE_MB")
    max_concurrent: int = Field(default=3, alias="MAX_CONCURRENT")
    bot_name: str = Field(default="TeraDrop", alias="BOT_NAME")
    bot_username: str = Field(default="TeraDropBot", alias="BOT_USERNAME")
    welcome_text: str = Field(default="", alias="WELCOME_TEXT")
    caption_template: str = Field(default="{filename}\n{size}", alias="CAPTION_TEMPLATE")
    teraboxdl_url: str = Field(default="https://www.teraboxdl.site", alias="TERABOXDL_URL")
    solver_url: str = Field(default="http://caboose.proxy.rlwy.net:42271", alias="SOLVER_URL")
    
    # UpFiles specific settings
    upfiles_solver_url: str = Field(
        default="http://caboose.proxy.rlwy.net:42271",  # reuse existing solver
        alias="UPFILES_SOLVER_URL",
    )
    upfiles_playwright_timeout: int = Field(default=90, alias="UPFILES_PLAYWRIGHT_TIMEOUT")
    
    turnstile_sitekey: str = Field(default="0x4AAAAAAC3x1HiBz5IFyj7s", alias="TURNSTILE_SITEKEY")
    upfiles_turnstile_sitekey: str = Field(
        default="0x4AAAAAACOs2qXUfX8e7LFB",
        alias="UPFILES_TURNSTILE_SITEKEY",
    )
    solver_timeout: int = Field(default=60, alias="SOLVER_TIMEOUT")
    bot_api_url: str = Field(default="", alias="BOT_API_URL")
    telegram_api_id: int = Field(default=0, alias="TELEGRAM_API_ID")
    telegram_api_hash: str = Field(default="", alias="TELEGRAM_API_HASH")
    session_secret: str = Field(default="", alias="SESSION_SECRET")
    admin_panel_password: str = Field(default="", alias="ADMIN_PANEL_PASSWORD")
    telegram_auth_refresh_minutes: int = Field(default=40, alias="TELEGRAM_AUTH_REFRESH_MINUTES")
    mongodb_uri: str = Field(default="", alias="MONGODB_URI")
    mongodb_database: str = Field(default="downloader_bot", alias="MONGODB_DATABASE")
    payment_api_url: str = Field(
        default="https://paytm-3b6fa57ab6ab.herokuapp.com/",
        alias="PAYMENT_API_URL",
    )
    paytm_mid: str = Field(default="", alias="PAYTM_MID")
    upi_id: str = Field(default="", alias="UPI_ID")
    payment_verify_interval: int = Field(default=60, alias="PAYMENT_VERIFY_INTERVAL")
    payment_max_minutes: int = Field(default=15, alias="PAYMENT_MAX_MINUTES")
    amount_tolerance: float = Field(default=0.01, alias="AMOUNT_TOLERANCE")
    upi_payee_name: str = Field(default="premium downloader", alias="UPI_PAYEE_NAME")
    payment_log_channel_id: int = Field(default=0, alias="PAYMENT_LOG_CHANNEL_ID")
    owner_tag: str = Field(default="", alias="OWNER_TAG")
    free_links_per_24h: int = Field(default=5, alias="FREE_LINKS_PER_24H")
    free_send_file_lifetime: int = Field(default=5, alias="FREE_SEND_FILE_LIFETIME")
    auto_delete_minutes: int = Field(default=45, alias="AUTO_DELETE_MINUTES")
    max_queue_size: int = Field(default=1000, alias="MAX_QUEUE_SIZE")
    
    # Supported Mini Apps
    flezen_tg_bot: str = Field(default="", alias="FLEZEN_TG_BOT")
    flezen_webapp_url: str = Field(
        default="https://flezen-downloader.pages.dev/",
        alias="FLEZEN_WEBAPP_URL",
    )
    diskwala_tg_bot: str = Field(default="", alias="DISKWALA_TG_BOT")
    diskwala_webapp_url: str = Field(
        default="https://miniapp.diskwala.net/",
        alias="DISKWALA_WEBAPP_URL",
    )
    vidbunker_tg_bot: str = Field(default="vidbunkerbot", alias="VIDBUNKER_TG_BOT")
    vidbunker_webapp_url: str = Field(
        default="https://vidbunker-ma.pages.dev/",
        alias="VIDBUNKER_WEBAPP_URL",
    )
    vidbunker_api_url: str = Field(
        default="https://vidbunker-backend.dailyweb577.workers.dev/api/download",
        alias="VIDBUNKER_API_URL",
    )
    
    download_dir: Path = Field(default=Path("data/tmp"), alias="DOWNLOAD_DIR")
    data_dir: Path = Field(default=Path("data"), alias="DATA_DIR")
    health_port: int = Field(default=8080, alias="HEALTH_PORT")
    # Optional explicit override. If unset, we fall back to Railway's own
    # RAILWAY_PUBLIC_DOMAIN (auto-injected once a public domain is generated
    # for this service), so no manual configuration is usually needed.
    public_base_url_override: str = Field(default="", alias="PUBLIC_BASE_URL")

    @property
    def public_base_url(self) -> str:
        """Public https base URL for this service's own webpage, used to hide
        the real TeraBox stream/direct links behind our own domain. Empty
        means link-hiding is disabled and raw links are used as before."""
        explicit = (self.public_base_url_override or "").strip().rstrip("/")
        if explicit and "your-public-domain.example" not in explicit:
            return explicit
        domain = (os.environ.get("RAILWAY_PUBLIC_DOMAIN") or "").strip().rstrip("/")
        if domain:
            return f"https://{domain}"
        host = (os.environ.get("PUBLIC_HOST") or "").strip().rstrip("/")
        port = (os.environ.get("PUBLIC_PORT") or "").strip()
        if host:
            scheme = (os.environ.get("PUBLIC_SCHEME") or "https").strip().lower()
            suffix = f":{port}" if port else ""
            return f"{scheme}://{host}{suffix}"
        return ""

    @property
    def owner_ids(self) -> set[int]:
        return _ids(self.owner_ids_raw)

    @property
    def authorized_ids(self) -> set[int]:
        return _ids(self.authorized_ids_raw)

    @property
    def max_file_bytes(self) -> int:
        return max(1, self.max_file_mb) * 1024 * 1024

    @property
    def telegram_api_root(self) -> str:
        raw = (self.bot_api_url or "").strip().rstrip("/")
        if not raw:
            return "https://api.telegram.org"
        if raw.endswith("/file/bot"):
            raw = raw[: -len("/file/bot")]
        if raw.endswith("/bot"):
            raw = raw[: -len("/bot")]
        return raw.rstrip("/")

    @property
    def bot_api_enabled(self) -> bool:
        return bool((self.bot_api_url or "").strip())

    @property
    def transport_max_file_mb(self) -> int:
        return 2000 if self.bot_api_enabled else 49

    @property
    def effective_max_file_mb(self) -> int:
        return max(1, min(max(1, self.max_file_mb), self.transport_max_file_mb))

    @property
    def effective_max_file_bytes(self) -> int:
        return self.effective_max_file_mb * 1024 * 1024

    def telegram_method_url(self, method: str) -> str:
        return f"{self.telegram_api_root}/bot{self.bot_token}/{method}"

    @property
    def resolver_hosts(self) -> list[str]:
        primary = (self.teraboxdl_url or "https://www.teraboxdl.site").rstrip("/")
        hosts = [primary, "https://www.teraboxdl.site", "https://teraboxdl.site"]
        out: list[str] = []
        for host in hosts:
            if host not in out:
                out.append(host)
        return out

    def is_owner(self, user_id: int) -> bool:
        return user_id in self.owner_ids

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.download_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()