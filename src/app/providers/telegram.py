from __future__ import annotations

import json
import logging
import random
import time
from typing import Any
from urllib import error, request

from app.config import settings
from app.domain.models import TelegramTargetItem, SyncKind

logger = logging.getLogger(__name__)


class TelegramApiError(RuntimeError):
    pass


class TelegramProvider:
    def __init__(self) -> None:
        self.token = settings.telegram_bot_token
        self.bot_user_id = settings.telegram_bot_user_id
        self.bot_username = settings.telegram_bot_username.lstrip("@")
        self.set_base_name = settings.telegram_set_base_name
        self.max_retries = settings.telegram_max_retries
        self.base_backoff_seconds = settings.telegram_backoff_seconds
        self.api_base_url = f"{settings.telegram_api_base_url}/bot{self.token}"

    def _managed_set_name(self, kind: SyncKind, shard_index: int = 0) -> str:
        return f"{self.set_base_name}_{kind}_{shard_index:02d}_by_{self.bot_username}"

    def _ensure_managed_set_name(self, set_name: str) -> None:
        required_suffix = f"_by_{self.bot_username}"
        if not set_name.endswith(required_suffix):
            raise ValueError(f"Refusing to operate unmanaged set '{set_name}'. Expected suffix: {required_suffix}")

    def _request(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        encoded = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.api_base_url}/{method}",
            data=encoded,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with request.urlopen(req, timeout=settings.telegram_timeout_seconds) as response:
                    raw_body = response.read().decode("utf-8")
                body = json.loads(raw_body)
                if body.get("ok"):
                    return body["result"]

                if body.get("error_code") == 429:
                    retry_after = float((body.get("parameters") or {}).get("retry_after", 1))
                    time.sleep(retry_after + random.uniform(0, 0.3))
                    continue

                raise TelegramApiError(f"Telegram API error on {method}: {body}")
            except error.HTTPError as exc:
                last_error = exc
                raw_error = exc.read().decode("utf-8", errors="ignore")
                try:
                    body = json.loads(raw_error) if raw_error else {}
                except json.JSONDecodeError:
                    body = {}

                if exc.code == 429:
                    retry_after = float((body.get("parameters") or {}).get("retry_after", 1))
                    time.sleep(retry_after + random.uniform(0, 0.3))
                    continue

                if exc.code >= 500 and attempt < self.max_retries:
                    time.sleep((self.base_backoff_seconds * (2**attempt)) + random.uniform(0, 0.3))
                    continue

                raise TelegramApiError(f"HTTP error on {method}: status={exc.code} body={raw_error}") from exc
            except error.URLError as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep((self.base_backoff_seconds * (2**attempt)) + random.uniform(0, 0.3))
                    continue
                raise TelegramApiError(f"Network error on {method}: {exc}") from exc

        raise TelegramApiError(f"Failed API call {method} after retries: {last_error}")

    def _set_exists(self, set_name: str) -> bool:
        try:
            self.read_set(set_name)
            return True
        except TelegramApiError as exc:
            if "STICKERSET_INVALID" in str(exc):
                return False
            raise

    def create_set(
        self,
        set_name: str,
        title: str,
        kind: SyncKind,
        first_item: TelegramTargetItem,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        self._ensure_managed_set_name(set_name)
        payload = {
            "user_id": self.bot_user_id,
            "name": set_name,
            "title": title,
            "sticker_type": "custom_emoji" if kind == "emoji" else "regular",
            "stickers": [self._sticker_payload(first_item, allow_missing_file_id=dry_run)],
        }
        if dry_run:
            return {"operation": "create_set", "payload": payload}
        self._request("createNewStickerSet", payload)
        return {"operation": "create_set", "set_name": set_name}

    def read_set(self, set_name: str, dry_run: bool = False) -> dict[str, Any]:
        self._ensure_managed_set_name(set_name)
        payload = {"name": set_name}
        if dry_run:
            return {"operation": "read_set", "payload": payload}
        return self._request("getStickerSet", payload)

    def add_item(self, set_name: str, item: TelegramTargetItem, dry_run: bool = False) -> dict[str, Any]:
        self._ensure_managed_set_name(set_name)
        payload = {
            "user_id": self.bot_user_id,
            "name": set_name,
            "sticker": self._sticker_payload(item, allow_missing_file_id=dry_run),
        }
        if dry_run:
            return {"operation": "add_item", "payload": payload}
        self._request("addStickerToSet", payload)
        return {"operation": "add_item", "source_id": item.source_id}

    def delete_item(self, sticker_id: str, dry_run: bool = False) -> dict[str, Any]:
        payload = {"sticker": sticker_id}
        if dry_run:
            return {"operation": "delete_item", "payload": payload}
        self._request("deleteStickerFromSet", payload)
        return {"operation": "delete_item", "sticker": sticker_id}

    def replace_item(self, old_sticker_id: str, new_item: TelegramTargetItem, dry_run: bool = False) -> dict[str, Any]:
        payload = {
            "user_id": self.bot_user_id,
            "old_sticker": old_sticker_id,
            "sticker": self._sticker_payload(new_item, allow_missing_file_id=dry_run),
        }
        if dry_run:
            return {"operation": "replace_item", "payload": payload}
        self._request("replaceStickerInSet", payload)
        return {"operation": "replace_item", "source_id": new_item.source_id}

    def update_emoji_list(self, sticker_id: str, emoji_list: list[str], dry_run: bool = False) -> dict[str, Any]:
        payload = {"sticker": sticker_id, "emoji_list": emoji_list}
        if dry_run:
            return {"operation": "update_emoji_list", "payload": payload}
        self._request("setStickerEmojiList", payload)
        return {"operation": "update_emoji_list", "sticker": sticker_id}

    def update_title(self, set_name: str, title: str, dry_run: bool = False) -> dict[str, Any]:
        self._ensure_managed_set_name(set_name)
        payload = {"name": set_name, "title": title}
        if dry_run:
            return {"operation": "update_title", "payload": payload}
        self._request("setStickerSetTitle", payload)
        return {"operation": "update_title", "set_name": set_name}

    def _sticker_payload(self, item: TelegramTargetItem, allow_missing_file_id: bool = False) -> dict[str, Any]:
        if not item.telegram_file_id and not allow_missing_file_id:
            raise TelegramApiError(f"Item {item.source_id} has no telegram_file_id for upload")
        return {
            "sticker": item.telegram_file_id or f"MISSING_FILE_ID:{item.source_id}",
            "format": "animated" if item.kind == "stickers" else "static",
            "emoji_list": [item.emoji or "😀"],
            "keywords": [item.source_id],
        }

    def read_current_state(self, kind: SyncKind) -> list[TelegramTargetItem]:
        set_name = self._managed_set_name(kind)
        if not self._set_exists(set_name):
            return []

        response = self.read_set(set_name)
        items: list[TelegramTargetItem] = []
        for sticker in response.get("stickers", []):
            source_id = (sticker.get("keywords") or [sticker.get("file_unique_id") or sticker.get("file_id")])[0]
            items.append(
                TelegramTargetItem(
                    target_id=sticker.get("file_id") or source_id,
                    source_id=source_id,
                    name=source_id,
                    kind=kind,
                    telegram_file_id=sticker.get("file_id"),
                    emoji=(sticker.get("emoji") or "😀"),
                    fingerprint=sticker.get("file_unique_id"),
                )
            )
        return items

    def apply(
        self,
        kind: SyncKind,
        to_create: list[TelegramTargetItem],
        to_update: list[TelegramTargetItem],
        to_delete: list[TelegramTargetItem],
        dry_run: bool,
    ) -> list[dict[str, Any]]:
        set_name = self._managed_set_name(kind)
        title = f"{self.set_base_name} {kind}".title()
        operations: list[dict[str, Any]] = []

        if dry_run:
            operations.append(self.read_set(set_name, dry_run=True))
            operations.append({"operation": "create_set_if_missing", "set_name": set_name})
            set_exists = True
        else:
            set_exists = self._set_exists(set_name)

        bootstrap_item = (to_create + to_update)[:1]
        if not set_exists and bootstrap_item:
            operations.append(self.create_set(set_name, title, kind, bootstrap_item[0], dry_run=dry_run))
            if to_create:
                to_create = to_create[1:]

        operations.append(self.update_title(set_name, title, dry_run=dry_run))

        for item in to_create:
            operations.append(self.add_item(set_name, item, dry_run=dry_run))
            if item.target_id:
                operations.append(self.update_emoji_list(item.target_id, [item.emoji or "😀"], dry_run=dry_run))

        for item in to_update:
            if item.target_id:
                operations.append(self.replace_item(item.target_id, item, dry_run=dry_run))
                operations.append(self.update_emoji_list(item.target_id, [item.emoji or "😀"], dry_run=dry_run))

        for item in to_delete:
            if item.target_id:
                operations.append(self.delete_item(item.target_id, dry_run=dry_run))

        return operations
