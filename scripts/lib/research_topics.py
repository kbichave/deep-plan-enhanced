"""ResearchTopicStore — unified interface for research topic storage.

Two backends, one interface:
- MemPalaceBackend: uses MemPalace MCP tools (semantic search, KG, cross-project)
- FlatFileBackend: reads/writes research-topics.yaml in the session directory

Callers never know which backend is active. Backend is selected at construction
based on whether the MemPalace MCP is available.

Usage:
    store = ResearchTopicStore.create(planning_dir=Path("..."), project_slug="my-api-a3f9c1")
    store.create_topic("rt-01", "Authentication & Authorization", "security", "high", ["Q1", "Q2"])
    store.set_status("rt-01", "covered", findings_file="findings/rt-01-auth.md")
    missing = store.get_missing()
    pct = store.coverage_pct()
    prior = store.search_prior("oauth JWT session management")  # [] on FlatFileBackend
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_TOPICS_FILENAME = "research-topics.yaml"


# ── Abstract interface ────────────────────────────────────────────────────────


class ResearchTopicStore(ABC):
    """Abstract interface for research topic storage."""

    @abstractmethod
    def create_topic(
        self,
        id: str,
        topic: str,
        category: str,
        priority: str,
        questions: list[str],
    ) -> None:
        """Record a new research topic."""

    @abstractmethod
    def set_status(
        self,
        id: str,
        status: str,
        findings_file: str | None = None,
    ) -> None:
        """Update a topic's status (pending → covered | skipped)."""

    @abstractmethod
    def get_missing(self) -> list[dict[str, Any]]:
        """Return topics that are still pending (not covered, not skipped)."""

    @abstractmethod
    def coverage_pct(self) -> float:
        """Return coverage percentage, excluding skipped topics from denominator."""

    @abstractmethod
    def get_all(self) -> list[dict[str, Any]]:
        """Return all topics with their current status."""

    def search_prior(self, query: str) -> list[dict[str, Any]]:  # noqa: ARG002
        """Search prior-project research for relevant topics.

        Returns a list of topic dicts from previous projects. Always returns []
        on the FlatFileBackend (no cross-project storage).
        """
        return []

    @classmethod
    def create(
        cls,
        *,
        planning_dir: Path,
        project_slug: str,
    ) -> "ResearchTopicStore":
        """Factory: return MemPalaceBackend if available, else FlatFileBackend."""
        if _detect_mempalace():
            logger.info("MemPalace detected — using MemPalaceBackend for research topics")
            return MemPalaceBackend(planning_dir=planning_dir, project_slug=project_slug)
        logger.info("MemPalace not available — using FlatFileBackend for research topics")
        return FlatFileBackend(planning_dir=planning_dir)


# ── FlatFileBackend ───────────────────────────────────────────────────────────


def _load_yaml_simple(path: Path) -> dict[str, Any]:
    """Load research-topics.yaml. Tries PyYAML, falls back to JSON."""
    content = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore[import]
        data = yaml.safe_load(content)
        return data if isinstance(data, dict) else {}
    except ImportError:
        pass
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {}


def _dump_yaml_simple(data: dict[str, Any], path: Path) -> None:
    """Write dict as YAML. Uses PyYAML if available, falls back to JSON."""
    try:
        import yaml  # type: ignore[import]
        path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return
    except ImportError:
        pass
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


@dataclass
class FlatFileBackend(ResearchTopicStore):
    """Stores research topics in research-topics.yaml inside the session directory."""

    planning_dir: Path

    @property
    def _topics_path(self) -> Path:
        return self.planning_dir / _TOPICS_FILENAME

    def _load(self) -> dict[str, Any]:
        if not self._topics_path.exists():
            return {"metadata": {}, "topics": []}
        return _load_yaml_simple(self._topics_path)

    def _save(self, data: dict[str, Any]) -> None:
        self.planning_dir.mkdir(parents=True, exist_ok=True)
        _dump_yaml_simple(data, self._topics_path)

    def create_topic(
        self,
        id: str,
        topic: str,
        category: str,
        priority: str,
        questions: list[str],
    ) -> None:
        data = self._load()
        topics: list[dict] = data.setdefault("topics", [])
        # Idempotent: skip if already exists
        if any(t.get("id") == id for t in topics):
            return
        topics.append({
            "id": id,
            "topic": topic,
            "category": category,
            "priority": priority,
            "questions": questions,
            "status": "pending",
            "findings_file": None,
        })
        meta = data.setdefault("metadata", {})
        meta["total"] = len(topics)
        meta["covered"] = sum(1 for t in topics if t.get("status") == "covered")
        self._save(data)

    def set_status(
        self,
        id: str,
        status: str,
        findings_file: str | None = None,
    ) -> None:
        data = self._load()
        for t in data.get("topics", []):
            if t.get("id") == id:
                t["status"] = status
                if findings_file is not None:
                    t["findings_file"] = findings_file
                break
        # Recompute metadata counts
        topics = data.get("topics", [])
        meta = data.setdefault("metadata", {})
        covered = [t for t in topics if t.get("status") == "covered"]
        skipped = [t for t in topics if t.get("status") == "skipped"]
        researchable = len(topics) - len(skipped)
        meta["covered"] = len(covered)
        meta["coverage_pct"] = round(len(covered) / researchable * 100, 1) if researchable > 0 else 100.0
        self._save(data)

    def get_missing(self) -> list[dict[str, Any]]:
        data = self._load()
        return [t for t in data.get("topics", []) if t.get("status") == "pending"]

    def coverage_pct(self) -> float:
        data = self._load()
        topics = data.get("topics", [])
        skipped = [t for t in topics if t.get("status") == "skipped"]
        covered = [t for t in topics if t.get("status") == "covered"]
        researchable = len(topics) - len(skipped)
        if researchable == 0:
            return 100.0
        return round(len(covered) / researchable * 100, 1)

    def get_all(self) -> list[dict[str, Any]]:
        return self._load().get("topics", [])


