from __future__ import annotations

import asyncio
import json
import sys
from contextlib import suppress
from typing import Any

from copilot_acp.models import PromptRequest, PromptResponse, RuntimeOptions
from copilot_acp.services.prompt_service import CopilotChatSession, CopilotPromptService


class PersistentCopilotHost:
    def __init__(
        self,
        prompt_service: CopilotPromptService,
        runtime_options: RuntimeOptions | None = None,
    ) -> None:
        self._prompt_service = prompt_service
        self._runtime_options = runtime_options or RuntimeOptions()
        self._session_context: Any = None
        self._session: CopilotChatSession | None = None
        self._server: asyncio.AbstractServer | None = None
        self._prompt_lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()

    @property
    def session_id(self) -> str | None:
        if self._session is None:
            return None
        return self._session.session_id

    async def start(self) -> None:
        self._session_context = self._prompt_service.open_chat_session()
        self._session = await self._session_context.__aenter__()
        self._server = await asyncio.start_server(
            self._handle_connection,
            host=self._runtime_options.host,
            port=self._runtime_options.port,
        )

    async def run(self) -> int:
        await self.start()
        try:
            print(
                f"ACP host ready on {self._runtime_options.host}:{self._runtime_options.port} "
                f"(session: {self.session_id})"
            )
            tasks = [asyncio.create_task(self._server.serve_forever())]
            if self._runtime_options.enable_repl and sys.stdin.isatty():
                print("Interactive prompt attached. Type /exit to stop the host.")
                tasks.append(asyncio.create_task(self._run_repl()))
            else:
                print("Interactive prompt disabled.")

            tasks.append(asyncio.create_task(self._shutdown_event.wait()))
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

            for task in pending:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

            for task in done:
                if task.cancelled():
                    continue
                exc = task.exception()
                if exc is not None:
                    raise exc
            return 0
        finally:
            await self.stop()

    async def stop(self) -> None:
        self._shutdown_event.set()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        if self._session_context is not None:
            await self._session_context.__aexit__(None, None, None)
            self._session_context = None
            self._session = None

    async def submit_prompt(self, request: PromptRequest) -> PromptResponse:
        if self._session is None:
            return PromptResponse(
                ok=False,
                text="",
                request_id=request.request_id,
                error="ACP host is not running.",
            )

        async with self._prompt_lock:
            try:
                transcript = await self._session.ask(request.prompt)
            except Exception as exc:
                return PromptResponse(
                    ok=False,
                    text="",
                    request_id=request.request_id,
                    session_id=self.session_id,
                    error=str(exc),
                )

        return PromptResponse(
            ok=True,
            text=transcript.text,
            stop_reason=transcript.stop_reason,
            session_id=self.session_id,
            request_id=request.request_id,
        )

    async def _run_repl(self) -> None:
        while not self._shutdown_event.is_set():
            prompt = await asyncio.to_thread(input, "> ")
            prompt = prompt.strip()
            if not prompt:
                continue
            if prompt in {"/exit", "/quit"}:
                self._shutdown_event.set()
                return

            response = await self.submit_prompt(PromptRequest(prompt=prompt))
            print(response.text, end="" if response.text.endswith("\n") else "\n")

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            while not reader.at_eof():
                raw_line = await reader.readline()
                if not raw_line:
                    break
                response = await self._handle_request_line(raw_line)
                writer.write((json.dumps(response.to_dict()) + "\n").encode("utf-8"))
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async def _handle_request_line(self, raw_line: bytes) -> PromptResponse:
        try:
            payload = json.loads(raw_line.decode("utf-8"))
        except json.JSONDecodeError as exc:
            return PromptResponse(ok=False, text="", error=f"Invalid JSON: {exc}")

        prompt = payload.get("prompt")
        request_id = payload.get("request_id")
        if not isinstance(prompt, str) or not prompt.strip():
            return PromptResponse(
                ok=False,
                text="",
                request_id=request_id,
                error="Request must include a non-empty `prompt` string.",
            )

        if prompt.strip() in {"/exit", "/quit"}:
            self._shutdown_event.set()
            return PromptResponse(
                ok=True,
                text="Host shutdown requested.",
                request_id=request_id,
                session_id=self.session_id,
            )

        return await self.submit_prompt(
            PromptRequest(prompt=prompt, request_id=request_id),
        )
