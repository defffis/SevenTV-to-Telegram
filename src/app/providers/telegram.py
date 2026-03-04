from __future__ import annotations

import logging

from app.domain.models import TelegramTargetItem, SyncKind

logger = logging.getLogger(__name__)


class TelegramProvider:
    """Заглушка Telegram API. Хранит состояние в памяти процесса."""

    def __init__(self) -> None:
        self._state: dict[SyncKind, list[TelegramTargetItem]] = {"emoji": [], "stickers": []}

    def read_current_state(self, kind: SyncKind) -> list[TelegramTargetItem]:
        return list(self._state[kind])

    def apply(
        self,
        kind: SyncKind,
        to_create: list[TelegramTargetItem],
        to_update: list[TelegramTargetItem],
        to_delete: list[TelegramTargetItem],
        dry_run: bool,
    ) -> None:
        logger.info(
            "Applying to Telegram: kind=%s create=%s update=%s delete=%s dry_run=%s",
            kind,
            len(to_create),
            len(to_update),
            len(to_delete),
            dry_run,
        )
        if dry_run:
            return

        remaining = [i for i in self._state[kind] if i.source_id not in {d.source_id for d in to_delete}]
        by_source = {i.source_id: i for i in remaining}

        for item in to_update:
            by_source[item.source_id] = item
        for item in to_create:
            by_source[item.source_id] = item

        self._state[kind] = list(by_source.values())
