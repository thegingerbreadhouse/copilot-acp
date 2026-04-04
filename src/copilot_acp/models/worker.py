from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class WorkerProfile:
    worker_id: str
    mailbox: str
    system_prompt: str
    model: str | None = None
