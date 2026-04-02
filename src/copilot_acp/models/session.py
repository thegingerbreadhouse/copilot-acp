from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SessionOptions:
    cwd: str | None = None
    executable: str | None = None
    model: str | None = None
    env: dict[str, str] | None = None
    extra_cli_args: list[str] | None = None
