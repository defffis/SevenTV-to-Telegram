from __future__ import annotations

from app.domain.models import SourceEmote, TelegramTargetItem


def build_diff(
    source_items: list[SourceEmote],
    current_items: list[TelegramTargetItem],
    force_full_resync: bool = False,
) -> tuple[list[TelegramTargetItem], list[TelegramTargetItem], list[TelegramTargetItem]]:
    current_by_source = {item.source_id: item for item in current_items}
    source_by_id = {item.source_id: item for item in source_items}

    to_create: list[TelegramTargetItem] = []
    to_update: list[TelegramTargetItem] = []
    for source in source_items:
        candidate = TelegramTargetItem(
            target_id=source.source_id,
            source_id=source.source_id,
            name=source.name,
            kind=source.kind,
            fingerprint=source.checksum,
        )
        existing = current_by_source.get(source.source_id)
        if existing is None:
            to_create.append(candidate)
            continue

        if force_full_resync or existing.fingerprint != candidate.fingerprint or existing.name != candidate.name:
            candidate.target_id = existing.target_id
            candidate.telegram_file_id = existing.telegram_file_id
            to_update.append(candidate)

    to_delete = [item for item in current_items if item.source_id not in source_by_id]
    return to_create, to_update, to_delete
