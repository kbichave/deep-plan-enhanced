#!/usr/bin/env python3
"""PostToolUse hook for deep-implement: Nudge progress updates after file changes."""

import sys
from pathlib import Path


def main() -> int:
    marker = Path.home() / ".claude" / ".deep-implement-active"
    if not marker.exists():
        return 0

    active_dir = Path(marker.read_text().strip())
    if not active_dir.is_dir():
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
