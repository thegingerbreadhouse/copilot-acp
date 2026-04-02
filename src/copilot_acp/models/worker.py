from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class WorkerProfile:
    worker_id: str
    mailbox: str
    role: str
    system_prompt: str
    model: str | None = None
    skills: list[str] = field(default_factory=list)
    hooks: list[str] = field(default_factory=list)
    operating_rules: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
