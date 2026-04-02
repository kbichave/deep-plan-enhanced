#!/usr/bin/env python3
"""PreToolUse hook for deep-implement: Re-read implementation progress before tool calls.

Injects current section progress into context to prevent goal drift
during long implementation sessions.
"""

import json
import sys
from pathlib import Path


def get_active_dir() -> Path | None:
    for marker_name in (".deep-implement-active", ".deep-plan-active"):
        marker = Path.home() / ".claude" / marker_name
        if marker.exists():
            d = Path(marker.read_text().strip())
            if d.is_dir():
                return d
    return None


def main() -> int:
    active_dir = get_active_dir()
    if not active_dir:
        print(json.dumps({"decision": "allow"}))
        return 0

    # Try deep-implement's progress first, fall back to deep-plan's
    for progress_name in ("impl-progress.md", "progress.md"):
        progress_file = active_dir / progress_name
        if progress_file.exists():
            lines = progress_file.read_text().splitlines()[:30]
            print("\n".join(lines), file=sys.stderr)
            break

    print(json.dumps({"decision": "allow"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
