from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app.domain.models import SourceEmote
from app.media.animated_render import RenderSkipError, render_animated
from app.media.static_render import render_static
from app.services.sync_service import SyncService


class _StubSevenTV:
    def __init__(self, emotes: list[SourceEmote]) -> None:
        self.emotes = emotes

    def fetch_emotes(self, kind: str) -> list[SourceEmote]:
        return [item for item in self.emotes if item.kind == kind]


class _StubTelegram:
    def read_current_state(self, kind: str) -> list:
        return []

    def apply(self, kind: str, to_create: list, to_update: list, to_delete: list, dry_run: bool) -> list:
        return []


class MediaRenderTests(unittest.TestCase):
    def _emote(self, **kwargs: object) -> SourceEmote:
        data = {
            "source_id": "1",
            "name": "test",
            "kind": "emoji",
            "image_url": "https://example.com/file.gif",
            "is_animated": False,
            "source_format": "gif",
        }
        data.update(kwargs)
        return SourceEmote(**data)

    def test_static_profile_uses_kind_based_checksum(self) -> None:
        item = self._emote(kind="emoji", source_format="png")
        rendered = render_static(item)
        self.assertEqual(rendered.source_format, "webp")
        self.assertIn(":emoji:webp:100", rendered.checksum or "")

    def test_animated_skip_when_disabled(self) -> None:
        item = self._emote(kind="stickers", is_animated=True, source_format="gif")
        with self.assertRaises(RenderSkipError):
            render_animated(item, enable_animated=False, enable_video=False)

    def test_service_skips_unsupported_emote_without_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            from app import config as config_module
            from app.services import sync_service as sync_service_module

            original_settings = config_module.settings
            patched_settings = original_settings.__class__(
                render_cache_dir=f"{tmpdir}/cache",
                enable_animated=True,
                enable_video=False,
            )
            config_module.settings = patched_settings
            sync_service_module.settings = patched_settings
            try:
                ok = self._emote(
                    source_id="ok",
                    kind="stickers",
                    is_animated=True,
                    source_format="gif",
                )
                bad = self._emote(
                    source_id="bad",
                    kind="stickers",
                    is_animated=True,
                    source_format="apng",
                )
                service = SyncService(seventv=_StubSevenTV([ok, bad]), telegram=_StubTelegram())
                plan = service.run(kind="stickers", dry_run=True)
                self.assertEqual(len(plan.skipped), 1)
                self.assertEqual(plan.skipped[0].source_id, "bad")
                self.assertEqual(len(plan.to_create), 1)
                self.assertEqual(plan.to_create[0].source_id, "ok")
            finally:
                config_module.settings = original_settings
                sync_service_module.settings = original_settings


if __name__ == "__main__":
    unittest.main()
