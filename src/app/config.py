from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    render_cache_dir: str = os.getenv("RENDER_CACHE_DIR", ".cache/render")
    default_shard_size: int = int(os.getenv("SHARD_SIZE", "120"))
    seventv_user_id: str = os.getenv("SEVENTV_USER_ID", "")


settings = Settings()
