from __future__ import annotations

import asyncio
from contextlib import suppress

from copilot_acp.mailbox import Mailbox
from copilot_acp.models import MessageKind, OutboundMessage, WorkerProfile
from copilot_acp.services import CopilotPromptService, SessionOptions


class AgentWorker:
    def __init__(
        self,
        profile: WorkerProfile,
        mailbox: Mailbox,
        *,
        session_options: SessionOptions | None = None,
        poll_interval_seconds: float = 1.0,
        lease_seconds: int = 300,
    ) -> None:
        self._profile = profile
        self._mailbox = mailbox
        self._poll_interval_seconds = poll_interval_seconds
        self._lease_seconds = lease_seconds
        effective_session_options = session_options or SessionOptions(model=profile.model)
        if effective_session_options.model is None:
            effective_session_options.model = profile.model
        self._prompt_service = CopilotPromptService(effective_session_options)
        self._shutdown_event = asyncio.Event()

    @property
    def worker_id(self) -> str:
        return self._profile.worker_id

    async def run(self) -> None:
        async with self._prompt_service.open_chat_session() as session:
            while not self._shutdown_event.is_set():
                handled = await self._process_next_message(session)
                if not handled:
                    await asyncio.sleep(self._poll_interval_seconds)

    async def run_until_idle(self, *, max_messages: int = 1) -> int:
        processed = 0
        async with self._prompt_service.open_chat_session() as session:
            while processed < max_messages:
                handled = await self._process_next_message(session)
                if not handled:
                    break
                processed += 1
        return processed

    async def stop(self) -> None:
        self._shutdown_event.set()

    async def _process_next_message(self, session: object) -> bool:
        message = await self._mailbox.claim_next(
            recipient=self._profile.mailbox,
            worker_id=self._profile.worker_id,
            lease_seconds=self._lease_seconds,
        )
        if message is None:
            return False

        try:
            prompt_text = self._build_prompt(message)
            transcript = await session.ask(prompt_text)
            await self._mailbox.publish(
                OutboundMessage(
                    recipient=message.sender,
                    sender=self._profile.worker_id,
                    kind=MessageKind.TASK_RESULT,
                    subject=message.subject,
                    body=transcript.text,
                    thread_id=message.thread_id,
                    parent_message_id=message.message_id,
                    metadata={
                        "worker_id": self._profile.worker_id,
                        "stop_reason": transcript.stop_reason,
                    },
                )
            )
            await self._mailbox.mark_completed(message.message_id)
        except Exception as exc:
            await self._mailbox.mark_failed(message.message_id, error=str(exc), requeue=False)
            with suppress(Exception):
                await self._mailbox.publish(
                    OutboundMessage(
                        recipient=message.sender,
                        sender=self._profile.worker_id,
                        kind=MessageKind.TASK_UPDATE,
                        subject=message.subject,
                        body=f"Worker failed: {exc}",
                        thread_id=message.thread_id,
                        parent_message_id=message.message_id,
                        metadata={
                            "worker_id": self._profile.worker_id,
                            "status": "failed",
                        },
                    )
                )
        return True

    def _build_prompt(self, message: object) -> str:
        subject = message.subject or "Task"
        return (
            f"Operating instructions:\n{self._profile.system_prompt}\n\n"
            f"Task subject: {subject}\n"
            f"From supervisor: {message.sender}\n"
            f"Thread id: {message.thread_id}\n\n"
            f"Task body:\n{message.body}\n\n"
            "Respond with the best useful completion for the supervisor."
        )
