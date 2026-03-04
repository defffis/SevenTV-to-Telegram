from __future__ import annotations

from app.domain.models import SourceEmote


def render_static(emote: SourceEmote) -> SourceEmote:
    """Нормализация для статичных эмоутов (placeholder)."""
    if emote.checksum is None:
        emote.checksum = f"{emote.source_id}:static"
    return emote
