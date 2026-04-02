#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import WorkerLaunchMode, WorkerLauncher


def _run(args: argparse.Namespace) -> int:
    launcher = WorkerLauncher(copilot_acp_command=args.copilot_acp_command)
    result = launcher.launch(
        config_path=args.config,
        conda_env=args.conda_env,
        mode=WorkerLaunchMode(args.mode),
        session_name=args.session_name,
        window_name=args.window_name,
    )
    print(json.dumps(result, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch a mailbox-backed worker from a generated worker config.")
    parser.add_argument("--config", required=True, help="Path to the worker config file.")
    parser.add_argument(
        "--mode",
        choices=[mode.value for mode in WorkerLaunchMode],
        default=WorkerLaunchMode.PRINT.value,
        help="How to handle the worker launch.",
    )
    parser.add_argument("--conda-env", default="copilot-acp", help="Conda environment used to run copilot-acp.")
    parser.add_argument("--copilot-acp-command", default="copilot-acp", help="copilot-acp executable or shell command name.")
    parser.add_argument("--session-name", default="dynamic-workers", help="tmux session name for tmux mode.")
    parser.add_argument("--window-name", help="tmux window name for tmux mode.")
    args = parser.parse_args()
    raise SystemExit(_run(args))


if __name__ == "__main__":
    main()
