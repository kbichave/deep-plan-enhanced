#!/usr/bin/env python3
"""Stop hook for deep-implement: Verify sections and request exit summary.

Session-aware: uses DEEP_SESSION_ID env var to find the correct session marker
in ~/.claude/.deep-implement-sessions/. Falls back to most recently modified
marker if env var is unavailable.
"""

import json
import os
import re
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
    if not progress_file.exists():
        return 0

    content = progress_file.read_text()

    # Count section checklist items
    total = len(re.findall(r"^- \[[ x]\]", content, re.MULTILINE))
    completed = len(re.findall(r"^- \[x\]", content, re.MULTILINE))

    if total == 0:
        return 0

    # Check if summary already exists (don't re-prompt)
    summary_file = active_dir / "impl-summary.md"
    has_summary = summary_file.exists() and summary_file.stat().st_size > 0

    if has_summary:
        return 0

    if completed >= total:
        output = {
            "followup_message": (
                f"[deep-implement] ALL SECTIONS COMPLETE ({completed}/{total}). "
                "Before exiting, write an implementation summary to "
                f"{active_dir}/impl-summary.md with:\n"
                "1. What was implemented (section-by-section, 1-2 sentences each)\n"
                "2. Key technical decisions made\n"
                "3. Known issues or TODOs remaining\n"
                "4. Test results (pass/fail count)\n"
                "5. Files created or modified\n"
                "Then you may exit."
            )
        }
    else:
        pending = total - completed
        output = {
            "followup_message": (
                f"[deep-implement] Implementation incomplete ({completed}/{total} sections, "
                f"{pending} remaining). Before exiting, write a session summary to "
                f"{active_dir}/impl-summary.md with:\n"
                "1. What was completed this session\n"
                "2. What remains and any blockers\n"
                "3. Errors encountered and how they were resolved\n"
                "4. Where to pick up next session\n"
                "Then you may exit."
            )
        }

    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
