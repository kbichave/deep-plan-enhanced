#!/usr/bin/env python3
"""Stop hook for deep-implement: Verify all sections implemented before exit."""

import json
import re
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
    if not progress_file.exists():
        return 0

    content = progress_file.read_text()

    # Count section checklist items
    total = len(re.findall(r"^- \[[ x]\]", content, re.MULTILINE))
    completed = len(re.findall(r"^- \[x\]", content, re.MULTILINE))

    if total == 0:
        return 0

    if completed >= total:
        output = {
            "followup_message": (
                f"[deep-implement] ALL SECTIONS COMPLETE ({completed}/{total}). "
                "Run final verification: full test suite, check for TODOs, then summarize."
            )
        }
    else:
        pending = total - completed
        output = {
            "followup_message": (
                f"[deep-implement] Implementation incomplete ({completed}/{total} sections, "
                f"{pending} remaining). Read impl-progress.md and continue with the next section."
            )
        }

    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
