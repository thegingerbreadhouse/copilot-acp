from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

from acp import spawn_agent_process, text_block
from acp.interfaces import Client


PermissionHandler = Callable[[Any, str | None, Any], Awaitable[dict[str, Any]]]
_COPILOT_SHIM_MARKER = os.path.join("github.copilot-chat", "copilotCli")
_DEFAULT_MODEL = "gpt-4.1"


def _read_attr(value: Any, *names: str) -> Any:
    for name in names:
        if isinstance(value, dict) and name in value:
            return value[name]
        if hasattr(value, name):
            return getattr(value, name)
    return None


def _is_text_chunk(update: Any) -> bool:
    kind = _read_attr(update, "session_update", "sessionUpdate")
    content = _read_attr(update, "content")
    return kind == "agent_message_chunk" and _read_attr(content, "type") == "text"


def _chunk_text(update: Any) -> str:
    content = _read_attr(update, "content")
    return _read_attr(content, "text") or ""


@dataclass(slots=True)
class SessionUpdateEvent:
    session_id: str
    update: Any


@dataclass(slots=True)
class SessionHandle:
    id: str
    events: asyncio.Queue[SessionUpdateEvent]


@dataclass(slots=True)
class PromptTranscript:
    session_id: str
    text: str
    stop_reason: str | None
    updates: list[Any] = field(default_factory=list)


class _EventClient(Client):
    def __init__(self, permission_handler: PermissionHandler | None = None) -> None:
        self.permission_handler = permission_handler or self._default_permission_handler
        self._session_queues: dict[str, asyncio.Queue[SessionUpdateEvent]] = {}
        self._all_events: asyncio.Queue[SessionUpdateEvent] = asyncio.Queue()

    def queue_for(self, session_id: str) -> asyncio.Queue[SessionUpdateEvent]:
        return self._session_queues.setdefault(session_id, asyncio.Queue())

    @property
    def all_events(self) -> asyncio.Queue[SessionUpdateEvent]:
        return self._all_events

    async def request_permission(
        self,
        options: Any,
        session_id: str | None = None,
        tool_call: Any = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return await self.permission_handler(options, session_id, tool_call)

    async def session_update(self, session_id: str, update: Any, **kwargs: Any) -> None:
        event = SessionUpdateEvent(session_id=session_id, update=update)
        await self._all_events.put(event)
        await self.queue_for(session_id).put(event)

    @staticmethod
    async def _default_permission_handler(
        options: Any,
        session_id: str | None,
        tool_call: Any,
    ) -> dict[str, Any]:
        return {"outcome": {"outcome": "cancelled"}}


class CopilotACPClient:
    def __init__(
        self,
        executable: str | None = None,
        *,
        model: str | None = None,
        protocol_version: int = 1,
        default_cwd: str | os.PathLike[str] | None = None,
        permission_handler: PermissionHandler | None = None,
    ) -> None:
        self.executable = self._resolve_executable(executable)
        self.model = model or _DEFAULT_MODEL
        self.protocol_version = protocol_version
        self.default_cwd = str(Path(default_cwd).resolve()) if default_cwd else os.getcwd()
        self._event_client = _EventClient(permission_handler=permission_handler)
        self._spawn_cm: Any = None
        self._connection: Any = None
        self._process: Any = None

    async def __aenter__(self) -> CopilotACPClient:
        command = [self.executable]
        if self.model:
            command.extend(["--model", self.model])
        command.extend(["--acp", "--stdio"])
        self._spawn_cm = spawn_agent_process(
            self._event_client,
            *command,
        )
        try:
            self._connection, self._process = await self._spawn_cm.__aenter__()
            await self._connection.initialize(
                protocol_version=self.protocol_version,
                client_capabilities={},
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"Copilot executable not found: {self.executable!r}. "
                "Install the standalone GitHub Copilot CLI or set COPILOT_CLI_PATH."
            ) from exc
        except Exception as exc:
            raise RuntimeError(
                "Failed to start Copilot ACP. If `copilot` resolves to VS Code's shim, "
                "install the standalone GitHub Copilot CLI first."
            ) from exc
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._spawn_cm is not None:
            await self._spawn_cm.__aexit__(exc_type, exc, tb)
        self._spawn_cm = None
        self._connection = None
        self._process = None

    @property
    def all_events(self) -> asyncio.Queue[SessionUpdateEvent]:
        return self._event_client.all_events

    async def create_session(
        self,
        *,
        cwd: str | os.PathLike[str] | None = None,
        mcp_servers: list[Any] | None = None,
    ) -> SessionHandle:
        self._require_connection()
        session = await self._connection.new_session(
            cwd=str(Path(cwd).resolve()) if cwd else self.default_cwd,
            mcp_servers=mcp_servers or [],
        )
        session_id = _read_attr(session, "session_id", "sessionId")
        if not session_id:
            raise RuntimeError(f"ACP returned a session without an id: {session!r}")
        return SessionHandle(id=session_id, events=self._event_client.queue_for(session_id))

    async def prompt(
        self,
        session_id: str,
        prompt: list[Any],
    ) -> Any:
        self._require_connection()
        return await self._connection.prompt(session_id=session_id, prompt=prompt)

    async def ask_text(self, session_id: str, prompt_text: str) -> PromptTranscript:
        queue = self._event_client.queue_for(session_id)
        collected_updates: list[Any] = []
        chunks: list[str] = []
        finished = asyncio.Event()

        async def consume_updates() -> None:
            while not finished.is_set():
                event = await queue.get()
                collected_updates.append(event.update)
                if _is_text_chunk(event.update):
                    chunks.append(_chunk_text(event.update))

        consumer = asyncio.create_task(consume_updates())
        try:
            result = await self.prompt(session_id, [text_block(prompt_text)])
            stop_reason = _read_attr(result, "stop_reason", "stopReason")
        finally:
            finished.set()
            consumer.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await consumer
        return PromptTranscript(
            session_id=session_id,
            text="".join(chunks),
            stop_reason=stop_reason,
            updates=collected_updates,
        )

    def _require_connection(self) -> None:
        if self._connection is None:
            raise RuntimeError("CopilotACPClient is not connected. Use `async with` first.")

    @staticmethod
    def _resolve_executable(executable: str | None) -> str:
        if executable:
            return executable

        env_path = os.environ.get("COPILOT_CLI_PATH")
        if env_path:
            return env_path

        preferred_paths = [
            "/opt/homebrew/bin/copilot",
            "/usr/local/bin/copilot",
        ]
        for candidate in preferred_paths:
            if os.path.exists(candidate):
                return candidate

        discovered = shutil.which("copilot")
        if discovered and _COPILOT_SHIM_MARKER not in discovered:
            return discovered

        return discovered or "copilot"
