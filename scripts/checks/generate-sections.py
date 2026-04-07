#!/usr/bin/env python3
"""Generate section issues in DeepStateTracker.

Replaces generate-section-tasks.py. Creates section issues with real
dependency edges from the SECTION_MANIFEST's depends_on syntax.

Usage:
    uv run generate-sections.py --planning-dir "/path/to/planning"
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.deepstate import DeepStateTracker
from lib.sections import check_section_progress
from lib.workflow import create_section_issues


def generate_sections(
    planning_dir: Path,
    plugin_root: Path | None = None,
) -> dict:
    """Generate section issues in the DeepStateTracker.

    Returns dict with: success, error, section_map, state, stats.
    """
    # Check section progress to determine state
    progress = check_section_progress(planning_dir)
    state = progress["state"]

    if state == "fresh":
        return {
            "success": False,
            "error": "No sections/index.md found. Create the section index first (step 18).",
            "section_map": {},
            "state": "fresh",
            "stats": {"total": 0, "completed": 0, "missing": 0},
        }

    if state == "invalid_index":
        return {
            "success": False,
            "error": f"Invalid sections/index.md: {progress.get('index_format', {}).get('error', 'unknown error')}",
            "section_map": {},
            "state": "invalid_index",
            "stats": {"total": 0, "completed": 0, "missing": 0},
        }

    # Check for existing deepstate
    state_dir = planning_dir / ".deepstate"
    if not state_dir.exists():
        return {
            "success": False,
            "error": "No .deepstate/ found. Run setup-session.py first.",
            "section_map": {},
            "state": state,
            "stats": {"total": 0, "completed": 0, "missing": 0},
        }

    tracker = DeepStateTracker(state_dir=state_dir)

    # If all sections are complete, return early
    defined = progress.get("defined_sections", [])
    completed = progress.get("completed_sections", [])
    missing = progress.get("missing_sections", [])

    if state == "complete":
        # Build mapping from existing issues or section names
        section_map = {s: s for s in defined}
        return {
            "success": True,
            "error": None,
            "section_map": section_map,
            "state": "complete",
            "stats": {
                "total": len(defined),
                "completed": len(completed),
                "missing": 0,
            },
        }

    # Create section issues via workflow factory
    section_map = create_section_issues(
        tracker,
        planning_dir=str(planning_dir),
        plugin_root=str(plugin_root) if plugin_root else "",
    )

    # Close issues for sections that already have files on disk
    for section_name in completed:
        try:
            issue = tracker.show(section_name)
            if issue["status"] == "open":
                tracker.close(section_name, "section file exists on disk")
        except KeyError:
            pass

    return {
        "success": True,
        "error": None,
        "section_map": section_map,
        "state": state,
        "stats": {
            "total": len(defined),
            "completed": len(completed),
            "missing": len(missing),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Generate section issues in DeepStateTracker")
    parser.add_argument("--planning-dir", required=True, help="Path to planning directory")
    parser.add_argument("--session-id", help="Session ID (passed through from hooks)")
    args = parser.parse_args()

    planning_dir = Path(args.planning_dir)
    if not planning_dir.is_absolute():
        planning_dir = Path.cwd() / planning_dir

    try:
        result = generate_sections(planning_dir)
    except Exception as e:
        result = {
            "success": False,
            "error": str(e),
            "section_map": {},
            "state": "error",
            "stats": {"total": 0, "completed": 0, "missing": 0},
        }

    print(json.dumps(result, indent=2))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
