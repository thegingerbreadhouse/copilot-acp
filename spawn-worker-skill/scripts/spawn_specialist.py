#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import DynamicWorkerSpec, WorkerConfigBuilder, WorkerLaunchMode, WorkerLauncher


def _run(args: argparse.Namespace) -> int:
    spec = DynamicWorkerSpec(
        worker_id=args.worker_id,
        mailbox=args.mailbox,
        system_prompt=args.system_prompt,
        model=args.model,
    )
    output_dir = Path(args.output_dir).resolve()
    config_path = output_dir / f"{spec.mailbox}.worker.config.json"
    builder = WorkerConfigBuilder()
    builder.write_config(
        spec=spec,
        database_path=args.database_path,
        workspace=args.workspace,
        output_path=config_path,
        executable=args.executable,
        extra_cli_args=args.extra_cli_arg,
    )
    response: dict[str, object] = {
        "spec": spec.to_dict(),
        "config_path": str(config_path),
    }

    if args.mode != WorkerLaunchMode.PRINT.value:
        launcher = WorkerLauncher(copilot_acp_command=args.copilot_acp_command)
        response["launch"] = launcher.launch(
            config_path=config_path,
            conda_env=args.conda_env,
            mode=WorkerLaunchMode(args.mode),
            session_name=args.session_name,
            window_name=spec.mailbox,
        )
    else:
        response["launch"] = {"mode": WorkerLaunchMode.PRINT.value}

    print(json.dumps(response, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Create and optionally launch a worker from an explicit specialist spec.")
    parser.add_argument("--database-path", required=True, help="Path to the shared mailbox SQLite database.")
    parser.add_argument("--workspace", required=True, help="Workspace the specialist should operate in.")
    parser.add_argument("--output-dir", required=True, help="Directory for generated worker config files.")
    parser.add_argument("--worker-id", required=True, help="Unique worker id, for example agent.prompt_service.1.")
    parser.add_argument("--mailbox", required=True, help="Mailbox identity for the worker.")
    parser.add_argument("--system-prompt", required=True, help="System prompt that defines the worker specialization.")
    parser.add_argument("--model", default="gpt-4.1", help="Model to assign if a worker is spawned.")
    parser.add_argument("--executable", default="/opt/homebrew/bin/copilot", help="Path to the standalone copilot executable.")
    parser.add_argument("--extra-cli-arg", action="append", default=[], help="Repeatable raw Copilot CLI argument.")
    parser.add_argument("--conda-env", default="copilot-acp", help="Conda environment used to run copilot-acp.")
    parser.add_argument("--copilot-acp-command", default="copilot-acp", help="copilot-acp executable or shell command name.")
    parser.add_argument(
        "--mode",
        choices=[mode.value for mode in WorkerLaunchMode],
        default=WorkerLaunchMode.PRINT.value,
        help="Launch handling for newly spawned specialists.",
    )
    parser.add_argument("--session-name", default="dynamic-workers", help="tmux session name for tmux mode.")
    args = parser.parse_args()
    raise SystemExit(_run(args))


if __name__ == "__main__":
    main()
