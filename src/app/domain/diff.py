from __future__ import annotations

from app.domain.models import SourceEmote, TelegramTargetItem


def _preferred_emoji(source: SourceEmote) -> str:
    return source.aliases[0] if source.aliases else "😀"


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
        existing = current_by_source.get(source.source_id)
        candidate = TelegramTargetItem(
            target_id=(existing.target_id if existing else source.source_id),
            source_id=source.source_id,
            name=source.name,
            kind=source.kind,
            telegram_file_id=(existing.telegram_file_id if existing else None),
            emoji=_preferred_emoji(source),
            fingerprint=source.checksum,
        )

        if existing is None:
            to_create.append(candidate)
            continue

        if force_full_resync or any(
            [
                existing.fingerprint != candidate.fingerprint,
                existing.name != candidate.name,
                (existing.emoji or "😀") != candidate.emoji,
            ]
        ):
            to_update.append(candidate)

    to_delete = [item for item in current_items if item.source_id not in source_by_id]
    return to_create, to_update, to_delete
