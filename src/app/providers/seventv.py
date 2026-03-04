from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.domain.models import SourceEmote, SyncKind


logger = logging.getLogger(__name__)


class SevenTVProviderError(RuntimeError):
    """Ошибка при работе с SevenTV API."""


@dataclass(frozen=True)
class SevenTVEndpoints:
    base_url: str = "https://7tv.io/v3"


class SevenTVProvider:
    """Провайдер SevenTV с единым контрактом SourceEmote."""

    def __init__(self, seventv_user_id: str, client: httpx.Client, endpoints: SevenTVEndpoints | None = None) -> None:
        self.seventv_user_id = seventv_user_id
        self.client = client
        self.endpoints = endpoints or SevenTVEndpoints()

    def fetch_emotes(self, kind: SyncKind) -> list[SourceEmote]:
        profile = self.get_user_profile()
        active_set = self.get_active_emote_set(profile)
        emotes = self.get_active_set_emotes(active_set)

        if kind == "emoji":
            return [item for item in emotes if not item.is_animated]
        return [item for item in emotes if item.is_animated]

    def get_user_profile(self) -> dict[str, Any]:
        return self._request_json(f"/users/{self.seventv_user_id}")

    def get_active_emote_set(self, profile: dict[str, Any]) -> dict[str, Any]:
        root_emote_set = profile.get("emote_set")
        if isinstance(root_emote_set, dict):
            return root_emote_set

        root_emote_set_id = self._extract_emote_set_id(root_emote_set) or self._extract_emote_set_id(profile.get("emote_set_id"))
        if root_emote_set_id:
            return self._request_json(f"/emote-sets/{root_emote_set_id}")

        connections = profile.get("connections")
        if isinstance(connections, list):
            preferred_connections = sorted(
                [item for item in connections if isinstance(item, dict)],
                key=lambda connection: 0 if str(connection.get("platform", "")).upper() == "TWITCH" else 1,
            )

            for connection in preferred_connections:
                connection_emote_set = connection.get("emote_set")
                if isinstance(connection_emote_set, dict):
                    return connection_emote_set

                connection_emote_set_id = self._extract_emote_set_id(connection_emote_set) or self._extract_emote_set_id(
                    connection.get("emote_set_id")
                )
                if connection_emote_set_id:
                    return self._request_json(f"/emote-sets/{connection_emote_set_id}")

        logger.debug("SevenTV profile keys: %s", list(profile.keys()))
        logger.debug("SevenTV profile connections: %s", json.dumps(profile.get("connections", []), ensure_ascii=False)[:4000])
        raise SevenTVProviderError(
            "SevenTV profile does not contain an active emote set in root fields or connections"
        )

    @staticmethod
    def _extract_emote_set_id(value: Any) -> str | None:
        if isinstance(value, str) and value:
            return value

        if isinstance(value, dict):
            nested_id = value.get("id")
            if isinstance(nested_id, str) and nested_id:
                return nested_id

        return None

    def get_active_set_emotes(self, active_set: dict[str, Any]) -> list[SourceEmote]:
        raw_emotes = active_set.get("emotes")
        if not isinstance(raw_emotes, list):
            raise SevenTVProviderError("SevenTV active emote set has invalid emotes format")
        return [self._to_source_emote(item) for item in raw_emotes]

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    def _request_json(self, path: str) -> dict[str, Any]:
        try:
            response = self.client.get(f"{self.endpoints.base_url}{path}")
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise SevenTVProviderError("SevenTV API returned non-object payload")
            return payload
        except (httpx.TimeoutException, httpx.NetworkError):
            raise
        except httpx.HTTPStatusError as exc:
            raise SevenTVProviderError(f"SevenTV API error: {exc.response.status_code}") from exc
        except ValueError as exc:
            raise SevenTVProviderError("SevenTV API returned invalid JSON") from exc

    def _to_source_emote(self, payload: dict[str, Any]) -> SourceEmote:
        emote = payload.get("data") or {}
        host = emote.get("host") or {}
        files = host.get("files") if isinstance(host.get("files"), list) else []

        selected_file = self._select_file(files, is_animated=bool(emote.get("animated")))
        source_format = str(selected_file.get("format") or "webp")

        host_url = str(host.get("url") or "")
        image_url = self._build_image_url(host_url, selected_file)

        aliases = emote.get("aliases")
        if not isinstance(aliases, list):
            aliases = []

        source_hash = str(selected_file.get("name") or emote.get("id") or "") or None

        return SourceEmote(
            source_id=str(emote.get("id") or payload.get("id") or ""),
            name=str(payload.get("name") or emote.get("name") or ""),
            kind="emoji",
            image_url=image_url,
            is_animated=bool(emote.get("animated")),
            source_format=source_format,
            width=self._as_int(selected_file.get("width")),
            height=self._as_int(selected_file.get("height")),
            aliases=[str(alias) for alias in aliases],
            source_hash=source_hash,
        )

    def _select_file(self, files: list[dict[str, Any]], is_animated: bool) -> dict[str, Any]:
        if not files:
            return {}

        preferred_formats = ["gif", "webp", "png", "avif"] if is_animated else ["webp", "png", "avif", "gif"]

        def sort_key(file_item: dict[str, Any]) -> tuple[int, int]:
            fmt = str(file_item.get("format") or "")
            fmt_score = preferred_formats.index(fmt) if fmt in preferred_formats else len(preferred_formats)
            area = self._as_int(file_item.get("width")) or 0
            area *= self._as_int(file_item.get("height")) or 0
            return (fmt_score, -area)

        return sorted(files, key=sort_key)[0]

    @staticmethod
    def _build_image_url(host_url: str, file_item: dict[str, Any]) -> str:
        if not host_url:
            return ""
        clean_host_url = host_url if host_url.startswith("http") else f"https:{host_url}"

        file_name = file_item.get("name")
        if file_name:
            return f"{clean_host_url}/{file_name}"

        if file_item.get("format"):
            return f"{clean_host_url}/4x.{file_item['format']}"

        return f"{clean_host_url}/4x.webp"

    @staticmethod
    def _as_int(value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
