#!/usr/bin/env python3
"""Stop hook: Verify planning workflow completion before allowing exit.

Checks progress.md for incomplete steps. If steps remain, outputs a
followup_message to auto-continue. Prevents premature exit mid-workflow.

Implements planning-with-files' "completion verification" pattern.
"""

import json
import re
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
        # No active session — allow stop
        return 0

    progress_file = planning_dir / "progress.md"
    if not progress_file.exists():
        return 0

    content = progress_file.read_text()

    # Count steps by status markers
    total = len(re.findall(r"^- \[[ x]\]", content, re.MULTILINE))
    completed = len(re.findall(r"^- \[x\]", content, re.MULTILINE))
    pending = total - completed

    if total == 0:
        # No checklist found — allow stop
        return 0

    if completed >= total:
        output = {
            "followup_message": (
                f"[deep-plan] ALL STEPS COMPLETE ({completed}/{total}). "
                "Planning workflow finished. You can proceed to implementation "
                "with /deep-implement or start a new session."
            )
        }
    else:
        output = {
            "followup_message": (
                f"[deep-plan] Workflow incomplete ({completed}/{total} steps done, "
                f"{pending} remaining). Read progress.md in {planning_dir} and "
                "continue from the current step."
            )
        }

    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
