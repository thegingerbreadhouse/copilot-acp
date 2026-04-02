from __future__ import annotations

import subprocess

from copilot_acp.config import TmuxSessionConfig, TmuxWorkerLaunch


class TmuxLauncher:
    def __init__(self, *, executable: str = "tmux") -> None:
        self._executable = executable

    def start_session(self, config: TmuxSessionConfig) -> None:
        self._ensure_tmux_available()
        if not config.workers:
            raise ValueError("Tmux session config must include at least one worker.")

        first, *remaining = config.workers
        self._run_tmux(
            "new-session",
            "-d",
            "-s",
            config.session_name,
            "-n",
            first.name,
            *self._build_worker_command(first),
        )
        for worker in remaining:
            self._run_tmux(
                "new-window",
                "-t",
                config.session_name,
                "-n",
                worker.name,
                *self._build_worker_command(worker),
            )

    def stop_session(self, session_name: str) -> None:
        self._run_tmux("kill-session", "-t", session_name)

    def list_sessions(self) -> list[str]:
        self._ensure_tmux_available()
        completed = subprocess.run(
            [self._executable, "list-sessions", "-F", "#{session_name}"],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            return []
        return [line.strip() for line in completed.stdout.splitlines() if line.strip()]

    def attach_hint(self, session_name: str) -> str:
        return f"tmux attach -t {session_name}"

    def _build_worker_command(self, worker: TmuxWorkerLaunch) -> list[str]:
        return [
            "conda",
            "run",
            "-n",
            worker.conda_env,
            "python",
            "-m",
            "copilot_acp",
            "worker",
            "--config",
            worker.worker_config,
        ]

    def _ensure_tmux_available(self) -> None:
        completed = subprocess.run(
            [self._executable, "-V"],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "tmux is not installed or not available on PATH. "
                "Install tmux to use the local control-plane launcher."
            )

    def _run_tmux(self, *args: str) -> None:
        completed = subprocess.run(
            [self._executable, *args],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            stderr = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(stderr or f"tmux command failed: {' '.join(args)}")
