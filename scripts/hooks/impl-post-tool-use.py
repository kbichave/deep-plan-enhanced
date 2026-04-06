#!/usr/bin/env python3
"""PostToolUse hook for deep-implement: Nudge progress updates after file changes.

Session-aware: uses DEEP_SESSION_ID env var to find the correct session marker
in ~/.claude/.deep-implement-sessions/. Falls back to most recently modified
marker if env var is unavailable.
"""

import os
import sys
from pathlib import Path


def find_active_dir() -> Path | None:
    """Find the active planning directory for the current session."""
    sessions_dir = Path.home() / ".claude" / ".deep-implement-sessions"
    if not sessions_dir.is_dir():
        return None

    # Try session-specific marker first
    session_id = os.environ.get("DEEP_SESSION_ID")
    if session_id:
        marker = sessions_dir / f"{session_id}.marker"
        if marker.exists():
            active_dir = Path(marker.read_text().strip())
            return active_dir if active_dir.is_dir() else None

    # Fallback: most recently modified marker
    markers = sorted(sessions_dir.glob("*.marker"), key=lambda p: p.stat().st_mtime, reverse=True)
    for marker in markers:
        active_dir = Path(marker.read_text().strip())
        if active_dir.is_dir():
            return active_dir

    return None


def main() -> int:
    active_dir = find_active_dir()
    if not active_dir:
        return 0

    progress_file = active_dir / "impl-progress.md"
    if progress_file.exists():
        print(
            "[deep-implement] Update impl-progress.md with what you just did. "
            "If the current section is done, check it off and update impl-task-plan.md status."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
