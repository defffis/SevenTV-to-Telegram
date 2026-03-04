from __future__ import annotations

from app.config import Settings


def test_validate_required_raises_for_missing_values() -> None:
    settings = Settings(seventv_user_id="", telegram_bot_token="", telegram_bot_username="")

    try:
        settings.validate_required()
        assert False, "validate_required() should fail for missing required env vars"
    except RuntimeError as exc:
        message = str(exc)
        assert "SEVENTV_USER_ID" in message
        assert "TELEGRAM_BOT_TOKEN" in message
        assert "TELEGRAM_BOT_USERNAME" in message


def test_from_env_parses_and_normalizes_values(monkeypatch) -> None:
    monkeypatch.setenv("SHARD_SIZE", "77")
    monkeypatch.setenv("SEVENTV_USER_ID", "user")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_BOT_USER_ID", "42")
    monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "@my_bot")
    monkeypatch.setenv("TELEGRAM_API_BASE_URL", "https://api.telegram.org/")

    settings = Settings.from_env()

    assert settings.default_shard_size == 77
    assert settings.telegram_bot_user_id == 42
    assert settings.telegram_bot_username == "my_bot"
    assert settings.telegram_api_base_url == "https://api.telegram.org"
