from __future__ import annotations

from app.domain.models import TelegramTargetItem
from app.domain.planner import shard_target_sets


def _item(source_id: str, kind: str = "emoji") -> TelegramTargetItem:
    return TelegramTargetItem(
        target_id=f"target-{source_id}",
        source_id=source_id,
        name=f"name-{source_id}",
        kind=kind,  # type: ignore[arg-type]
        telegram_file_id=f"file-{source_id}",
        emoji="😀",
    )


def test_sharding_respects_max_for_stickers_and_name_pattern() -> None:
    items = [_item(f"{idx:03d}", kind="stickers") for idx in range(121)]

    shards = shard_target_sets("stickers", items, shard_size=999, base_set_name="base", bot_username="@bot")

    assert len(shards) == 2
    assert len(shards[0].items) == 120
    assert len(shards[1].items) == 1
    assert shards[0].set_name == "base_stickers_001_by_bot"
    assert shards[1].set_name == "base_stickers_002_by_bot"
