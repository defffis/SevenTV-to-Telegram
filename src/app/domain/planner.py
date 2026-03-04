from __future__ import annotations

from app.domain.models import TargetSetPlan, TelegramTargetItem, SyncKind


def shard_target_sets(
    kind: SyncKind,
    items: list[TelegramTargetItem],
    shard_size: int,
    base_set_name: str,
) -> list[TargetSetPlan]:
    if shard_size <= 0:
        raise ValueError("shard_size must be > 0")

    shards: list[TargetSetPlan] = []
    for idx in range(0, len(items), shard_size):
        shard_number = idx // shard_size
        shard_items = items[idx : idx + shard_size]
        shards.append(
            TargetSetPlan(
                kind=kind,
                shard_index=shard_number,
                set_name=f"{base_set_name}_{kind}_{shard_number:02d}",
                items=shard_items,
            )
        )
    return shards
