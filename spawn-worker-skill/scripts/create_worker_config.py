#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import DynamicWorkerSpec, WorkerConfigBuilder


def _default_output_path(output_dir: str, mailbox: str) -> Path:
    return Path(output_dir).resolve() / f"{mailbox}.worker.config.json"


def _run(args: argparse.Namespace) -> int:
    spec = DynamicWorkerSpec(
        worker_id=args.worker_id,
        mailbox=args.mailbox,
        system_prompt=args.system_prompt,
        model=args.model,
        metadata=_pairs_to_dict(args.metadata),
    )
    output_path = Path(args.output_path).resolve() if args.output_path else _default_output_path(args.output_dir, args.mailbox)
    builder = WorkerConfigBuilder()
    builder.write_config(
        spec=spec,
        database_path=args.database_path,
        workspace=args.workspace,
        output_path=output_path,
        executable=args.executable,
        env=_pairs_to_dict(args.env),
        extra_cli_args=args.extra_cli_arg,
        poll_interval_seconds=args.poll_interval_seconds,
        lease_seconds=args.lease_seconds,
    )
    print(
        json.dumps(
            {
                "config_path": str(output_path),
                "worker_id": spec.worker_id,
                "mailbox": spec.mailbox,
                "model": spec.model,
            },
            indent=2,
        )
    )
    return 0


def _pairs_to_dict(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Expected KEY=VALUE pair, got: {value}")
        key, raw_value = value.split("=", 1)
        result[key] = raw_value
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a worker.config.json for a dynamically spawned specialist.")
    parser.add_argument("--output-dir", required=True, help="Directory where generated configs should be stored.")
    parser.add_argument("--output-path", help="Explicit output path. Overrides --output-dir naming.")
    parser.add_argument("--database-path", required=True, help="Path to the shared mailbox SQLite database.")
    parser.add_argument("--workspace", required=True, help="Workspace the worker should operate in.")
    parser.add_argument("--mailbox", required=True, help="Mailbox identity for the new worker.")
    parser.add_argument("--worker-id", required=True, help="Unique worker id, for example smart_file_auth.1.")
    parser.add_argument("--system-prompt", required=True, help="System prompt for the worker specialization.")
    parser.add_argument("--model", default="gpt-4.1", help="Model id for the worker.")
    parser.add_argument("--executable", default="/opt/homebrew/bin/copilot", help="Path to the standalone copilot executable.")
    parser.add_argument("--poll-interval-seconds", type=float, default=1.0, help="Mailbox poll interval.")
    parser.add_argument("--lease-seconds", type=int, default=300, help="Mailbox lease duration.")
    parser.add_argument("--metadata", action="append", default=[], help="Repeatable KEY=VALUE metadata pair.")
    parser.add_argument("--env", action="append", default=[], help="Repeatable KEY=VALUE session environment pair.")
    parser.add_argument("--extra-cli-arg", action="append", default=[], help="Repeatable raw Copilot CLI argument.")
    args = parser.parse_args()
    raise SystemExit(_run(args))


if __name__ == "__main__":
    main()
