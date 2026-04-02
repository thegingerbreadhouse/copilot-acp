#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import SpawnPolicy, SpecializationRequest


def _run(args: argparse.Namespace) -> int:
    request = SpecializationRequest(
        specialization=args.specialization,
        task_summary=args.task_summary,
        target=args.target,
        expected_follow_ups=args.expected_follow_ups,
        complexity=args.complexity,
        requires_persistent_context=args.requires_persistent_context,
        existing_workers=args.existing_worker,
        preferred_model=args.preferred_model,
    )
    decision = SpawnPolicy().decide(request)
    print(json.dumps(decision.to_dict(), indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan whether a new specialized worker should be spawned.")
    parser.add_argument("--specialization", required=True, help="Specialization family such as smart_file or note_taker.")
    parser.add_argument("--task-summary", required=True, help="Short summary of the work driving this spawn request.")
    parser.add_argument("--target", help="Optional artifact or domain owned by the new specialist.")
    parser.add_argument("--expected-follow-ups", type=int, default=1, help="Expected number of related follow-up tasks.")
    parser.add_argument("--complexity", default="medium", help="Complexity hint such as low, medium, or high.")
    parser.add_argument(
        "--requires-persistent-context",
        action="store_true",
        help="Set when retaining artifact-local context is expected to help.",
    )
    parser.add_argument(
        "--existing-worker",
        action="append",
        default=[],
        help="Existing specialist mailbox names available for reuse checks.",
    )
    parser.add_argument("--preferred-model", default="gpt-4.1", help="Model to suggest if a new worker is spawned.")
    args = parser.parse_args()
    raise SystemExit(_run(args))


if __name__ == "__main__":
    main()
