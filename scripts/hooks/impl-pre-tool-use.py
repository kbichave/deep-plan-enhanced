#!/usr/bin/env python3
"""PreToolUse hook: Always allow, no output beyond the decision.

The attention manipulation pattern (re-reading progress) caused issues
with Claude Code's hook parser when progress content leaked to stdout.
PostToolUse and Stop hooks handle the discipline layer instead.
"""

import json
import sys


def main() -> int:
    print(json.dumps({"decision": "allow"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
