from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class RuntimeOptions:
    host: str = "127.0.0.1"
    port: int = 8765
    enable_repl: bool = True


@dataclass(slots=True)
class PromptRequest:
    prompt: str
    request_id: str | None = None


@dataclass(slots=True)
class PromptResponse:
    ok: bool
    text: str
    stop_reason: str | None = None
    session_id: str | None = None
    request_id: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, str | bool | None]:
        return asdict(self)
