from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app.domain.models import TelegramTargetItem
from app.domain.planner import shard_target_sets


class PlannerTests(unittest.TestCase):
    def _item(self, source_id: str, kind: str = "emoji") -> TelegramTargetItem:
        return TelegramTargetItem(
            target_id=f"target_{source_id}",
            source_id=source_id,
            name=f"name_{source_id}",
            kind=kind,  # type: ignore[arg-type]
            telegram_file_id=f"file_{source_id}",
            emoji="😀",
        )

    def test_set_name_format_and_3_digit_index(self) -> None:
        items = [self._item("b"), self._item("a")]

        shards = shard_target_sets("emoji", items, shard_size=500, base_set_name="prefix", bot_username="@mybot")

        self.assertEqual(len(shards), 1)
        self.assertEqual(shards[0].set_name, "prefix_emoji_001_by_mybot")
        self.assertEqual([item.source_id for item in shards[0].items], ["a", "b"])

    def test_sticker_limit_applied_even_with_larger_shard_size(self) -> None:
        items = [self._item(f"{idx:03d}", kind="stickers") for idx in range(121)]

        shards = shard_target_sets("stickers", items, shard_size=500, base_set_name="prefix", bot_username="bot")

        self.assertEqual(len(shards), 2)
        self.assertEqual(len(shards[0].items), 120)
        self.assertEqual(len(shards[1].items), 1)
        self.assertEqual(shards[0].set_name, "prefix_stickers_001_by_bot")
        self.assertEqual(shards[1].set_name, "prefix_stickers_002_by_bot")

    def test_independent_planning_for_kinds(self) -> None:
        emoji_items = [self._item("1", kind="emoji")]
        sticker_items = [self._item("1", kind="stickers")]

        emoji_shards = shard_target_sets("emoji", emoji_items, shard_size=500, base_set_name="prefix", bot_username="bot")
        sticker_shards = shard_target_sets("stickers", sticker_items, shard_size=500, base_set_name="prefix", bot_username="bot")

        self.assertEqual(emoji_shards[0].set_name, "prefix_emoji_001_by_bot")
        self.assertEqual(sticker_shards[0].set_name, "prefix_stickers_001_by_bot")


if __name__ == "__main__":
    unittest.main()
