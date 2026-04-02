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
    supervisor = SupervisorClient(mailbox, supervisor_id=args.supervisor)
    message = supervisor.submit_task(
        recipient=args.recipient,
        subject=args.subject,
        body=args.body,
    )
    print(
        json.dumps(
            {
                "message_id": message.message_id,
                "thread_id": message.thread_id,
                "recipient": message.recipient,
                "sender": message.sender,
                "status": message.status.value,
            },
            indent=2,
        )
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit a supervisor task into a worker mailbox.")
    parser.add_argument("--db", required=True, help="Path to the shared mailbox SQLite database.")
    parser.add_argument("--supervisor", required=True, help="Supervisor mailbox identity.")
    parser.add_argument("--recipient", required=True, help="Worker mailbox name.")
    parser.add_argument("--subject", required=True, help="Short task subject.")
    parser.add_argument("--body", required=True, help="Task body.")
    args = parser.parse_args()
    raise SystemExit(_run(args))


if __name__ == "__main__":
    main()
