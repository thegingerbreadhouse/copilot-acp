from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MessageKind(StrEnum):
    TASK_REQUEST = "task_request"
    TASK_RESULT = "task_result"
    TASK_UPDATE = "task_update"
    CONTROL = "control"


class MessageStatus(StrEnum):
    PENDING = "pending"
    LEASED = "leased"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


@dataclass(slots=True)
class OutboundMessage:
    recipient: str
    sender: str
    kind: MessageKind
    body: str
    subject: str | None = None
    thread_id: str | None = None
    parent_message_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    message_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class MailboxMessage:
    message_id: str
    recipient: str
    sender: str
    kind: MessageKind
    body: str
    status: MessageStatus
    created_at: datetime
    updated_at: datetime
    subject: str | None = None
    thread_id: str | None = None
    parent_message_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None
    attempts: int = 0
    error: str | None = None
