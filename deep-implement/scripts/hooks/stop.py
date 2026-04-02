#!/usr/bin/env python3
"""Stop hook for deep-implement: Verify sections and request exit summary."""

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

    # Check if summary already exists (don't re-prompt)
    summary_file = active_dir / "impl-summary.md"
    has_summary = summary_file.exists() and summary_file.stat().st_size > 0

    if has_summary:
        # Summary written, allow clean exit
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
