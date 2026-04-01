from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from copilot_acp import CopilotACPClient


async def _run(prompt: str, cwd: str | None, executable: str | None) -> int:
    async with CopilotACPClient(executable=executable, default_cwd=cwd) as client:
        session = await client.create_session()
        transcript = await client.ask_text(session.id, prompt)
        print(transcript.text, end="" if transcript.text.endswith("\n") else "\n")
        return 0 if transcript.stop_reason in {None, "end_turn"} else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Send one ACP prompt to GitHub Copilot CLI.")
    parser.add_argument("prompt", help="Prompt text to send.")
    parser.add_argument(
        "--cwd",
        default=str(Path.cwd()),
        help="Working directory for the ACP session.",
    )
    parser.add_argument(
        "--copilot",
        default=None,
        help="Path to the standalone `copilot` executable.",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args.prompt, args.cwd, args.copilot)))


if __name__ == "__main__":
    main()
