from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from pathlib import Path

from copilot_acp.models import RuntimeOptions
from copilot_acp.services import CopilotPromptService, PersistentCopilotHost, SessionOptions


@dataclass(slots=True)
class CLIOptions:
    command: str
    prompt: str | None
    cwd: str | None
    executable: str | None
    model: str | None
    host: str
    port: int
    enable_repl: bool


class CopilotACPCLI:
    def __init__(self) -> None:
        self._parser = self._build_parser()

    def run(self, argv: list[str] | None = None) -> int:
        options = self._parse_args(argv)
        return asyncio.run(self._dispatch(options))

    def _build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="copilot-acp",
            description="CLI wrapper for talking to GitHub Copilot over ACP.",
        )
        parser.add_argument(
            "--cwd",
            default=str(Path.cwd()),
            help="Working directory for the ACP session.",
        )
        parser.add_argument(
            "--copilot",
            dest="executable",
            default=None,
            help="Path to the standalone `copilot` executable.",
        )
        parser.add_argument(
            "--model",
            default=None,
            help="Copilot model id to use. Defaults to gpt-4.1.",
        )

        subparsers = parser.add_subparsers(dest="command")

        ask_parser = subparsers.add_parser("ask", help="Send one prompt and print the response.")
        ask_parser.add_argument("prompt", help="Prompt text to send.")

        subparsers.add_parser("chat", help="Start an interactive ACP chat session.")
        serve_parser = subparsers.add_parser(
            "serve",
            help="Keep one ACP session active for terminal and programmatic prompts.",
        )
        serve_parser.add_argument(
            "--host",
            default="127.0.0.1",
            help="Host interface for the local JSON prompt server.",
        )
        serve_parser.add_argument(
            "--port",
            type=int,
            default=8765,
            help="TCP port for the local JSON prompt server.",
        )
        serve_parser.add_argument(
            "--no-repl",
            action="store_true",
            help="Disable the attached terminal prompt and only serve TCP requests.",
        )
        return parser

    def _parse_args(self, argv: list[str] | None) -> CLIOptions:
        args = self._parser.parse_args(argv)
        command = args.command or ("ask" if getattr(args, "prompt", None) else "chat")
        return CLIOptions(
            command=command,
            prompt=getattr(args, "prompt", None),
            cwd=args.cwd,
            executable=args.executable,
            model=args.model,
            host=getattr(args, "host", "127.0.0.1"),
            port=getattr(args, "port", 8765),
            enable_repl=not getattr(args, "no_repl", False),
        )

    async def _dispatch(self, options: CLIOptions) -> int:
        service = CopilotPromptService(
            SessionOptions(
                cwd=options.cwd,
                executable=options.executable,
                model=options.model,
            )
        )
        if options.command == "ask":
            return await self._run_ask(service, options)
        if options.command == "serve":
            return await self._run_serve(service, options)
        return await self._run_chat(service)

    async def _run_ask(self, service: CopilotPromptService, options: CLIOptions) -> int:
        if not options.prompt:
            raise ValueError("The `ask` command requires a prompt.")
        transcript = await service.ask_once(options.prompt)
        print(transcript.text, end="" if transcript.text.endswith("\n") else "\n")
        return 0 if transcript.stop_reason in {None, "end_turn"} else 1

    async def _run_chat(self, service: CopilotPromptService) -> int:
        print("Interactive ACP chat. Type /exit to quit.")
        async with service.open_chat_session() as session:
            while True:
                try:
                    prompt = input("> ").strip()
                except EOFError:
                    print()
                    return 0

                if not prompt:
                    continue
                if prompt in {"/exit", "/quit"}:
                    return 0

                transcript = await session.ask(prompt)
                print(transcript.text, end="" if transcript.text.endswith("\n") else "\n")
        return 0

    async def _run_serve(self, service: CopilotPromptService, options: CLIOptions) -> int:
        host = PersistentCopilotHost(
            prompt_service=service,
            runtime_options=RuntimeOptions(
                host=options.host,
                port=options.port,
                enable_repl=options.enable_repl,
            ),
        )
        return await host.run()
