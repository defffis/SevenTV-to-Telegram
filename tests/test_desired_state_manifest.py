from __future__ import annotations

import json
import sys
from pathlib import Path

from app.domain.models import SyncPlan, TargetSetPlan, TelegramTargetItem
from app.main import main


class _StubSettings:
    seventv_user_id = "user"
    seventv_emote_set_id = ""
    telegram_bot_token = "token"
    telegram_bot_username = "bot"

    def validate_required(self) -> None:
        return


class _StubSevenTVProvider:
    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003, D401
        return


class _StubTelegramProvider:
    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003, D401
        return


class _StubSyncService:
    def __init__(self, seventv, telegram) -> None:  # noqa: ANN001
        return

    def run(self, kind: str, **kwargs) -> SyncPlan:  # noqa: ANN003
        item = TelegramTargetItem(
            target_id="target-1",
            source_id=f"src-{kind}",
            name=f"name-{kind}",
            kind=kind,  # type: ignore[arg-type]
            telegram_file_id="file-1",
            emoji="😀",
        )
        shard = TargetSetPlan(kind=kind, shard_index=0, set_name=f"base_{kind}_001_by_bot", items=[item])
        return SyncPlan(kind=kind, source_count=1, current_count=0, shards=[shard])


def test_generates_desired_state_manifest(monkeypatch, tmp_path: Path) -> None:
    from app import main as main_module

    monkeypatch.setattr(main_module, "settings", _StubSettings())
    monkeypatch.setattr(main_module, "SevenTVProvider", _StubSevenTVProvider)
    monkeypatch.setattr(main_module, "TelegramProvider", _StubTelegramProvider)
    monkeypatch.setattr(main_module, "SyncService", _StubSyncService)

    report = tmp_path / "report.json"
    desired = tmp_path / "desired.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "sync",
            "--dry-run",
            "--kind",
            "emoji",
            "--report-path",
            str(report),
            "--desired-state-path",
            str(desired),
        ],
    )

    exit_code = main()

    assert exit_code == 0
    payload = json.loads(desired.read_text(encoding="utf-8"))
    assert "shards" in payload
    assert len(payload["shards"]) == 1
    assert payload["shards"][0]["set_name"] == "base_emoji_001_by_bot"
