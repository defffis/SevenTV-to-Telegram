from __future__ import annotations

from app.config import settings
from app.domain.diff import build_diff
from app.domain.models import SourceEmote, SyncKind, SyncPlan
from app.domain.planner import shard_target_sets
from app.media.animated_render import render_animated
from app.media.cache import RenderCache
from app.media.static_render import render_static
from app.providers.seventv import SevenTVProvider
from app.providers.telegram import TelegramProvider


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
    ) -> SyncPlan:
        # fetch
        source_items = self.seventv.fetch_emotes(kind)

        # normalize
        normalized = self._normalize(source_items, kind)

        # render
        rendered = self._render(normalized)

        # shard
        shards = shard_target_sets(kind, rendered, settings.default_shard_size, "seventv")

        # read current state
        current = self.telegram.read_current_state(kind)

        # diff
        to_create, to_update, to_delete = build_diff(rendered, current, force_full_resync=force_full_resync)

        # apply
        self.telegram.apply(kind, to_create, to_update, to_delete, dry_run=dry_run)

        # report
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
        )

    def _normalize(self, source_items: list[SourceEmote], kind: SyncKind) -> list[SourceEmote]:
        normalized: list[SourceEmote] = []
        for item in source_items:
            normalized.append(item.model_copy(update={"kind": kind}))
        return normalized

    def _render(self, source_items: list[SourceEmote]) -> list[SourceEmote]:
        rendered: list[SourceEmote] = []
        cache_state = self.cache.load()
        for item in source_items:
            if item.animated:
                item = render_animated(item)
            else:
                item = render_static(item)
            cache_state[item.source_id] = item.checksum or ""
            rendered.append(item)
        self.cache.save(cache_state)
        return rendered
