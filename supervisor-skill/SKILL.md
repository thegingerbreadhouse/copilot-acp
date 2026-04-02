---
name: supervisor-skill
description: Route work to mailbox-backed specialized agents, wait for results, and inspect mailbox state. Use when supervising a local agent fleet through a shared SQLite mailbox.
compatibility: Requires Python 3 and read/write access to the shared SQLite mailbox database on the same machine.
metadata:
  author: copilot-acp
  transport: sqlite-mailbox
---

# Supervisor Skill

Use this skill when you are supervising a fleet of specialized agents and need to route work, wait for results, or inspect mailbox state.

## Goal

Treat mailbox storage as the integration boundary. Do not talk to agent ACP sessions directly. Instead:

1. Identify the shared mailbox SQLite database.
2. Identify the target agent mailbox name.
3. Submit a task into that mailbox.
4. Wait for the result on the supervisor mailbox.
5. Inspect message state if something stalls or fails.

## Assumptions

- Each specialized agent has a mailbox identity.
- Each agent points at a shared SQLite mailbox database.
- The supervisor can read and write that database path.

## Recommended workflow

### 1. Activate the target agent

Make sure the target specialized agent is active and listening on its mailbox identity.

### 2. Submit a task

Use the `submit_task.py` script to write a `task_request` message into the target agent mailbox:

```bash
python supervisor-skill/scripts/submit_task.py \
  --db /path/to/copilot-acp.sqlite \
  --supervisor supervisor.main \
  --recipient note_taker \
  --subject "Repository question" \
  --body "Briefly summarize the repository structure."
```

This prints a JSON payload containing the `thread_id`.

### 3. Wait for the response

Use:

```bash
python supervisor-skill/scripts/wait_for_result.py \
  --db /path/to/copilot-acp.sqlite \
  --supervisor supervisor.main \
  --thread-id <thread_id>
```

### 4. Inspect mailbox state if needed

Use:

```bash
python supervisor-skill/scripts/inspect_mailbox.py \
  --db /path/to/copilot-acp.sqlite \
  --recipient note_taker
```

or:

```bash
python supervisor-skill/scripts/inspect_mailbox.py \
  --db /path/to/copilot-acp.sqlite \
  --thread-id <thread_id>
```

## Routing guidance

- Use distinct mailbox names for distinct specializations.
- Use the same mailbox name for horizontal replicas of the same specialization.
- Use a stable supervisor mailbox identity, for example `supervisor.main`.
- Model agent identity around its specialization, for example `note_taker`, `smart_file_1`, `smart_file_2`, `reviewer`, or `researcher`.

## Good supervisor behavior

- Keep subjects short and descriptive.
- Put the actual task in the body.
- Use one thread per unit of work unless you intentionally want conversational continuity.
- Wait on `thread_id`, not just mailbox name.
- Inspect failures before resubmitting.
- Route tasks to the most specific specialized agent available.
- Split work across agents when the task naturally decomposes into independent parts.

## Example mailboxes

- `note_taker`
- `smart_file_1`
- `smart_file_2`
- `reviewer`
- `researcher`
- `tester`

## Failure triage

If a task does not complete:

1. Confirm the target agent is active.
2. Confirm worker and supervisor are using the same SQLite database path.
3. Inspect the mailbox by `thread_id`.
4. Check whether the task is still `pending`, `leased`, `failed`, or `completed`.
5. If `leased`, the worker may still be processing or may have died before lease release.

## Notes

- This skill is intentionally mailbox-centric.
- The agent’s ACP runtime is an implementation detail behind the mailbox boundary.
- The scripts are self-contained and do not import the main `copilot_acp` package.
