from __future__ import annotations

import httpx

from app.providers.seventv import SevenTVProvider


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
