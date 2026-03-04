from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import SourceEmote


@dataclass(frozen=True)
class RenderSkipError(RuntimeError):
    reason: str


ANIMATED_FORMATS = {"gif", "webp", "tgs"}
VIDEO_FORMATS = {"webm", "mp4"}


def _convert_animated(emote: SourceEmote) -> SourceEmote:
    """Лёгкая нормализация animated-контента (без тяжёлой перекодировки)."""
    if emote.source_format in {"gif", "webp"}:
        emote.source_format = "webp"
    if emote.checksum is None:
        emote.checksum = f"{emote.source_id}:animated:{emote.source_format}"
    return emote


def _convert_video(emote: SourceEmote) -> SourceEmote:
    """Лёгкая нормализация video-контента."""
    emote.source_format = "webm"
    if emote.checksum is None:
        emote.checksum = f"{emote.source_id}:video:{emote.source_format}"
    return emote


def render_animated(emote: SourceEmote, enable_animated: bool, enable_video: bool) -> SourceEmote:
    """Подготавливает animated/video медиа либо пропускает с контролируемой ошибкой."""
    source_format = emote.source_format.lower()

    if source_format in ANIMATED_FORMATS:
        if not enable_animated:
            raise RenderSkipError("animated content is disabled by ENABLE_ANIMATED")
        return _convert_animated(emote)

    if source_format in VIDEO_FORMATS:
        if not enable_video:
            raise RenderSkipError("video content is disabled by ENABLE_VIDEO")
        return _convert_video(emote)

    raise RenderSkipError(f"unsupported animated/video format: {source_format}")
