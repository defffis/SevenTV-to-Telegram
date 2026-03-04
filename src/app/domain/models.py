from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


SyncKind = Literal["emoji", "stickers"]


class SourceEmote(BaseModel):
    source_id: str = Field(..., description="Уникальный ID эмоута в SevenTV")
    name: str = Field(..., description="Человекочитаемое имя")
    kind: SyncKind
    source_url: str
    file_ext: str
    animated: bool = False
    width: Optional[int] = None
    height: Optional[int] = None
    checksum: Optional[str] = None
    updated_at: Optional[datetime] = None


class TelegramTargetItem(BaseModel):
    target_id: str = Field(..., description="ID объекта внутри Telegram-набора")
    source_id: str = Field(..., description="Связанный ID в SevenTV")
    name: str
    kind: SyncKind
    telegram_file_id: Optional[str] = None
    emoji: Optional[str] = None
    fingerprint: Optional[str] = Field(
        default=None,
        description="Хеш/признак версии отрендеренного контента",
    )


class TargetSetPlan(BaseModel):
    kind: SyncKind
    shard_index: int = Field(..., ge=0)
    set_name: str
    items: list[TelegramTargetItem]


class SyncPlan(BaseModel):
    kind: SyncKind
    source_count: int = 0
    current_count: int = 0
    dry_run: bool = False
    force_full_resync: bool = False
    to_create: list[TelegramTargetItem] = Field(default_factory=list)
    to_update: list[TelegramTargetItem] = Field(default_factory=list)
    to_delete: list[TelegramTargetItem] = Field(default_factory=list)
    shards: list[TargetSetPlan] = Field(default_factory=list)
