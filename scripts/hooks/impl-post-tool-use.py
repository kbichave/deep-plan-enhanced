#!/usr/bin/env python3
"""PostToolUse hook for deep-implement: Truncation guard + progress nudge.

Session-aware: uses DEEP_SESSION_ID env var to find the correct session marker
in ~/.claude/.deep-implement-sessions/. Falls back to most recently modified
marker if env var is unavailable.

Also checks for truncated writes to critical planning files via a size cache.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Critical planning files where truncation is catastrophic
CRITICAL_FILES = {
    "claude-plan.md",
    "claude-plan-tdd.md",
    "index.md",
    "state.json",
    "progress.md",
    "findings.md",
}

# Shrinkage threshold: warn if file shrinks by more than this fraction
SHRINKAGE_THRESHOLD = 0.5


def find_active_dir() -> Path | None:
    """Find the active planning directory for the current session."""
    sessions_dir = Path.home() / ".claude" / ".deep-implement-sessions"
    if not sessions_dir.is_dir():
        return None

    session_id = os.environ.get("DEEP_SESSION_ID")
    if session_id:
        marker = sessions_dir / f"{session_id}.marker"
        if marker.exists():
            active_dir = Path(marker.read_text().strip())
            return active_dir if active_dir.is_dir() else None

    markers = sorted(sessions_dir.glob("*.marker"), key=lambda p: p.stat().st_mtime, reverse=True)
    for marker in markers:
        active_dir = Path(marker.read_text().strip())
        if active_dir.is_dir():
            return active_dir

    return None


def find_planning_dir() -> Path | None:
    """Find the planning directory from either deep-implement or deep-plan markers."""
    # Try deep-implement session marker first
    impl_dir = find_active_dir()
    if impl_dir:
        return impl_dir

    # Try deep-plan active marker
    active_marker = Path.home() / ".claude" / ".deep-plan-active"
    if active_marker.exists():
        planning_dir = Path(active_marker.read_text().strip())
        if planning_dir.is_dir():
            return planning_dir

    return None


def check_truncation(planning_dir: Path) -> list[str]:
    """Check for truncated writes to critical files. Returns warning messages."""
    cache_file = planning_dir / ".file-sizes.json"
    warnings = []

    # Load cached sizes
    cached_sizes: dict[str, int] = {}
    if cache_file.exists():
        try:
            cached_sizes = json.loads(cache_file.read_text())
        except (json.JSONDecodeError, OSError):
            cached_sizes = {}

    # Scan current sizes of critical files
    current_sizes: dict[str, int] = {}
    for name in CRITICAL_FILES:
        # Check in planning_dir and planning_dir/sections/
        for search_dir in [planning_dir, planning_dir / "sections", planning_dir / ".deepstate"]:
            candidate = search_dir / name
            if candidate.exists():
                current_sizes[name] = candidate.stat().st_size
                break

    # Compare against cache
    for name, current_size in current_sizes.items():
        if name in cached_sizes:
            old_size = cached_sizes[name]
            if old_size > 0 and current_size < old_size * (1 - SHRINKAGE_THRESHOLD):
                pct = round((1 - current_size / old_size) * 100)
                warnings.append(
                    f"[deep-plan] WARNING: {name} shrank by {pct}% "
                    f"(from {old_size} to {current_size} bytes). "
                    f"This may indicate truncated output. "
                    f"Please verify the file content is complete."
                )

    # Update cache
    if current_sizes:
        try:
            cache_file.write_text(json.dumps(current_sizes, indent=2))
        except OSError:
            pass

    return warnings


def main() -> int:
    planning_dir = find_planning_dir()
    if not planning_dir:
        return 0

    # Truncation guard (runs for both deep-plan and deep-implement)
    truncation_warnings = check_truncation(planning_dir)
    for warning in truncation_warnings:
        print(warning)

    # Progress nudge (deep-implement only)
    progress_file = planning_dir / "impl-progress.md"
    if progress_file.exists():
        print(
            "[deep-implement] Update impl-progress.md with what you just did. "
            "If the current section is done, check it off and update impl-task-plan.md status."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
