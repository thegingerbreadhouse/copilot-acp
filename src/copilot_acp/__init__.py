from __future__ import annotations

from importlib import import_module
from typing import Any

from .config import WorkerConfig, WorkerConfigLoader
from .mailbox import SQLiteMailbox
from .models import (
    MailboxMessage,
    MessageKind,
    MessageStatus,
    OutboundMessage,
    PromptRequest,
    PromptResponse,
    RuntimeOptions,
    SessionOptions,
    WorkerProfile,
)
from .supervisor import Supervisor

__all__ = [
    "CopilotACPClient",
    "CopilotChatSession",
    "CopilotPromptService",
    "MailboxMessage",
    "MessageKind",
    "MessageStatus",
    "OutboundMessage",
    "PromptRequest",
    "PromptResponse",
    "PromptTranscript",
    "RuntimeOptions",
    "SQLiteMailbox",
    "SessionHandle",
    "SessionOptions",
    "SessionUpdateEvent",
    "Supervisor",
    "WorkerConfig",
    "WorkerConfigLoader",
    "WorkerProfile",
    "AgentWorker",
]


def __getattr__(name: str) -> Any:
    if name in {"CopilotACPClient", "PromptTranscript", "SessionHandle", "SessionUpdateEvent"}:
        module = import_module("copilot_acp.client")
        return getattr(module, name)
    if name in {"CopilotChatSession", "CopilotPromptService", "SessionOptions"}:
        module = import_module("copilot_acp.services")
        return getattr(module, name)
    if name == "AgentWorker":
        module = import_module("copilot_acp.workers")
        return getattr(module, name)
    raise AttributeError(f"module 'copilot_acp' has no attribute {name!r}")
