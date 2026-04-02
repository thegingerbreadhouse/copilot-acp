from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from copilot_acp.client import CopilotACPClient, PromptTranscript, SessionHandle
from copilot_acp.models import SessionOptions


class CopilotChatSession:
    def __init__(self, client: CopilotACPClient, handle: SessionHandle) -> None:
        self._client = client
        self._handle = handle

    @property
    def session_id(self) -> str:
        return self._handle.id

    async def ask(self, prompt_text: str) -> PromptTranscript:
        return await self._client.ask_text(self._handle.id, prompt_text)


class CopilotPromptService:
    def __init__(self, options: SessionOptions | None = None) -> None:
        self._options = options or SessionOptions()

    async def ask_once(self, prompt_text: str) -> PromptTranscript:
        async with self.open_chat_session() as session:
            return await session.ask(prompt_text)

    @asynccontextmanager
    async def open_chat_session(self) -> AsyncIterator[CopilotChatSession]:
        async with CopilotACPClient(
            executable=self._options.executable,
            model=self._options.model,
            default_cwd=self._options.cwd,
            env=self._options.env,
            extra_cli_args=self._options.extra_cli_args,
        ) as client:
            handle = await client.create_session(cwd=self._options.cwd)
            yield CopilotChatSession(client=client, handle=handle)
