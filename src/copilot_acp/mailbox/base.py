from __future__ import annotations

from abc import ABC, abstractmethod

from copilot_acp.models import MailboxMessage, MessageKind, MessageStatus, OutboundMessage


class Mailbox(ABC):
    @abstractmethod
    async def publish(self, message: OutboundMessage) -> MailboxMessage:
        raise NotImplementedError

    @abstractmethod
    async def claim_next(
        self,
        *,
        recipient: str,
        worker_id: str,
        lease_seconds: int,
    ) -> MailboxMessage | None:
        raise NotImplementedError

    @abstractmethod
    async def mark_completed(self, message_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def mark_failed(
        self,
        message_id: str,
        *,
        error: str,
        requeue: bool = False,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def list_messages(
        self,
        *,
        recipient: str | None = None,
        thread_id: str | None = None,
        kind: MessageKind | None = None,
        status: MessageStatus | None = None,
        limit: int = 100,
    ) -> list[MailboxMessage]:
        raise NotImplementedError
