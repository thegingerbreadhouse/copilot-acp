---
name: spawn-worker-skill
description: Assess when the current agent fleet is insufficient, define a new specialized worker, generate its worker config, and launch it. Use when supervising a mailbox-backed swarm and you need to add a specialist dynamically instead of routing to an existing agent.
compatibility: Requires Python 3. Uses only the standard library plus local commands such as copilot-acp, conda, and tmux when launch actions are requested.
metadata:
  author: copilot-acp
  version: 1.0.0
---

# Spawn Worker Skill

Use this skill when you are supervising a specialized agent fleet and need to decide whether to add a new worker for a niche, recurring, or artifact-scoped task.

## Goal

Expand the swarm deliberately, not reflexively.

1. Check whether an existing specialist already fits the work.
2. Spawn only when the expected benefit is higher than the coordination cost.
3. Generate a worker config with a clear specialization boundary.
4. Launch the new worker and route future work to its mailbox.

## Use this skill when

- No current specialist cleanly fits the task.
- The work clusters around one artifact, domain, or responsibility.
- Persistent local context is likely to help.
- You expect multiple follow-up tasks for the same niche.
- You want a reusable mailbox identity such as `smart_file_auth`, `note_taker_release`, or `migration_42`.

## Do not use this skill when

- The task is small enough for the supervisor to do directly.
- An existing specialist already covers the work.
- The boundary is too fuzzy to give the new worker a clear specialization prompt.
- The task is a one-off with little chance of reuse.

## Workflow

### 1. Plan the specialization

Use `plan_specialist.py` first. It evaluates whether to reuse, spawn, or defer:

```bash
python spawn-worker-skill/scripts/plan_specialist.py \
  --specialization smart_file \
  --target src/app/auth.py \
  --task-summary "Perform repeated edits in the authentication flow." \
  --expected-follow-ups 3 \
  --complexity high \
  --requires-persistent-context \
  --existing-worker reviewer \
  --existing-worker note_taker
```

### 2. Generate a worker config

If the decision is `spawn_new`, create a worker config:

```bash
python spawn-worker-skill/scripts/create_worker_config.py \
  --output-dir /path/to/generated-workers \
  --database-path /path/to/copilot-acp.sqlite \
  --workspace /path/to/repository \
  --mailbox smart_file_auth \
  --worker-id smart_file_auth.1 \
  --system-prompt "You own src/app/auth.py. Keep edits localized, preserve external behavior, and report blockers clearly."
```

### 3. Launch the specialist

Use `launch_worker.py` to activate it:

```bash
python spawn-worker-skill/scripts/launch_worker.py \
  --config /path/to/generated-workers/smart_file_auth.worker.config.json \
  --mode tmux \
  --session-name dynamic-workers \
  --window-name smart_file_auth
```

### 4. Use the new mailbox

Once launched, route tasks to the mailbox defined in the worker config.

## Scripts

- `plan_specialist.py`: Decide whether to reuse an existing worker, spawn a new one, or defer.
- `create_worker_config.py`: Generate a `worker.config.json` file for the new specialization.
- `launch_worker.py`: Print or execute the worker start command, including optional tmux hosting.
- `spawn_specialist.py`: Combined workflow for planning, config creation, and optional launch.

## Naming guidance

- Use mailbox names that reflect the specialization, not the process model.
- Favor stable names such as `smart_file_auth`, `api_guard_payments`, or `note_taker_release`.
- Keep `worker_id` unique even when the mailbox is reused by replicas.

## Good supervisor behavior

- Reuse before spawning.
- Give each spawned worker one clear ownership boundary.
- Keep system prompts specific to the specialization.
- Prefer `gpt-4.1` unless a different model is materially justified.
- Avoid creating many low-value specialists with overlapping scopes.

## Notes

- This skill manages specialist lifecycle, not ordinary task routing.
- Treat the mailbox identity as the public address of the new worker.
- Use the existing supervisor skill to send work once the specialist is active.
