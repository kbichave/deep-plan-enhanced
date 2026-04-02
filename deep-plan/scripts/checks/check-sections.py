#!/usr/bin/env python3
"""Check section-splitting progress and determine resume state.

Outputs JSON indicating where we are in the section-splitting workflow:
- fresh: No sections/ dir or empty → start from scratch
- has_index: index.md exists, no section files → start writing sections
- partial: index.md + some section files → resume from next_section
- complete: all sections written → done
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent to path for lib imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.sections import check_section_progress


def main():
    parser = argparse.ArgumentParser(description="Check section-splitting progress")
    parser.add_argument(
        "--planning-dir",
        required=True,
        type=Path,
        help="Path to planning directory"
    )
    args = parser.parse_args()

    result = check_section_progress(args.planning_dir)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
