from __future__ import annotations

from app.domain.models import SourceEmote


def render_animated(emote: SourceEmote) -> SourceEmote:
    """Нормализация для анимированных эмоутов (placeholder)."""
    if emote.checksum is None:
        emote.checksum = f"{emote.source_id}:animated"
    return emote
