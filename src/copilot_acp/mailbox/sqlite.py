from __future__ import annotations

import asyncio
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from copilot_acp.mailbox.base import Mailbox
from copilot_acp.models import MailboxMessage, MessageKind, MessageStatus, OutboundMessage


class SQLiteMailbox(Mailbox):
    def __init__(self, database_path: str | Path) -> None:
        self._database_path = str(Path(database_path))
        self._initialize()

    async def publish(self, message: OutboundMessage) -> MailboxMessage:
        return await asyncio.to_thread(self._publish_sync, message)

    async def claim_next(
        self,
        *,
        recipient: str,
        worker_id: str,
        lease_seconds: int,
    ) -> MailboxMessage | None:
        return await asyncio.to_thread(
            self._claim_next_sync,
            recipient,
            worker_id,
            lease_seconds,
        )

    async def mark_completed(self, message_id: str) -> None:
        await asyncio.to_thread(self._mark_completed_sync, message_id)

    async def mark_failed(
        self,
        message_id: str,
        *,
        error: str,
        requeue: bool = False,
    ) -> None:
        await asyncio.to_thread(self._mark_failed_sync, message_id, error, requeue)

    async def list_messages(
        self,
        *,
        recipient: str | None = None,
        thread_id: str | None = None,
        kind: MessageKind | None = None,
        status: MessageStatus | None = None,
        limit: int = 100,
    ) -> list[MailboxMessage]:
        return await asyncio.to_thread(
            self._list_messages_sync,
            recipient,
            thread_id,
            kind,
            status,
            limit,
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    recipient TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    subject TEXT,
                    body TEXT NOT NULL,
                    thread_id TEXT,
                    parent_message_id TEXT,
                    metadata_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    lease_owner TEXT,
                    lease_expires_at TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    error TEXT
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_recipient_status "
                "ON messages(recipient, status, created_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_thread_id "
                "ON messages(thread_id, created_at)"
            )
            connection.commit()

    def _publish_sync(self, message: OutboundMessage) -> MailboxMessage:
        timestamp = self._format_time(message.created_at)
        thread_id = message.thread_id or message.message_id
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO messages (
                    message_id, recipient, sender, kind, subject, body,
                    thread_id, parent_message_id, metadata_json, status,
                    created_at, updated_at, lease_owner, lease_expires_at,
                    attempts, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.message_id,
                    message.recipient,
                    message.sender,
                    message.kind.value,
                    message.subject,
                    message.body,
                    thread_id,
                    message.parent_message_id,
                    json.dumps(message.metadata),
                    MessageStatus.PENDING.value,
                    timestamp,
                    timestamp,
                    None,
                    None,
                    0,
                    None,
                ),
            )
            connection.commit()
            row = connection.execute(
                "SELECT * FROM messages WHERE message_id = ?",
                (message.message_id,),
            ).fetchone()
        return self._row_to_message(row)

    def _claim_next_sync(
        self,
        recipient: str,
        worker_id: str,
        lease_seconds: int,
    ) -> MailboxMessage | None:
        now = datetime.now(timezone.utc)
        lease_expires_at = now + timedelta(seconds=lease_seconds)
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT * FROM messages
                WHERE recipient = ?
                  AND (
                    status = ?
                    OR (status = ? AND (lease_expires_at IS NULL OR lease_expires_at < ?))
                  )
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (
                    recipient,
                    MessageStatus.PENDING.value,
                    MessageStatus.LEASED.value,
                    self._format_time(now),
                ),
            ).fetchone()

            if row is None:
                connection.commit()
                return None

            connection.execute(
                """
                UPDATE messages
                SET status = ?, lease_owner = ?, lease_expires_at = ?, updated_at = ?, attempts = attempts + 1
                WHERE message_id = ?
                """,
                (
                    MessageStatus.LEASED.value,
                    worker_id,
                    self._format_time(lease_expires_at),
                    self._format_time(now),
                    row["message_id"],
                ),
            )
            updated = connection.execute(
                "SELECT * FROM messages WHERE message_id = ?",
                (row["message_id"],),
            ).fetchone()
            connection.commit()
        return self._row_to_message(updated)

    def _mark_completed_sync(self, message_id: str) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                UPDATE messages
                SET status = ?, lease_owner = NULL, lease_expires_at = NULL, updated_at = ?
                WHERE message_id = ?
                """,
                (
                    MessageStatus.COMPLETED.value,
                    self._format_time(datetime.now(timezone.utc)),
                    message_id,
                ),
            )
            connection.commit()

    def _mark_failed_sync(self, message_id: str, error: str, requeue: bool) -> None:
        status = MessageStatus.PENDING if requeue else MessageStatus.FAILED
        lease_owner = None
        lease_expires_at = None
        with closing(self._connect()) as connection:
            connection.execute(
                """
                UPDATE messages
                SET status = ?, error = ?, lease_owner = ?, lease_expires_at = ?, updated_at = ?
                WHERE message_id = ?
                """,
                (
                    status.value,
                    error,
                    lease_owner,
                    lease_expires_at,
                    self._format_time(datetime.now(timezone.utc)),
                    message_id,
                ),
            )
            connection.commit()

    def _list_messages_sync(
        self,
        recipient: str | None,
        thread_id: str | None,
        kind: MessageKind | None,
        status: MessageStatus | None,
        limit: int,
    ) -> list[MailboxMessage]:
        clauses: list[str] = []
        values: list[str | int] = []

        if recipient is not None:
            clauses.append("recipient = ?")
            values.append(recipient)
        if thread_id is not None:
            clauses.append("thread_id = ?")
            values.append(thread_id)
        if kind is not None:
            clauses.append("kind = ?")
            values.append(kind.value)
        if status is not None:
            clauses.append("status = ?")
            values.append(status.value)

        where_clause = ""
        if clauses:
            where_clause = "WHERE " + " AND ".join(clauses)

        query = (
            "SELECT * FROM messages "
            f"{where_clause} "
            "ORDER BY created_at ASC "
            "LIMIT ?"
        )
        values.append(limit)

        with closing(self._connect()) as connection:
            rows = connection.execute(query, values).fetchall()
        return [self._row_to_message(row) for row in rows]

    def _row_to_message(self, row: sqlite3.Row) -> MailboxMessage:
        return MailboxMessage(
            message_id=row["message_id"],
            recipient=row["recipient"],
            sender=row["sender"],
            kind=MessageKind(row["kind"]),
            body=row["body"],
            status=MessageStatus(row["status"]),
            created_at=self._parse_time(row["created_at"]),
            updated_at=self._parse_time(row["updated_at"]),
            subject=row["subject"],
            thread_id=row["thread_id"],
            parent_message_id=row["parent_message_id"],
            metadata=json.loads(row["metadata_json"]),
            lease_owner=row["lease_owner"],
            lease_expires_at=self._parse_time(row["lease_expires_at"]) if row["lease_expires_at"] else None,
            attempts=row["attempts"],
            error=row["error"],
        )

    @staticmethod
    def _format_time(value: datetime) -> str:
        return value.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _parse_time(value: str) -> datetime:
        return datetime.fromisoformat(value)
