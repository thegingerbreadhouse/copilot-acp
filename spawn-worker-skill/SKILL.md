---
name: spawn-worker-skill
description: Define a new specialized worker, generate its worker config, and launch it. Use when the orchestrator has already decided to add an agent and needs the concrete create-and-launch steps.
compatibility: Requires Python 3. Uses only the standard library plus local commands such as copilot-acp, conda, and tmux when launch actions are requested.
metadata:
  author: copilot-acp
  version: 1.0.0
---

# Spawn Worker Skill

Use this skill when you are supervising a specialized agent fleet and need to create and launch a worker from an explicit agent specification.

## Goal

Turn an explicit specialization decision into a live worker.

1. Define the worker identity and mailbox.
2. Define the worker system prompt.
3. Generate a worker config.
4. Launch the worker and route future work to its mailbox.

The orchestrator is responsible for deciding whether to reuse, spawn, or defer. This skill is only for the concrete spawn path after that decision is already made.

## Workflow

### 1. Generate a worker config

Create a worker config from an explicit agent spec:

```bash
python spawn-worker-skill/scripts/create_worker_config.py \
  --output-dir /path/to/generated-workers \
  --database-path /path/to/copilot-acp.sqlite \
  --workspace /path/to/repository \
  --mailbox smart_file_auth \
  --worker-id smart_file_auth.1 \
  --system-prompt "You own src/app/auth.py. Keep edits localized, preserve external behavior, and report blockers clearly."
```

### 2. Launch the specialist

Use `launch_worker.py` to activate it:

```bash
python spawn-worker-skill/scripts/launch_worker.py \
  --config /path/to/generated-workers/smart_file_auth.worker.config.json \
  --mode tmux \
  --session-name dynamic-workers \
  --window-name smart_file_auth
```

### 3. Use the new mailbox

Once launched, route tasks to the mailbox defined in the worker config.

## Scripts

- `create_worker_config.py`: Generate a `worker.config.json` file for the new specialization.
- `launch_worker.py`: Print or execute the worker start command, including optional tmux hosting.
- `spawn_specialist.py`: Combined workflow for config creation and optional launch from an explicit worker spec.

Generated configs are intentionally minimal. The required external fields are:

- `id`
- `mailbox`
- `database`
- `system_prompt`

Everything else is optional and can be defaulted by the runtime.

## Naming guidance

- Use mailbox names that reflect the specialization, not the process model.
- Favor stable names such as `smart_file_auth`, `api_guard_payments`, or `note_taker_release`.
- Keep `worker_id` unique even when the mailbox is reused by replicas.

## Good supervisor behavior

- Let the orchestrator decide when spawning is warranted.
- Give each spawned worker one clear ownership boundary.
- Keep system prompts specific to the specialization.
- Prefer `gpt-4.1` unless a different model is materially justified.
- Avoid creating many low-value specialists with overlapping scopes.

## Notes

- This skill handles concrete worker creation and launch, not spawn policy.
- Treat the mailbox identity as the public address of the new worker.
- Use the existing supervisor skill to send work once the specialist is active.
