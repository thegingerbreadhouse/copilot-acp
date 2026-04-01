# copilot-acp

Thin Python wrapper for talking to GitHub Copilot CLI through the Agent Client Protocol (ACP).

Default model: `gpt-4.1`.

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

The wrapper has been validated through:

- ACP process startup against `/opt/homebrew/bin/copilot`
- `initialize`
- `newSession`

Prompt execution currently returns:

```text
Error: You are not authorized to use this Copilot feature, it requires an enterprise or organization policy to be enabled.
```

So the Python transport is working, but successful prompts depend on Copilot-side account or org policy for ACP-enabled agent features.

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
