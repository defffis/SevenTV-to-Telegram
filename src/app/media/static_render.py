from __future__ import annotations

from app.domain.models import SourceEmote


STATIC_PROFILE_BY_KIND = {
    "emoji": {
        "target_format": "webp",
        "max_side": 100,
    },
    "stickers": {
        "target_format": "webp",
        "max_side": 512,
    },
}


def render_static(emote: SourceEmote) -> SourceEmote:
    """Подготавливает static-медиа под профиль Telegram для emoji/stickers."""
    profile = STATIC_PROFILE_BY_KIND[emote.kind]
    target_format = profile["target_format"]

    if emote.source_format != target_format:
        emote.source_format = target_format

    if emote.checksum is None:
        emote.checksum = f"{emote.source_id}:static:{emote.kind}:{target_format}:{profile['max_side']}"
    return emote
