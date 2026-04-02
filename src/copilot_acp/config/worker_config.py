from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from copilot_acp.models import WorkerProfile
from copilot_acp.services import SessionOptions


@dataclass(slots=True)
class MailboxBackendConfig:
    database_path: str


@dataclass(slots=True)
class WorkerRuntimeConfig:
    poll_interval_seconds: float = 1.0
    lease_seconds: int = 300


@dataclass(slots=True)
class WorkerCustomizationConfig:
    skills: list[str] = field(default_factory=list)
    hooks: list[str] = field(default_factory=list)
    operating_rules: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WorkerConfig:
    mailbox: MailboxBackendConfig
    profile: WorkerProfile
    session: SessionOptions
    runtime: WorkerRuntimeConfig
    customization: WorkerCustomizationConfig


class WorkerConfigLoader:
    def load(self, config_path: str | Path) -> WorkerConfig:
        path = Path(config_path).resolve()
        payload = json.loads(path.read_text(encoding="utf-8"))
        return self._from_dict(payload, config_path=path)

    def _from_dict(self, payload: dict[str, Any], *, config_path: Path) -> WorkerConfig:
        mailbox_payload = payload["mailbox"]
        worker_payload = payload["worker"]
        session_payload = payload.get("session", {})
        runtime_payload = payload.get("runtime", {})
        customization_payload = payload.get("customization", {})
        customization = WorkerCustomizationConfig(
            skills=customization_payload.get("skills", []),
            hooks=customization_payload.get("hooks", []),
            operating_rules=customization_payload.get("operating_rules", []),
        )

        session_cwd = session_payload.get("cwd")
        if session_cwd is not None:
            session_cwd = str((config_path.parent / session_cwd).resolve())

        profile = WorkerProfile(
            worker_id=worker_payload["worker_id"],
            mailbox=worker_payload["mailbox"],
            role=worker_payload["role"],
            system_prompt=worker_payload["system_prompt"],
            model=worker_payload.get("model"),
            skills=customization.skills,
            hooks=customization.hooks,
            operating_rules=customization.operating_rules,
            metadata=worker_payload.get("metadata", {}),
        )

        return WorkerConfig(
            mailbox=MailboxBackendConfig(database_path=str((config_path.parent / mailbox_payload["database_path"]).resolve())),
            profile=profile,
            session=SessionOptions(
                cwd=session_cwd,
                executable=session_payload.get("executable"),
                model=session_payload.get("model") or worker_payload.get("model"),
                env=session_payload.get("env", {}),
                extra_cli_args=session_payload.get("extra_cli_args", []),
            ),
            runtime=WorkerRuntimeConfig(
                poll_interval_seconds=runtime_payload.get("poll_interval_seconds", 1.0),
                lease_seconds=runtime_payload.get("lease_seconds", 300),
            ),
            customization=customization,
        )
