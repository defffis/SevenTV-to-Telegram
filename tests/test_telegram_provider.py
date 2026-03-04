from __future__ import annotations

from app.domain.models import TelegramTargetItem
from app.providers.telegram import TelegramProvider


class _MockTelegramProvider(TelegramProvider):
    def __init__(self) -> None:
        # Avoid reading real settings in tests.
        self.token = "token"
        self.bot_user_id = 123
        self.bot_username = "bot"
        self.set_base_name = "base"
        self.max_retries = 0
        self.base_backoff_seconds = 0.0
        self.api_base_url = "https://api.telegram.org/botTOKEN"
        self.calls: list[tuple[str, dict]] = []

    def _set_exists(self, set_name: str) -> bool:  # noqa: ARG002
        return True

    def _request(self, method: str, payload: dict):
        self.calls.append((method, payload))
        if method == "getStickerSet":
            return {
                "stickers": [
                    {
                        "file_id": "file-1",
                        "file_unique_id": "uniq-1",
                        "emoji": "😎",
                        "keywords": ["src-1"],
                    }
                ]
            }
        return {"ok": True}


def _item(source_id: str) -> TelegramTargetItem:
    return TelegramTargetItem(
        target_id=f"target-{source_id}",
        source_id=source_id,
        name=f"name-{source_id}",
        kind="emoji",
        telegram_file_id=f"file-{source_id}",
        emoji="😀",
    )


def test_mocked_telegram_provider_read_current_state() -> None:
    provider = _MockTelegramProvider()

    state = provider.read_current_state("emoji")

    assert len(state) == 1
    assert state[0].source_id == "src-1"
    assert state[0].fingerprint == "uniq-1"


def test_mocked_telegram_provider_apply_dry_run() -> None:
    provider = _MockTelegramProvider()

    operations = provider.apply(
        kind="emoji",
        to_create=[_item("create")],
        to_update=[_item("update")],
        to_delete=[_item("delete")],
        dry_run=True,
    )

    assert operations[0]["operation"] == "read_set"
    assert any(op["operation"] == "add_item" for op in operations)
    assert any(op["operation"] == "replace_item" for op in operations)
    assert any(op["operation"] == "delete_item" for op in operations)
