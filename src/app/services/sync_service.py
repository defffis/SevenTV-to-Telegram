from __future__ import annotations

import logging

from app.config import settings
from app.domain.diff import build_diff
from app.domain.models import SkippedEmote, SourceEmote, SyncKind, SyncPlan, TelegramTargetItem
from app.domain.planner import shard_target_sets
from app.media.animated_render import RenderSkipError, render_animated
from app.media.cache import RenderCache
from app.media.static_render import render_static
from app.providers.seventv import SevenTVProvider
from app.providers.telegram import TelegramProvider

logger = logging.getLogger(__name__)


class SyncService:
    def __init__(self, seventv: SevenTVProvider, telegram: TelegramProvider) -> None:
        self.seventv = seventv
        self.telegram = telegram
        self.cache = RenderCache(f"{settings.render_cache_dir}/state.json")

    def run(
        self,
        kind: SyncKind,
        dry_run: bool = False,
        force_full_resync: bool = False,
        max_items: int | None = None,
    ) -> SyncPlan:
        source_items = self.seventv.fetch_emotes(kind)
        if max_items is not None:
            source_items = source_items[:max_items]
        normalized = self._normalize(source_items, kind)
        rendered, skipped = self._render(normalized)
        current = self.telegram.read_current_state(kind)

        to_create, to_update, to_delete = build_diff(rendered, current, force_full_resync=force_full_resync)

        if to_create or to_update or to_delete:
            self.telegram.apply(kind, to_create, to_update, to_delete, dry_run=dry_run)

        projected = self._project_state(current, to_create, to_update, to_delete)
        shards = shard_target_sets(
            kind,
            projected,
            settings.default_shard_size,
            settings.telegram_set_base_name,
            settings.telegram_bot_username,
        )

        return SyncPlan(
            kind=kind,
            source_count=len(source_items),
            current_count=len(current),
            dry_run=dry_run,
            force_full_resync=force_full_resync,
            to_create=to_create,
            to_update=to_update,
            to_delete=to_delete,
            shards=shards,
            skipped=skipped,
        )

    def _project_state(
        self,
        current: list[TelegramTargetItem],
        to_create: list[TelegramTargetItem],
        to_update: list[TelegramTargetItem],
        to_delete: list[TelegramTargetItem],
    ) -> list[TelegramTargetItem]:
        deleted_sources = {item.source_id for item in to_delete}
        by_source = {item.source_id: item for item in current if item.source_id not in deleted_sources}
        for item in to_update:
            by_source[item.source_id] = item
        for item in to_create:
            by_source[item.source_id] = item
        return list(by_source.values())

    def _normalize(self, source_items: list[SourceEmote], kind: SyncKind) -> list[SourceEmote]:
        normalized: list[SourceEmote] = []
        for item in source_items:
            normalized.append(item.model_copy(update={"kind": kind}))
        return normalized

    def _render(self, source_items: list[SourceEmote]) -> tuple[list[SourceEmote], list[SkippedEmote]]:
        rendered: list[SourceEmote] = []
        skipped: list[SkippedEmote] = []
        cache_state = self.cache.load()
        for item in source_items:
            try:
                if item.animated:
                    item = render_animated(
                        item,
                        enable_animated=settings.enable_animated,
                        enable_video=settings.enable_video,
                    )
                else:
                    item = render_static(item)
            except RenderSkipError as exc:
                logger.warning(
                    "Skipping emote '%s' (%s): %s",
                    item.name,
                    item.source_id,
                    exc.reason,
                )
                skipped.append(
                    SkippedEmote(
                        source_id=item.source_id,
                        name=item.name,
                        reason=exc.reason,
                    )
                )
                continue

            cache_state[item.source_id] = item.checksum or ""
            rendered.append(item)
        self.cache.save(cache_state)
        return rendered, skipped
