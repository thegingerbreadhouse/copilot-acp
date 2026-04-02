#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import MailboxClient, MessageKind, MessageStatus


def _run(args: argparse.Namespace) -> int:
    mailbox = MailboxClient(args.db)
    messages = mailbox.list_messages(
        recipient=args.recipient,
        thread_id=args.thread_id,
        kind=MessageKind(args.kind) if args.kind else None,
        status=MessageStatus(args.status) if args.status else None,
        limit=args.limit,
    )
    payload = [
        {
            "message_id": message.message_id,
            "thread_id": message.thread_id,
            "sender": message.sender,
            "recipient": message.recipient,
            "kind": message.kind.value,
            "status": message.status.value,
            "subject": message.subject,
            "attempts": message.attempts,
            "lease_owner": message.lease_owner,
            "body": message.body,
            "error": message.error,
        }
        for message in messages
    ]
    print(json.dumps(payload, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect mailbox messages by recipient, thread, kind, or status.")
    parser.add_argument("--db", required=True, help="Path to the shared mailbox SQLite database.")
    parser.add_argument("--recipient", default=None, help="Mailbox recipient to inspect.")
    parser.add_argument("--thread-id", default=None, help="Thread identifier to inspect.")
    parser.add_argument("--kind", default=None, help="Optional message kind filter.")
    parser.add_argument("--status", default=None, help="Optional message status filter.")
    parser.add_argument("--limit", type=int, default=100, help="Maximum number of messages to return.")
    args = parser.parse_args()
    raise SystemExit(_run(args))


if __name__ == "__main__":
    main()
