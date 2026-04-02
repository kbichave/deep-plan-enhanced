#!/usr/bin/env python3
"""PreToolUse hook: Re-read planning state before major tool calls.

Implements planning-with-files' "attention manipulation through recitation" pattern.
Before Write/Edit/Bash calls, injects the current planning step and recent progress
into context so the agent doesn't lose sight of goals after many tool calls.

Reads the active planning directory from ~/.claude/.deep-plan-active (written by
setup-planning-session.py) and outputs the first 30 lines of progress.md.

Always returns {"decision": "allow"} — never blocks tool execution.
"""

import json
import sys
from pathlib import Path


def get_active_planning_dir() -> Path | None:
    """Find the active deep-plan planning directory."""
    marker = Path.home() / ".claude" / ".deep-plan-active"
    if not marker.exists():
        return None
    planning_dir = Path(marker.read_text().strip())
    if planning_dir.is_dir():
        return planning_dir
    return None


def main() -> int:
    planning_dir = get_active_planning_dir()
    if not planning_dir:
        print(json.dumps({"decision": "allow"}))
        return 0

    progress_file = planning_dir / "progress.md"
    if not progress_file.exists():
        print(json.dumps({"decision": "allow"}))
        return 0

    # Read first 30 lines of progress.md for goal context
    lines = progress_file.read_text().splitlines()[:30]
    context = "\n".join(lines)

    # Output to stderr (visible in hook logs, keeps goals attended)
    print(context, file=sys.stderr)

    print(json.dumps({"decision": "allow"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
