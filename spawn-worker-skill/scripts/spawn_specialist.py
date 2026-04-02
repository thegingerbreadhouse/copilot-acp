#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import SpawnDecisionAction, SpawnPolicy, SpecializationRequest, WorkerConfigBuilder, WorkerLaunchMode, WorkerLauncher


def _run(args: argparse.Namespace) -> int:
    request = SpecializationRequest(
        specialization=args.specialization,
        task_summary=args.task_summary,
        target=args.target,
        expected_follow_ups=args.expected_follow_ups,
        complexity=args.complexity,
        requires_persistent_context=args.requires_persistent_context,
        existing_workers=args.existing_worker,
        preferred_model=args.model,
    )
    decision = SpawnPolicy().decide(request)
    response: dict[str, object] = {"decision": decision.to_dict()}

    if decision.action != SpawnDecisionAction.SPAWN_NEW or decision.spec is None:
        print(json.dumps(response, indent=2))
        return 0

    output_dir = Path(args.output_dir).resolve()
    config_path = output_dir / f"{decision.spec.mailbox}.worker.config.json"
    builder = WorkerConfigBuilder()
    builder.write_config(
        spec=decision.spec,
        database_path=args.database_path,
        workspace=args.workspace,
        output_path=config_path,
        executable=args.executable,
        extra_cli_args=args.extra_cli_arg,
    )
    response["config_path"] = str(config_path)

    if args.mode != WorkerLaunchMode.PRINT.value:
        launcher = WorkerLauncher(copilot_acp_command=args.copilot_acp_command)
        response["launch"] = launcher.launch(
            config_path=config_path,
            conda_env=args.conda_env,
            mode=WorkerLaunchMode(args.mode),
            session_name=args.session_name,
            window_name=decision.spec.mailbox,
        )
    else:
        response["launch"] = {"mode": WorkerLaunchMode.PRINT.value}

    print(json.dumps(response, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan, create, and optionally launch a dynamically spawned specialist.")
    parser.add_argument("--specialization", required=True, help="Specialization family such as smart_file or note_taker.")
    parser.add_argument("--task-summary", required=True, help="Short summary of the work driving this spawn request.")
    parser.add_argument("--database-path", required=True, help="Path to the shared mailbox SQLite database.")
    parser.add_argument("--workspace", required=True, help="Workspace the specialist should operate in.")
    parser.add_argument("--output-dir", required=True, help="Directory for generated worker config files.")
    parser.add_argument("--target", help="Optional artifact or domain owned by the specialist.")
    parser.add_argument("--expected-follow-ups", type=int, default=1, help="Expected number of related follow-up tasks.")
    parser.add_argument("--complexity", default="medium", help="Complexity hint such as low, medium, or high.")
    parser.add_argument("--model", default="gpt-4.1", help="Model to assign if a worker is spawned.")
    parser.add_argument(
        "--requires-persistent-context",
        action="store_true",
        help="Set when retaining local context is expected to help.",
    )
    parser.add_argument("--existing-worker", action="append", default=[], help="Existing specialist mailbox names for reuse checks.")
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