# ── MemPalaceBackend ──────────────────────────────────────────────────────────


def _detect_mempalace() -> bool:
    """Return True if the MemPalace CLI or MCP server is available."""
    return shutil.which("mempalace") is not None or shutil.which("mempalace-mcp") is not None


def _mp_call(*args: str, timeout: int = 30) -> dict[str, Any] | None:
    """Call the MemPalace CLI and return parsed JSON output.

    Returns None on any failure — MemPalace is always optional.
    """
    cmd = ["mempalace", *args]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            logger.warning("mempalace %s failed (rc=%d): %s", " ".join(args), result.returncode, result.stderr[:200])
            return None
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        logger.warning("mempalace %s timed out after %ds", " ".join(args), timeout)
        return None
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("mempalace %s error: %s", " ".join(args), exc)
        return None


@dataclass
class MemPalaceBackend(ResearchTopicStore):
    """Stores research topics in MemPalace (semantic vector store + knowledge graph).

    Wing layout: project_slug
    Room layout: topic category (security, data-model, api, etc.)
    KG triples: {topic-id} → status → {pending|covered|skipped}
                {topic-id} → findings_file → {path}
                {topic-id} → project → {project_slug}

    Falls back to FlatFileBackend for all mutating operations if MemPalace
    calls fail, so a degraded MemPalace installation never breaks the workflow.
    """

    planning_dir: Path
    project_slug: str
    _fallback: FlatFileBackend = field(init=False)

    def __post_init__(self) -> None:
        self._fallback = FlatFileBackend(planning_dir=self.planning_dir)

    def create_topic(
        self,
        id: str,
        topic: str,
        category: str,
        priority: str,
        questions: list[str],
    ) -> None:
        # Always write to flat file as source of truth
        self._fallback.create_topic(id, topic, category, priority, questions)

        # Mirror to MemPalace (best-effort)
        content = (
            f"# {topic}\n\n"
            f"**Category:** {category}  **Priority:** {priority}  **ID:** {id}\n\n"
            f"## Questions\n" + "\n".join(f"- {q}" for q in questions)
        )
        _mp_call(
            "add-drawer",
            "--wing", self.project_slug,
            "--room", category,
            "--content", content,
            "--metadata", json.dumps({"topic_id": id, "status": "pending", "project": self.project_slug}),
        )
        _mp_call(
            "kg-add",
            "--subject", id,
            "--predicate", "status",
            "--object", "pending",
            "--source", self.project_slug,
        )
        _mp_call(
            "kg-add",
            "--subject", id,
            "--predicate", "project",
            "--object", self.project_slug,
        )

    def set_status(
        self,
        id: str,
        status: str,
        findings_file: str | None = None,
    ) -> None:
        # Source of truth: flat file
        self._fallback.set_status(id, status, findings_file)

        # Mirror to MemPalace KG (temporal: new triple, old one remains with valid_to set)
        _mp_call("kg-add", "--subject", id, "--predicate", "status", "--object", status, "--source", self.project_slug)
        if findings_file:
            _mp_call("kg-add", "--subject", id, "--predicate", "findings_file", "--object", findings_file, "--source", self.project_slug)

    def get_missing(self) -> list[dict[str, Any]]:
        # Read from flat file (authoritative, always consistent)
        return self._fallback.get_missing()

    def coverage_pct(self) -> float:
        return self._fallback.coverage_pct()

    def get_all(self) -> list[dict[str, Any]]:
        return self._fallback.get_all()

    def search_prior(self, query: str) -> list[dict[str, Any]]:
        """Search MemPalace for relevant research topics from prior projects."""
        result = _mp_call("search", "--query", query, "--room", "security", "--limit", "10")
        if not result:
            # Try without room filter
            result = _mp_call("search", "--query", query, "--limit", "10")
        if not result:
            return []

        # Parse MemPalace search results into topic-like dicts
        items = result if isinstance(result, list) else result.get("results", [])
        suggestions: list[dict[str, Any]] = []
        for item in items:
            metadata = item.get("metadata", {})
            topic_id = metadata.get("topic_id")
            if not topic_id:
                continue
            # Skip topics from the current project (not "prior")
            if metadata.get("project") == self.project_slug:
                continue
            suggestions.append({
                "id": topic_id,
                "topic": item.get("content", "")[:80],
                "source": "prior_project",
                "prior_project": metadata.get("project", "unknown"),
                "relevance_score": item.get("distance", None),
            })
        return suggestions


# ── Session indexing helper ───────────────────────────────────────────────────


def index_session_in_mempalace(
    *,
    project_slug: str,
    session_prefix: str,
    workflow: str,
    initial_file: str,
    planning_dir: str,
) -> None:
    """Record a session in MemPalace (best-effort, non-fatal).

    Called from setup-session.py after a new session is created.
    No-op if MemPalace is not available.
    """
    if not _detect_mempalace():
        return
    content = (
        f"Session: {session_prefix}\n"
        f"Workflow: {workflow}\n"
        f"Initial file: {initial_file}\n"
        f"Planning dir: {planning_dir}\n"
        f"Created: {datetime.now(timezone.utc).isoformat()}"
    )
    _mp_call(
        "add-drawer",
        "--wing", project_slug,
        "--room", "sessions",
        "--content", content,
        "--metadata", json.dumps({
            "session_prefix": session_prefix,
            "workflow": workflow,
            "planning_dir": planning_dir,
        }),
    )
