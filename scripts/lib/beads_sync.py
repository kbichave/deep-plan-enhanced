"""Optional beads write-through sync layer.

Wraps DeepStateTracker and mirrors operations to bd CLI when available.
Beads failure is always non-fatal -- deepstate is the source of truth.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from lib.deepstate import DeepStateTracker

logger = logging.getLogger(__name__)


@dataclass
class BeadsSyncTracker:
    """Write-through wrapper: deepstate is primary, beads is secondary."""

    tracker: DeepStateTracker
    beads_available: bool
    beads_cwd: Path | None = None

    def _bd(self, *args: str) -> dict | None:
        """Run bd command. Returns parsed JSON on success, None on any failure."""
        if not self.beads_available:
            return None
        try:
            result = subprocess.run(
                ["bd", *args, "--json"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.beads_cwd,
            )
            if result.returncode != 0:
                logger.warning("bd %s failed (exit %d): %s", args[0], result.returncode, result.stderr)
                return None
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            logger.warning("bd %s timed out", args[0])
            return None
        except json.JSONDecodeError:
            logger.warning("bd %s returned non-JSON output", args[0])
            return None
        except FileNotFoundError:
            logger.warning("bd binary not found despite detection")
            return None

    def _bd_raw(self, *args: str) -> str | None:
        """Run bd command returning raw stdout (for prime). None on failure."""
        if not self.beads_available:
            return None
        try:
            result = subprocess.run(
                ["bd", *args],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.beads_cwd,
            )
            if result.returncode != 0:
                return None
            return result.stdout.strip() or None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def init(self, epic_title: str, context: dict) -> None:
        """Initialize tracker and optionally beads."""
        self.tracker.init(epic_title, context)
        self._bd("init", "--stealth", "--skip-hooks")

    def create(self, issue_id: str, title: str, **kwargs) -> dict:
        """Create issue in deepstate, mirror to beads."""
        result = self.tracker.create(issue_id, title, **kwargs)
        self._bd("create", title)
        return result

    def ready(self) -> list[dict]:
        """Always read from deepstate."""
        return self.tracker.ready()

    def close(self, issue_id: str, reason: str) -> dict:
        """Close in deepstate, mirror to beads."""
        result = self.tracker.close(issue_id, reason)
        self._bd("close", issue_id)
        return result

    def show(self, issue_id: str) -> dict:
        """Read from deepstate."""
        return self.tracker.show(issue_id)

    def update(self, issue_id: str, **kwargs) -> dict:
        """Update in deepstate, mirror to beads."""
        result = self.tracker.update(issue_id, **kwargs)
        self._bd("update", issue_id)
        return result

    def list_issues(self, **kwargs) -> list[dict]:
        """Read from deepstate."""
        return self.tracker.list_issues(**kwargs)

    def prime(self) -> str:
        """Use bd prime when available (richer output), fallback to deepstate."""
        if self.beads_available:
            bd_prime = self._bd_raw("prime")
            if bd_prime:
                return bd_prime
        return self.tracker.prime()

    def dep_tree(self, issue_id: str) -> str:
        """Read from deepstate."""
        return self.tracker.dep_tree(issue_id)


def detect_beads() -> bool:
    """Return True if bd CLI is on PATH."""
    return shutil.which("bd") is not None
