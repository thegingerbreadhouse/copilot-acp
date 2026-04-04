# copilot-acp

Thin Python wrapper for talking to GitHub Copilot CLI through the Agent Client Protocol (ACP).

Default model: `gpt-4.1`.

The project now has two layers:

- a thin ACP transport wrapper for Copilot CLI
- a higher-level mailbox runtime for supervisor/worker orchestration

## Why this shape

GitHub documents Copilot CLI's ACP mode as a stdio/TCP server started with `copilot --acp`, and explicitly recommends `stdio` for IDE-style integrations. The official ACP Python SDK already handles ACP framing, process lifecycle, and session callbacks, so this project keeps the wrapper narrow instead of rebuilding transport code.

## Chosen Python library

This project uses [`agent-client-protocol`](https://pypi.org/project/agent-client-protocol/), the published ACP Python SDK.

Reasons:

- It is purpose-built for ACP clients and agents.
- Its quickstart includes the exact subprocess pattern needed here: `spawn_agent_process(...)` over stdio.
- It tracks ACP schema releases and ships typed helpers for streamed updates and permission flows.
- It supports Python 3.10 through 3.14, which matches the current published package metadata.

## Copilot CLI prerequisite

You need the standalone GitHub Copilot CLI installed and authenticated.

GitHub's current install docs list:

- `brew install copilot-cli` on macOS/Linux
- `npm install -g @github/copilot` on any platform

On this machine, `which copilot` currently resolves to VS Code's shim under:

`/Users/kateanderson/Library/Application Support/Code/User/globalStorage/github.copilot-chat/copilotCli/copilot`

That shim prompts to install the real CLI if `copilot-cli` is not separately installed, so the wrapper may fail until the standalone CLI is installed.

The wrapper now prefers common standalone install locations such as `/opt/homebrew/bin/copilot` before falling back to `PATH`, but you should still run:

```bash
/opt/homebrew/bin/copilot login
```

before attempting live ACP sessions.

## Current runtime status on this machine

The project has been validated on this machine through:

- ACP process startup against `/opt/homebrew/bin/copilot`
- `initialize`
- `newSession`
- one-shot prompt/response through the Python wrapper
- persistent host mode over TCP
- mailbox supervisor/worker routing through SQLite
- config-driven isolated workers started from their own terminal

Verified live prompts currently work with authenticated Copilot CLI access on this machine.

## Install

### Conda

```bash
conda env create -f environment.yml
conda activate copilot-acp
```

### Pip only

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -e .
```

Use `requirements-lock.txt` if you want the pinned transitive set used during development.

## Quick use

```python
import asyncio

from copilot_acp import CopilotACPClient


async def main() -> None:
    async with CopilotACPClient() as client:
        session = await client.create_session()
        response = await client.ask_text(session.id, "Summarize this repository.")
        print(response.text)


asyncio.run(main())
```

## CLI wrapper

The package now includes a thin CLI on top of the ACP client:

```bash
python -m copilot_acp ask "Briefly, state your capabilities."
python -m copilot_acp --model gpt-5.2 ask "Summarize this repository."
python -m copilot_acp chat
python -m copilot_acp serve
```

After reinstalling the editable package, the console script is also available:

```bash
copilot-acp ask "Briefly, state your capabilities."
copilot-acp chat
copilot-acp serve
```

## Persistent host mode

Use `serve` to keep one ACP session alive and accept prompts from both:

- the attached terminal prompt
- a lightweight local JSON-over-TCP interface

Start it:

```bash
copilot-acp serve
copilot-acp serve --port 9000
copilot-acp serve --no-repl
```

When running, it listens on `127.0.0.1:8765` by default and accepts one JSON object per line:

```json
{"prompt":"Briefly, state your capabilities.","request_id":"demo-1"}
```

It returns one JSON response per line:

```json
{"ok":true,"text":"...","stop_reason":"end_turn","session_id":"...","request_id":"demo-1","error":null}
```

You can also send `"/exit"` or `"/quit"` as the prompt to stop the host.

## Mailbox runtime

For multi-agent orchestration, the project now includes a mailbox-oriented runtime:

- `SQLiteMailbox` provides a durable local queue with lease-based claiming
- `Supervisor` submits tasks and waits for results
- `AgentWorker` holds a persistent ACP session and processes mailbox messages
- `WorkerProfile` defines mailbox identity and the worker's system prompt

This is the intended direction for swarm-style coordination because ACP handles the Copilot session, while the mailbox layer handles durable routing, retries, and supervisor/worker boundaries.

## Config-driven workers

The intended terminal model is:

- one terminal
- one worker process
- one `worker.config.json`
- one persistent ACP session
- one subscribed mailbox

That keeps agents isolated and cheap to run while allowing each worker to specialize independently.

Start a worker from config:

```bash
copilot-acp worker --config examples/worker.config.example.json
```

The config file controls:

- agent identity and mailbox subscription
- database path
- system prompt specialization
- optional model override, defaulting to `gpt-4.1`
- optional session cwd and executable
- optional raw Copilot CLI args for tool or MCP customization
- optional environment variables
- optional mailbox polling and lease overrides

The minimum working worker config is:

```json
{
  "id": "worker.dev.1",
  "mailbox": "worker.dev",
  "database": "../copilot-acp.sqlite",
  "system_prompt": "Implement requested work carefully and report blockers clearly."
}
```

If omitted:

- `model` defaults to `gpt-4.1`
- `session` defaults to the current working directory, the preferred standalone `copilot` executable, and no extra env or CLI args
- `runtime` defaults to `poll_interval_seconds: 1.0` and `lease_seconds: 300`

The example config is in [worker.config.example.json](/Users/kateanderson/Documents/Programming/copilot-acp/examples/worker.config.example.json).

## Supervisor workflow

For a supervisor running in another terminal on the same machine, use the mailbox as the integration boundary.

The dedicated supervisor skill is in [SKILL.md](/Users/kateanderson/Documents/Programming/copilot-acp/supervisor-skill/SKILL.md).

The `supervisor-skill/` folder is portable on the same machine. You can copy it elsewhere and still use its scripts as long as they can access the shared SQLite mailbox database path.

Typical flow:

1. Start a worker in terminal A:

```bash
copilot-acp worker --config examples/worker.config.example.json
```

2. Submit work from terminal B:

```bash
python supervisor-skill/scripts/submit_task.py \
  --db /absolute/path/to/copilot-acp.sqlite \
  --supervisor supervisor.main \
  --recipient worker.dev \
  --subject "Repository question" \
  --body "Briefly summarize the repository structure."
```

3. Wait for the result from terminal B:

```bash
python supervisor-skill/scripts/wait_for_result.py \
  --db /absolute/path/to/copilot-acp.sqlite \
  --supervisor supervisor.main \
  --thread-id <thread_id>
```

4. Inspect mailbox state if needed:

```bash
python supervisor-skill/scripts/inspect_mailbox.py \
  --db /absolute/path/to/copilot-acp.sqlite \
  --thread-id <thread_id>
```

## Tmux control plane

If you want tmux to host the worker terminals while the mailbox remains the message bus:

```bash
copilot-acp tmux up --config examples/tmux.session.example.json
tmux attach -t copilot-acp-swarm
```

To inspect or stop the session:

```bash
copilot-acp tmux ls
copilot-acp tmux down --session-name copilot-acp-swarm
```

The tmux session config is in [tmux.session.example.json](/Users/kateanderson/Documents/Programming/copilot-acp/examples/tmux.session.example.json).

Worker configs used by tmux sessions follow the same minimal schema described above.

Minimal programmatic shape:

```python
import asyncio
from pathlib import Path

from copilot_acp import AgentWorker, SQLiteMailbox, Supervisor, WorkerProfile


async def main() -> None:
    mailbox = SQLiteMailbox(Path("/tmp/copilot-acp.sqlite"))
    supervisor = Supervisor(mailbox, supervisor_id="supervisor.main")
    worker = AgentWorker(
        WorkerProfile(
            worker_id="worker.dev.1",
            mailbox="worker.dev",
            system_prompt="Answer briefly and accurately.",
            model="gpt-4.1",
        ),
        mailbox,
    )

    task = await supervisor.submit_task(
        recipient="worker.dev",
        subject="Smoke test",
        body="Reply with exactly mailbox-ok.",
    )

    await worker.run_until_idle(max_messages=1)
    result = await supervisor.wait_for_result(thread_id=task.thread_id)
    print(result.body)


asyncio.run(main())
```

## Example script

```bash
copilot-acp-once "Explain the current directory."
copilot-acp-once --model gpt-5.2 "Explain the current directory."
```

Optionally set `COPILOT_CLI_PATH` if `copilot` is not on `PATH`.

## Model selection

`CopilotACPClient(...)` defaults to `gpt-4.1`.

Pass `model=` to choose a different Copilot model for the ACP server process:

```python
async with CopilotACPClient(model="gpt-5.2") as client:
    ...
```

Or use `--model` in the example CLI:

```bash
copilot-acp-once --model gpt-5.2 "Briefly, state your capabilities."
```

The wrapper forwards this directly to the standalone Copilot CLI through `--model <model-id>`.
