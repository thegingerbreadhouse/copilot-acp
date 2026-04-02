---
name: supervisor-skill
description: Submit tasks to mailbox-backed copilot-acp workers, wait for results, and inspect mailbox state. Use when supervising workers from another terminal or another folder on the same machine through a shared SQLite mailbox.
compatibility: Requires Python 3 and read/write access to the shared SQLite mailbox database on the same machine.
metadata:
  author: copilot-acp
  transport: sqlite-mailbox
---

# Supervisor Skill

Use this skill when you are acting as a supervisor process on the same machine as `copilot-acp` workers and need to send them mailbox tasks, wait for results, or inspect mailbox state.

This skill is designed to be portable. You can copy the entire `supervisor-skill/` folder to another location on the same machine and still use it, because the scripts only depend on:

- Python standard library
- the path to the shared SQLite mailbox database

## Goal

Treat mailbox storage as the integration boundary. Do not talk to worker ACP sessions directly. Instead:

1. Identify the shared mailbox SQLite database.
2. Identify the worker mailbox name.
3. Submit a task into that mailbox.
4. Wait for the result on the supervisor mailbox.
5. Inspect message state if something stalls or fails.

## Assumptions

- Workers are started independently in other terminals with `copilot-acp worker --config ...`.
- The worker config points at a shared SQLite mailbox database.
- The supervisor is on the same machine and can read and write that database path.
- The supervisor skill folder can live anywhere on the same machine.

## Recommended workflow

### 1. Submit a task

Use:

```bash
python supervisor-skill/scripts/submit_task.py \
  --db /path/to/copilot-acp.sqlite \
  --supervisor supervisor.main \
  --recipient worker.dev \
  --subject "Repository question" \
  --body "Briefly summarize the repository structure."
```

This prints a JSON payload containing the `thread_id`. Keep it.

### 2. Wait for the response

Use:

```bash
python supervisor-skill/scripts/wait_for_result.py \
  --db /path/to/copilot-acp.sqlite \
  --supervisor supervisor.main \
  --thread-id <thread_id>
```

### 3. Inspect mailbox state if needed

Use:

```bash
python supervisor-skill/scripts/inspect_mailbox.py \
  --db /path/to/copilot-acp.sqlite \
  --recipient worker.dev
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
- Supervisors should have their own stable mailbox identity, for example `supervisor.main`.

## Good supervisor behavior

- Keep subjects short and descriptive.
- Put the actual task in the body.
- Use one thread per unit of work unless you intentionally want conversational continuity.
- Wait on `thread_id`, not just mailbox name.
- Inspect failures before resubmitting.

## Example mailboxes

- `worker.dev`
- `worker.review`
- `worker.test`
- `worker.research`

## Failure triage

If a task does not complete:

1. Confirm the worker terminal is running.
2. Confirm worker and supervisor are using the same SQLite database path.
3. Inspect the mailbox by `thread_id`.
4. Check whether the task is still `pending`, `leased`, `failed`, or `completed`.
5. If `leased`, the worker may still be processing or may have died before lease release.

## Notes

- This skill is intentionally mailbox-centric.
- The worker’s ACP runtime is an implementation detail behind the mailbox boundary.
- The scripts are self-contained and do not import the main `copilot_acp` package.
