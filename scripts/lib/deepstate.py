"""DeepState — pure Python dependency tracker for deep-plan-enhanced.

Stores workflow state as JSON in .deepstate/state.json with atomic writes.
No external dependencies — stdlib only.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DeepStateTracker:
    """Minimal dependency graph tracker stored as a single JSON file.

    Usage:
        tracker = DeepStateTracker(state_dir=Path(".deepstate"))
        tracker.init("my-epic", {"planning_dir": "/path"})
        tracker.create("step-01", "Research", depends_on=[])
        tracker.create("step-02", "Interview", depends_on=["step-01"])
        ready = tracker.ready()  # -> [step-01]
        tracker.close("step-01", "Research complete")
        ready = tracker.ready()  # -> [step-02]
    """

    state_dir: Path

    def init(self, epic_title: str, context: dict) -> None:
        """Create .deepstate/ directory and write initial state.json.

        Raises FileExistsError if state.json already exists.
        """
        self.state_dir.mkdir(parents=True, exist_ok=True)
        state_file = self.state_dir / "state.json"
        if state_file.exists():
            raise FileExistsError(f"{state_file} already exists")
        state = {
            "epic": {
                "title": epic_title,
                "context": context,
            },
            "issues": {},
        }
        self._save(state)

    def create(
        self,
        issue_id: str,
        title: str,
        *,
        description: str = "",
        depends_on: list[str] | None = None,
    ) -> dict:
        """Create an issue. Returns the created issue dict.

        Raises ValueError on duplicate ID or invalid dependency target.
        """
        state = self._load()
        if issue_id in state["issues"]:
            raise ValueError(f"Issue '{issue_id}' already exists")
        deps = depends_on or []
        for dep in deps:
            if dep not in state["issues"]:
                raise ValueError(
                    f"Dependency '{dep}' does not exist — "
                    f"create it before '{issue_id}'"
                )
        issue = {
            "title": title,
            "status": "open",
            "description": description,
            "depends_on": deps,
            "closed_reason": None,
        }
        state["issues"][issue_id] = issue
        self._save(state)
        return {"id": issue_id, **issue}

    def ready(self) -> list[dict]:
        """Return open issues whose depends_on are ALL closed."""
        state = self._load()
        result = []
        for issue_id, issue in state["issues"].items():
            if issue["status"] != "open":
                continue
            all_deps_closed = all(
                state["issues"][dep]["status"] == "closed"
                for dep in issue["depends_on"]
            )
            if all_deps_closed:
                result.append({"id": issue_id, **issue})
        return result

    def close(self, issue_id: str, reason: str) -> dict:
        """Mark issue as closed with a reason string.

        Raises KeyError if issue doesn't exist.
        Raises ValueError if issue is already closed.
        """
        state = self._load()
        if issue_id not in state["issues"]:
            raise KeyError(f"Issue '{issue_id}' not found")
        issue = state["issues"][issue_id]
        if issue["status"] == "closed":
            raise ValueError(f"Issue '{issue_id}' is already closed")
        issue["status"] = "closed"
        issue["closed_reason"] = reason
        self._save(state)
        return {"id": issue_id, **issue}

    def show(self, issue_id: str) -> dict:
        """Get full issue dict. Raises KeyError if not found."""
        state = self._load()
        if issue_id not in state["issues"]:
            raise KeyError(f"Issue '{issue_id}' not found")
        return {"id": issue_id, **state["issues"][issue_id]}

    def update(
        self,
        issue_id: str,
        *,
        status: str | None = None,
        description: str | None = None,
    ) -> dict:
        """Update mutable fields. Only overwrites fields that are not None."""
        state = self._load()
        if issue_id not in state["issues"]:
            raise KeyError(f"Issue '{issue_id}' not found")
        issue = state["issues"][issue_id]
        if status is not None:
            issue["status"] = status
        if description is not None:
            issue["description"] = description
        self._save(state)
        return {"id": issue_id, **issue}

    def list_issues(self, *, status: str | None = None) -> list[dict]:
        """List all issues, optionally filtered by status."""
        state = self._load()
        result = []
        for issue_id, issue in state["issues"].items():
            if status is not None and issue["status"] != status:
                continue
            result.append({"id": issue_id, **issue})
        return result

    def prime(self) -> str:
        """Generate a context recovery summary.

        Writes to {state_dir}/prime.md and returns the string.
        """
        state = self._load()
        epic_title = state["epic"]["title"]
        issues = state["issues"]
        total = len(issues)
        closed = sum(1 for i in issues.values() if i["status"] == "closed")
        ready_issues = self.ready()
        ready_titles = [f"- {i['title']}" for i in ready_issues[:5]]

        lines = [
            f"# {epic_title}",
            f"Progress: {closed}/{total} issues closed",
            "",
        ]
        if ready_titles:
            lines.append("Next ready:")
            lines.extend(ready_titles)
        else:
            lines.append("All issues closed." if closed == total else "No issues ready (check dependencies).")

        summary = "\n".join(lines)
        (self.state_dir / "prime.md").write_text(summary)
        return summary

    def dep_tree(self, issue_id: str) -> str:
        """ASCII dependency tree rooted at issue_id."""
        state = self._load()
        if issue_id not in state["issues"]:
            raise KeyError(f"Issue '{issue_id}' not found")

        def _format_node(iid: str, indent: int = 0) -> list[str]:
            issue = state["issues"][iid]
            marker = "[x]" if issue["status"] == "closed" else "[ ]"
            prefix = "  " * indent
            lines = [f"{prefix}{marker} {iid}: {issue['title']}"]
            for dep in issue["depends_on"]:
                if dep in state["issues"]:
                    lines.extend(_format_node(dep, indent + 1))
            return lines

        return "\n".join(_format_node(issue_id))

    def _load(self) -> dict:
        """Read and parse state.json."""
        state_file = self.state_dir / "state.json"
        if not state_file.exists():
            raise FileNotFoundError(f"{state_file} does not exist")
        return json.loads(state_file.read_text())

    def _save(self, state: dict) -> None:
        """Atomic write: write to state.json.tmp, then os.rename."""
        tmp_file = self.state_dir / "state.json.tmp"
        state_file = self.state_dir / "state.json"
        tmp_file.write_text(json.dumps(state, indent=2))
        os.rename(tmp_file, state_file)
