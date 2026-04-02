from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class TmuxWorkerLaunch:
    name: str
    worker_config: str
    conda_env: str = "copilot-acp"


@dataclass(slots=True)
class TmuxSessionConfig:
    session_name: str
    workers: list[TmuxWorkerLaunch] = field(default_factory=list)


class TmuxSessionConfigLoader:
    def load(self, config_path: str | Path) -> TmuxSessionConfig:
        path = Path(config_path).resolve()
        payload = json.loads(path.read_text(encoding="utf-8"))
        workers_payload: list[dict[str, Any]] = payload.get("workers", [])
        workers = [
            TmuxWorkerLaunch(
                name=worker["name"],
                worker_config=str((path.parent / worker["worker_config"]).resolve()),
                conda_env=worker.get("conda_env", "copilot-acp"),
            )
            for worker in workers_payload
        ]
        return TmuxSessionConfig(
            session_name=payload["session_name"],
            workers=workers,
        )
