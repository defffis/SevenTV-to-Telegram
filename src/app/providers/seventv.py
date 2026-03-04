from __future__ import annotations

from app.domain.models import SourceEmote, SyncKind


class SevenTVProvider:
    """Заглушка провайдера SevenTV."""

    def fetch_emotes(self, kind: SyncKind) -> list[SourceEmote]:
        # В реальном проекте здесь будет API-вызов SevenTV.
        return []
