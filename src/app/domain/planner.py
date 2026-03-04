from __future__ import annotations

from app.domain.models import TargetSetPlan, TelegramTargetItem, SyncKind


TELEGRAM_MAX_ITEMS_PER_SET: dict[SyncKind, int] = {
    "emoji": 200,
    "stickers": 120,
}


def _build_set_name(base_set_name: str, kind: SyncKind, shard_number: int, bot_username: str) -> str:
    return f"{base_set_name}_{kind}_{shard_number:03d}_by_{bot_username}"


def _stable_items(items: list[TelegramTargetItem]) -> list[TelegramTargetItem]:
    return sorted(items, key=lambda item: (item.source_id, item.name, item.target_id))


def shard_target_sets(
    kind: SyncKind,
    items: list[TelegramTargetItem],
    shard_size: int,
    base_set_name: str,
    bot_username: str,
) -> list[TargetSetPlan]:
    if shard_size <= 0:
        raise ValueError("shard_size must be > 0")

    effective_shard_size = min(shard_size, TELEGRAM_MAX_ITEMS_PER_SET[kind])
    ordered_items = _stable_items(items)

    shards: list[TargetSetPlan] = []
    for idx in range(0, len(ordered_items), effective_shard_size):
        shard_number = idx // effective_shard_size + 1
        shard_items = ordered_items[idx : idx + effective_shard_size]
        shards.append(
            TargetSetPlan(
                kind=kind,
                shard_index=shard_number - 1,
                set_name=_build_set_name(base_set_name, kind, shard_number, bot_username.lstrip("@")),
                items=shard_items,
            )
        )
    return shards
