#!/usr/bin/env python3
"""CLI wrapper for DeepStateTracker operations.

Provides bash-friendly access to tracker commands so SKILL.md
instructions don't require inline Python.

Usage:
    uv run tracker-cli.py --state-dir .deepstate ready
    uv run tracker-cli.py --state-dir .deepstate close <issue-id> "reason"
    uv run tracker-cli.py --state-dir .deepstate show <issue-id>
    uv run tracker-cli.py --state-dir .deepstate list [--status open|closed]
    uv run tracker-cli.py --state-dir .deepstate prime
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.deepstate import DeepStateTracker


def cmd_ready(tracker: DeepStateTracker, args: argparse.Namespace) -> int:
    ready = tracker.ready()
    print(json.dumps(ready, indent=2))
    return 0


def cmd_close(tracker: DeepStateTracker, args: argparse.Namespace) -> int:
    try:
        result = tracker.close(args.issue_id, args.reason)
        print(json.dumps(result, indent=2))
        return 0
    except (KeyError, ValueError) as e:
        print(json.dumps({"error": str(e)}))
        return 1


def cmd_show(tracker: DeepStateTracker, args: argparse.Namespace) -> int:
    try:
        result = tracker.show(args.issue_id)
        print(json.dumps(result, indent=2))
        return 0
    except KeyError as e:
        print(json.dumps({"error": str(e)}))
        return 1


def cmd_list(tracker: DeepStateTracker, args: argparse.Namespace) -> int:
    issues = tracker.list_issues(status=args.status)
    print(json.dumps(issues, indent=2))
    return 0


def cmd_prime(tracker: DeepStateTracker, args: argparse.Namespace) -> int:
    print(tracker.prime())
    return 0


def main():
    parser = argparse.ArgumentParser(description="DeepStateTracker CLI")
    parser.add_argument(
        "--state-dir", required=True,
        help="Path to .deepstate directory",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ready", help="List unblocked issues")

    close_p = sub.add_parser("close", help="Close an issue")
    close_p.add_argument("issue_id", help="Issue ID to close")
    close_p.add_argument("reason", help="Reason for closing")

    show_p = sub.add_parser("show", help="Show issue details")
    show_p.add_argument("issue_id", help="Issue ID to show")

    list_p = sub.add_parser("list", help="List all issues")
    list_p.add_argument("--status", choices=["open", "closed"], help="Filter by status")

    sub.add_parser("prime", help="Generate context recovery summary")

    args = parser.parse_args()
    tracker = DeepStateTracker(state_dir=Path(args.state_dir))

    commands = {
        "ready": cmd_ready,
        "close": cmd_close,
        "show": cmd_show,
        "list": cmd_list,
        "prime": cmd_prime,
    }
    return commands[args.command](tracker, args)


if __name__ == "__main__":
    sys.exit(main())
