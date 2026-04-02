#!/usr/bin/env python3
"""PostToolUse hook: Nudge agent to update progress after file modifications.

Fires after Write/Edit tool calls. If an active deep-plan session exists,
reminds the agent to log what was done to progress.md.

Implements planning-with-files' "progress nudge" pattern — without this,
agents never remember to log what they just did.
"""

import json
import sys
from pathlib import Path


def get_active_planning_dir() -> Path | None:
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
        return 0

    progress_file = planning_dir / "progress.md"
    if progress_file.exists():
        print(
            "[deep-plan] Update progress.md with what you just completed. "
            "If this finishes the current step, mark it done and note any errors encountered."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
