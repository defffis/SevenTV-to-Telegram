from __future__ import annotations

from app.domain.diff import build_diff
from app.domain.models import SourceEmote, TelegramTargetItem


def _source(source_id: str, name: str = "name", aliases: list[str] | None = None, checksum: str = "v1") -> SourceEmote:
    return SourceEmote(
        source_id=source_id,
        name=name,
        kind="emoji",
        image_url="https://example.com/img.webp",
        source_format="webp",
        aliases=aliases or [],
        source_hash=checksum,
    )


def _current(source_id: str, name: str = "name", emoji: str = "😀", fingerprint: str = "v1") -> TelegramTargetItem:
    return TelegramTargetItem(
        target_id=f"tg-{source_id}",
        source_id=source_id,
        name=name,
        kind="emoji",
        telegram_file_id=f"file-{source_id}",
        emoji=emoji,
        fingerprint=fingerprint,
    )


def test_emoji_fallback_defaults_to_grinning_face() -> None:
    to_create, to_update, to_delete = build_diff([_source("1", aliases=[])], [])

    assert len(to_create) == 1
    assert to_create[0].emoji == "😀"
    assert to_update == []
    assert to_delete == []


def test_diff_logic_create_update_delete() -> None:
    source_items = [
        _source("create", aliases=["🔥"]),
        _source("update", name="new-name", aliases=["😎"], checksum="v2"),
    ]
    current_items = [
        _current("update", name="old-name", emoji="😀", fingerprint="old"),
        _current("delete"),
    ]

    to_create, to_update, to_delete = build_diff(source_items, current_items)

    assert [item.source_id for item in to_create] == ["create"]
    assert [item.source_id for item in to_update] == ["update"]
    assert [item.source_id for item in to_delete] == ["delete"]
