"""Ubiquitous-language glossary extraction and merge.

Provides three pure functions used by the audit-doc-writer agent and the
``ubiquitous-language`` audit topic:

* :func:`extract_terms` — scan a repository for domain nouns.
* :func:`diff_merge` — additive merge of new terms into an existing
  glossary file, flagging definition conflicts without clobbering.
* :func:`promote_to_global` — copy a project glossary entry into the
  cross-project global glossary.

Output schema for every glossary file is the same Obsidian-friendly
markdown so files can live either in the vault (``glossary/<slug>/``)
or in the auto-memory directory when the vault is unavailable.

Stdlib only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


# --- Term extraction ----------------------------------------------------

CAMEL_RE = re.compile(r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b")
PYTHON_CLASS_RE = re.compile(r"^class\s+([A-Z][A-Za-z0-9_]*)\s*[:\(]", re.MULTILINE)
DBT_REF_RE = re.compile(r"\{\{\s*ref\(\s*['\"]([a-z][a-z0-9_]*)['\"]\s*\)\s*\}\}")
SNOWFLAKE_SCHEMA_RE = re.compile(r"\b([A-Z][A-Z0-9_]{2,})\.([A-Z][A-Z0-9_]{2,})\b")
HEADING_RE = re.compile(r"^#{1,3}\s+([A-Z][^\n]{2,80})$", re.MULTILINE)

TEXT_SUFFIXES = {".py", ".sql", ".md", ".yml", ".yaml", ".ts", ".tsx", ".js"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}


@dataclass
class Term:
    """A single glossary entry."""

    term: str
    definition: str = ""
    evidence: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        body = ["---", f"name: {self.term}", "type: ubiquitous-language", "---", "", f"# {self.term}", ""]
        if self.definition:
            body.append(self.definition)
            body.append("")
        if self.evidence:
            body.append("## Evidence")
            body.append("")
            for ev in self.evidence:
                body.append(f"- {ev}")
            body.append("")
        return "\n".join(body)


def extract_terms(repo_path: Path, *, max_files: int = 500) -> dict[str, Term]:
    """Walk ``repo_path`` and collect candidate domain terms.

    The walk is deterministic and bounded: it stops after ``max_files``
    text files so that huge repositories do not stall the workflow. The
    function favours coverage over depth — it captures evidence (file
    path) for each term but does not synthesise a definition. Definitions
    are filled in by the audit-doc-writer agent based on context.

    Returns a mapping of term -> :class:`Term`. Empty when no candidates
    are found.
    """

    repo_path = repo_path.expanduser().resolve()
    if not repo_path.is_dir():
        return {}

    found: dict[str, Term] = {}
    seen_files = 0
    for path in _iter_text_files(repo_path):
        if seen_files >= max_files:
            break
        seen_files += 1
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(path.relative_to(repo_path))
        for match in PYTHON_CLASS_RE.finditer(text):
            _record(found, match.group(1), rel)
        for match in CAMEL_RE.finditer(text):
            _record(found, match.group(0), rel)
        for match in DBT_REF_RE.finditer(text):
            _record(found, match.group(1), rel)
        for db, schema in SNOWFLAKE_SCHEMA_RE.findall(text):
            _record(found, schema, rel)
            _record(found, db, rel)
        if path.suffix == ".md":
            for match in HEADING_RE.finditer(text):
                heading = match.group(1).strip()
                if 2 < len(heading) < 80 and heading[0].isupper():
                    _record(found, heading, rel)

    return found


def _iter_text_files(root: Path):
    for path in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def _record(found: dict[str, Term], term: str, evidence: str) -> None:
    term = term.strip()
    if not term or len(term) < 3 or len(term) > 80:
        return
    if term.upper() == term and len(term) <= 3:
        return
    entry = found.setdefault(term, Term(term=term))
    if evidence not in entry.evidence:
        entry.evidence.append(evidence)
        entry.evidence[:] = entry.evidence[:5]


# --- Merge --------------------------------------------------------------


@dataclass
class MergeReport:
    """Result of merging extracted terms into an existing glossary."""

    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.added) + len(self.updated) + len(self.conflicts) + len(self.unchanged)


def diff_merge(glossary_dir: Path, new_terms: dict[str, Term]) -> MergeReport:
    """Merge ``new_terms`` into per-term files under ``glossary_dir``.

    Each term lives in its own file ``<sanitised>.md`` so wikilinks
    resolve cleanly inside Obsidian. Existing files are preserved when
    they already carry a definition; evidence lists are extended with new
    file paths but trimmed at five entries.

    Conflict detection: when a term file already has a non-empty
    definition AND the new term carries a different non-empty definition,
    the term is appended to ``conflicts`` and the file on disk is left
    untouched. The caller decides how to surface the conflict.
    """

    glossary_dir.mkdir(parents=True, exist_ok=True)
    report = MergeReport()
    for term in new_terms.values():
        path = glossary_dir / f"{_safe_filename(term.term)}.md"
        if not path.exists():
            path.write_text(term.to_markdown(), encoding="utf-8")
            report.added.append(term.term)
            continue
        existing = _parse_existing(path)
        if (
            existing.definition
            and term.definition
            and existing.definition.strip() != term.definition.strip()
        ):
            report.conflicts.append(term.term)
            continue
        merged = _merge_term(existing, term)
        if merged == existing:
            report.unchanged.append(term.term)
            continue
        path.write_text(merged.to_markdown(), encoding="utf-8")
        report.updated.append(term.term)
    return report


def _safe_filename(term: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", term).strip("-")
    return cleaned or "term"


def _parse_existing(path: Path) -> Term:
    text = path.read_text(encoding="utf-8")
    name = path.stem
    name_match = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
    if name_match:
        name = name_match.group(1).strip()
    definition = ""
    body_match = re.search(r"^#\s+.+?\n(?P<body>.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    if body_match:
        definition = body_match.group("body").strip()
    evidence: list[str] = []
    ev_block = re.search(r"^## Evidence\n(?P<body>.*)", text, re.MULTILINE | re.DOTALL)
    if ev_block:
        for line in ev_block.group("body").splitlines():
            line = line.strip()
            if line.startswith("- "):
                evidence.append(line[2:].strip())
    return Term(term=name, definition=definition, evidence=evidence)


def _merge_term(existing: Term, incoming: Term) -> Term:
    definition = existing.definition or incoming.definition
    evidence = list(existing.evidence)
    for ev in incoming.evidence:
        if ev not in evidence:
            evidence.append(ev)
    return Term(term=existing.term, definition=definition, evidence=evidence[:5])


# --- Promotion ----------------------------------------------------------


def promote_to_global(term: str, project_glossary_dirs: list[Path], *, global_dir: Path | None = None) -> Path | None:
    """Copy a term from the first project glossary that defines it into
    the global glossary.

    Returns the destination path on success, ``None`` when the term is
    not found in any of the supplied project glossaries.
    """

    target_dir = (global_dir or GLOBAL_GLOSSARY_DIR_DEFAULT).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    safe = _safe_filename(term)
    for project_dir in project_glossary_dirs:
        candidate = project_dir / f"{safe}.md"
        if candidate.is_file():
            destination = target_dir / f"{safe}.md"
            destination.write_text(candidate.read_text(encoding="utf-8"), encoding="utf-8")
            return destination
    return None


GLOBAL_GLOSSARY_DIR_DEFAULT = Path.home() / ".claude" / "glossary"
