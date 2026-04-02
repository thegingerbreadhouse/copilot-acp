#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import MailboxClient, SupervisorClient


def _run(args: argparse.Namespace) -> int:
    mailbox = MailboxClient(args.db)
    supervisor = SupervisorClient(
        mailbox,
        supervisor_id=args.supervisor,
        poll_interval_seconds=args.poll_interval,
    )
    result = supervisor.wait_for_result(
        thread_id=args.thread_id,
        timeout_seconds=args.timeout,
    )
    print(
        json.dumps(
            {
                "message_id": result.message_id,
                "thread_id": result.thread_id,
                "sender": result.sender,
                "recipient": result.recipient,
                "kind": result.kind.value,
                "status": result.status.value,
                "body": result.body,
            },
            indent=2,
        )
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Wait for a worker result on a supervisor mailbox thread.")
    parser.add_argument("--db", required=True, help="Path to the shared mailbox SQLite database.")
    parser.add_argument("--supervisor", required=True, help="Supervisor mailbox identity.")
    parser.add_argument("--thread-id", required=True, help="Thread identifier returned during submit.")
    parser.add_argument("--timeout", type=float, default=300.0, help="Timeout in seconds.")
    parser.add_argument("--poll-interval", type=float, default=1.0, help="Polling interval in seconds.")
    args = parser.parse_args()
    raise SystemExit(_run(args))


if __name__ == "__main__":
    main()
