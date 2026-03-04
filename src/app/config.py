from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


_TRUE_VALUES = {"1", "true", "yes", "on"}


def _load_local_dotenv(dotenv_path: Path = Path(".env")) -> None:
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _parse_int(name: str, default: int, min_value: int | None = None) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        value = default
    else:
        try:
            value = int(raw)
        except ValueError as exc:
            raise RuntimeError(f"{name} must be an integer, got: {raw}") from exc
    if min_value is not None and value < min_value:
        raise RuntimeError(f"{name} must be >= {min_value}, got: {value}")
    return value


def _parse_float(name: str, default: float, min_value: float | None = None) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        value = default
    else:
        try:
            value = float(raw)
        except ValueError as exc:
            raise RuntimeError(f"{name} must be a float, got: {raw}") from exc
    if min_value is not None and value < min_value:
        raise RuntimeError(f"{name} must be >= {min_value}, got: {value}")
    return value


def _parse_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in _TRUE_VALUES


@dataclass(frozen=True)
class Settings:
    render_cache_dir: str = ".cache/render"
    default_shard_size: int = 120
    seventv_user_id: str = ""
    seventv_emote_set_id: str = ""
    telegram_bot_token: str = ""
    telegram_bot_user_id: int = 0
    telegram_bot_username: str = ""
    telegram_set_base_name: str = "seventv"
    telegram_api_base_url: str = "https://api.telegram.org"
    telegram_max_retries: int = 5
    telegram_backoff_seconds: float = 0.5
    telegram_timeout_seconds: int = 30
    enable_animated: bool = True
    enable_video: bool = False

    def validate_required(self) -> None:
        missing: list[str] = []
        if not self.seventv_user_id:
            missing.append("SEVENTV_USER_ID")
        if not self.telegram_bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not self.telegram_bot_username:
            missing.append("TELEGRAM_BOT_USERNAME")
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    @classmethod
    def from_env(cls) -> "Settings":
        _load_local_dotenv()
        telegram_api_base_url = os.getenv("TELEGRAM_API_BASE_URL", "https://api.telegram.org").rstrip("/")
        if not telegram_api_base_url.startswith(("http://", "https://")):
            raise RuntimeError("TELEGRAM_API_BASE_URL must start with http:// or https://")
        return cls(
            render_cache_dir=os.getenv("RENDER_CACHE_DIR", ".cache/render"),
            default_shard_size=_parse_int("SHARD_SIZE", default=120, min_value=1),
            seventv_user_id=os.getenv("SEVENTV_USER_ID", "").strip(),
            seventv_emote_set_id=os.getenv("SEVENTV_EMOTE_SET_ID", "").strip(),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
            telegram_bot_user_id=_parse_int("TELEGRAM_BOT_USER_ID", default=0, min_value=0),
            telegram_bot_username=os.getenv("TELEGRAM_BOT_USERNAME", "").strip().lstrip("@"),
            telegram_set_base_name=os.getenv("TELEGRAM_SET_BASE_NAME", "seventv"),
            telegram_api_base_url=telegram_api_base_url,
            telegram_max_retries=_parse_int("TELEGRAM_MAX_RETRIES", default=5, min_value=0),
            telegram_backoff_seconds=_parse_float("TELEGRAM_BACKOFF_SECONDS", default=0.5, min_value=0.0),
            telegram_timeout_seconds=_parse_int("TELEGRAM_TIMEOUT_SECONDS", default=30, min_value=1),
            enable_animated=_parse_bool("ENABLE_ANIMATED", default=True),
            enable_video=_parse_bool("ENABLE_VIDEO", default=False),
        )


settings = Settings.from_env()
