from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from copilot_acp.models import SessionOptions, WorkerProfile


@dataclass(slots=True)
class MailboxBackendConfig:
    database_path: str


@dataclass(slots=True)
class WorkerRuntimeConfig:
    poll_interval_seconds: float = 1.0
    lease_seconds: int = 300


@dataclass(slots=True)
class WorkerConfig:
    mailbox: MailboxBackendConfig
    profile: WorkerProfile
    session: SessionOptions
    runtime: WorkerRuntimeConfig


class WorkerConfigLoader:
    def load(self, config_path: str | Path) -> WorkerConfig:
        path = Path(config_path).resolve()
        payload = json.loads(path.read_text(encoding="utf-8"))
        return self._from_dict(payload, config_path=path)

    def _from_dict(self, payload: dict[str, Any], *, config_path: Path) -> WorkerConfig:
        session_payload = payload.get("session", {})
        runtime_payload = payload.get("runtime", {})
        database_path = self._resolve_database_path(payload)
        worker_id = self._read_required_field(payload, "id", fallback_group="worker", fallback_key="worker_id")
        mailbox_name = self._read_required_field(payload, "mailbox", fallback_group="worker", fallback_key="mailbox")
        system_prompt = self._read_required_field(payload, "system_prompt", fallback_group="worker", fallback_key="system_prompt")
        metadata = self._resolve_metadata(payload)
        model = self._resolve_model(payload, session_payload)

        session_cwd = session_payload.get("cwd")
        if session_cwd is not None:
            session_cwd = str((config_path.parent / session_cwd).resolve())

        profile = WorkerProfile(
            worker_id=worker_id,
            mailbox=mailbox_name,
            system_prompt=system_prompt,
            model=model,
            metadata=metadata,
        )

        return WorkerConfig(
            mailbox=MailboxBackendConfig(database_path=str((config_path.parent / database_path).resolve())),
            profile=profile,
            session=SessionOptions(
                cwd=session_cwd,
                executable=session_payload.get("executable"),
                model=model,
                env=session_payload.get("env", {}),
                extra_cli_args=session_payload.get("extra_cli_args", []),
            ),
            runtime=WorkerRuntimeConfig(
                poll_interval_seconds=runtime_payload.get("poll_interval_seconds", 1.0),
                lease_seconds=runtime_payload.get("lease_seconds", 300),
            ),
        )

    @staticmethod
    def _read_required_field(
        payload: dict[str, Any],
        field_name: str,
        *,
        fallback_group: str,
        fallback_key: str,
    ) -> str:
        value = payload.get(field_name)
        if isinstance(value, str):
            return value
        fallback_payload = payload.get(fallback_group, {})
        fallback_value = fallback_payload.get(fallback_key)
        if isinstance(fallback_value, str):
            return fallback_value
        raise KeyError(field_name)

    @staticmethod
    def _resolve_database_path(payload: dict[str, Any]) -> str:
        if "database" in payload:
            return payload["database"]
        mailbox_payload = payload.get("mailbox", {})
        if isinstance(mailbox_payload, dict) and "database_path" in mailbox_payload:
            return mailbox_payload["database_path"]
        raise KeyError("database")

    @staticmethod
    def _resolve_metadata(payload: dict[str, Any]) -> dict[str, Any]:
        metadata = payload.get("metadata")
        if metadata is not None:
            return metadata
        worker_payload = payload.get("worker", {})
        return worker_payload.get("metadata", {})

    @staticmethod
    def _resolve_model(payload: dict[str, Any], session_payload: dict[str, Any]) -> str | None:
        if "model" in payload:
            return payload["model"]
        if session_payload.get("model") is not None:
            return session_payload["model"]
        worker_payload = payload.get("worker", {})
        return worker_payload.get("model")
