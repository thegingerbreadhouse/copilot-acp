from __future__ import annotations

import asyncio
from uuid import uuid4

from copilot_acp.mailbox import Mailbox
from copilot_acp.models import MailboxMessage, MessageKind, MessageStatus, OutboundMessage


class Supervisor:
    def __init__(
        self,
        mailbox: Mailbox,
        *,
        supervisor_id: str = "supervisor",
        poll_interval_seconds: float = 1.0,
    ) -> None:
        self._mailbox = mailbox
        self._supervisor_id = supervisor_id
        self._poll_interval_seconds = poll_interval_seconds

    @property
    def supervisor_id(self) -> str:
        return self._supervisor_id

    async def submit_task(
        self,
        *,
        recipient: str,
        subject: str,
        body: str,
        metadata: dict[str, str] | None = None,
        thread_id: str | None = None,
    ) -> MailboxMessage:
        thread = thread_id or str(uuid4())
        return await self._mailbox.publish(
            OutboundMessage(
                recipient=recipient,
                sender=self._supervisor_id,
                kind=MessageKind.TASK_REQUEST,
                subject=subject,
                body=body,
                thread_id=thread,
                metadata=metadata or {},
            )
        )

    async def wait_for_result(
        self,
        *,
        thread_id: str,
        timeout_seconds: float = 300.0,
    ) -> MailboxMessage:
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while True:
            messages = await self._mailbox.list_messages(
                recipient=self._supervisor_id,
                thread_id=thread_id,
                limit=50,
            )
            for message in messages:
                if message.kind == MessageKind.TASK_RESULT and message.status == MessageStatus.PENDING:
                    await self._mailbox.mark_completed(message.message_id)
                    return message
                if message.kind == MessageKind.TASK_UPDATE and message.status == MessageStatus.PENDING:
                    await self._mailbox.mark_completed(message.message_id)

            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError(f"Timed out waiting for thread {thread_id}")
            await asyncio.sleep(self._poll_interval_seconds)
