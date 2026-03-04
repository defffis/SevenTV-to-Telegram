from __future__ import annotations

import httpx
import pytest

from app.providers.seventv import SevenTVProvider, SevenTVProviderError


def test_seventv_provider_fetch_emotes_filters_by_kind_with_mocked_http() -> None:
    payload = {
        "emote_set": {
            "emotes": [
                {
                    "id": "one",
                    "name": "static_one",
                    "data": {
                        "id": "e1",
                        "name": "static_one",
                        "animated": False,
                        "aliases": ["🙂"],
                        "host": {
                            "url": "//cdn.7tv.app/emote/e1",
                            "files": [{"name": "1x.webp", "format": "webp", "width": 32, "height": 32}],
                        },
                    },
                },
                {
                    "id": "two",
                    "name": "anim_two",
                    "data": {
                        "id": "e2",
                        "name": "anim_two",
                        "animated": True,
                        "aliases": ["🔥"],
                        "host": {
                            "url": "//cdn.7tv.app/emote/e2",
                            "files": [{"name": "1x.gif", "format": "gif", "width": 32, "height": 32}],
                        },
                    },
                },
            ]
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
        return httpx.Response(200, json=payload)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = SevenTVProvider(seventv_user_id="user", client=client)

    emoji_only = provider.fetch_emotes("emoji")
    stickers_only = provider.fetch_emotes("stickers")

    assert [item.source_id for item in emoji_only] == ["e1"]
    assert [item.source_id for item in stickers_only] == ["e2"]


def test_seventv_provider_fetch_emotes_raises_when_emote_set_missing() -> None:
    payload = {"id": "user"}

    def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
        return httpx.Response(200, json=payload)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = SevenTVProvider(seventv_user_id="user", client=client)

    with pytest.raises(SevenTVProviderError, match="does not contain an active emote set"):
        provider.fetch_emotes("emoji")


def test_seventv_provider_fetches_emote_set_by_id_when_profile_contains_string_reference() -> None:
    profile_payload = {"emote_set": "set_123"}
    set_payload = {
        "id": "set_123",
        "emotes": [
            {
                "id": "three",
                "name": "anim_three",
                "data": {
                    "id": "e3",
                    "name": "anim_three",
                    "animated": True,
                    "aliases": ["🚀"],
                    "host": {
                        "url": "//cdn.7tv.app/emote/e3",
                        "files": [{"name": "1x.gif", "format": "gif", "width": 32, "height": 32}],
                    },
                },
            }
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith('/users/user'):
            return httpx.Response(200, json=profile_payload)
        if request.url.path.endswith('/emote-sets/set_123'):
            return httpx.Response(200, json=set_payload)
        return httpx.Response(404, json={})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = SevenTVProvider(seventv_user_id="user", client=client)

    assert [item.source_id for item in provider.fetch_emotes("stickers")] == ["e3"]


def test_seventv_provider_fetches_emote_set_from_twitch_connection() -> None:
    profile_payload = {
        "id": "user",
        "connections": [
            {"platform": "KICK", "emote_set_id": "set_kick"},
            {"platform": "TWITCH", "emote_set_id": "set_twitch"},
        ],
    }
    twitch_set_payload = {
        "id": "set_twitch",
        "emotes": [
            {
                "id": "four",
                "name": "static_four",
                "data": {
                    "id": "e4",
                    "name": "static_four",
                    "animated": False,
                    "aliases": ["✨"],
                    "host": {
                        "url": "//cdn.7tv.app/emote/e4",
                        "files": [{"name": "1x.webp", "format": "webp", "width": 32, "height": 32}],
                    },
                },
            }
        ],
    }

    called_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        called_paths.append(request.url.path)
        if request.url.path.endswith('/users/user'):
            return httpx.Response(200, json=profile_payload)
        if request.url.path.endswith('/emote-sets/set_twitch'):
            return httpx.Response(200, json=twitch_set_payload)
        return httpx.Response(404, json={})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = SevenTVProvider(seventv_user_id="user", client=client)

    assert [item.source_id for item in provider.fetch_emotes("emoji")] == ["e4"]
    assert any(path.endswith("/emote-sets/set_twitch") for path in called_paths)
    assert not any(path.endswith("/emote-sets/set_kick") for path in called_paths)
