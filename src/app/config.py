from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    render_cache_dir: str = os.getenv("RENDER_CACHE_DIR", ".cache/render")
    default_shard_size: int = int(os.getenv("SHARD_SIZE", "120"))
    seventv_user_id: str = os.getenv("SEVENTV_USER_ID", "")
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_bot_user_id: int = int(os.getenv("TELEGRAM_BOT_USER_ID", "0"))
    telegram_bot_username: str = os.getenv("TELEGRAM_BOT_USERNAME", "")
    telegram_set_base_name: str = os.getenv("TELEGRAM_SET_BASE_NAME", "seventv")
    telegram_api_base_url: str = os.getenv("TELEGRAM_API_BASE_URL", "https://api.telegram.org")
    telegram_max_retries: int = int(os.getenv("TELEGRAM_MAX_RETRIES", "5"))
    telegram_backoff_seconds: float = float(os.getenv("TELEGRAM_BACKOFF_SECONDS", "0.5"))
    telegram_timeout_seconds: int = int(os.getenv("TELEGRAM_TIMEOUT_SECONDS", "30"))
    enable_animated: bool = os.getenv("ENABLE_ANIMATED", "1").lower() in {"1", "true", "yes", "on"}
    enable_video: bool = os.getenv("ENABLE_VIDEO", "0").lower() in {"1", "true", "yes", "on"}


settings = Settings()
