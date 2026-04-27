"""Lightweight shallow-vs-deep module audit.

Runs heuristically over a Python repository to surface candidates that
:command:`/deep plan` should offer to deepen as part of the next plan.
The audit is deliberately fast and non-exhaustive — it reports leads,
not conclusions. The user always gets the final say.

Three signals are produced:

* ``shallow_modules`` — modules whose interface size is comparable to
  their implementation size (small functions doing one trivial thing
  each).
* ``hypothetical_seams`` — abstract base classes / Protocols with only
  one concrete subclass anywhere in the tree.
* ``scattered_knowledge`` — clusters of small files inside a single
  directory whose names share a stem (e.g. ``order_create.py``,
  ``order_validate.py``, ``order_persist.py``).

Stdlib only.
"""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Candidate:
    """A single deepening opportunity."""

    kind: str
    files: list[str]
    description: str
    suggested_action: str
    score: int = 0


@dataclass
class AuditResult:
    """Bundle returned by :func:`run_audit`."""

    shallow_modules: list[Candidate] = field(default_factory=list)
    hypothetical_seams: list[Candidate] = field(default_factory=list)
    scattered_knowledge: list[Candidate] = field(default_factory=list)

    @property
    def total(self) -> int:
        return (
            len(self.shallow_modules)
            + len(self.hypothetical_seams)
            + len(self.scattered_knowledge)
        )

    def all_candidates(self) -> list[Candidate]:
        return [
            *self.shallow_modules,
            *self.hypothetical_seams,
            *self.scattered_knowledge,
        ]


def run_audit(repo_path: Path, *, max_files: int = 400) -> AuditResult:
    """Walk ``repo_path`` and return all detected candidates.

    The walk is bounded by ``max_files`` to keep the audit cheap. Files
    that fail to parse are skipped silently.
    """

    repo_path = repo_path.expanduser().resolve()
    py_files = _collect_py_files(repo_path, max_files=max_files)
    return AuditResult(
        shallow_modules=find_shallow_modules(py_files, repo_path),
        hypothetical_seams=find_hypothetical_seams(py_files, repo_path),
        scattered_knowledge=find_scattered_knowledge(py_files, repo_path),
    )


def _collect_py_files(repo_path: Path, *, max_files: int) -> list[Path]:
    files: list[Path] = []
    for path in sorted(repo_path.rglob("*.py")):
        if any(part.startswith(".") or part in {"__pycache__", "node_modules", "venv", ".venv"} for part in path.parts):
            continue
        files.append(path)
        if len(files) >= max_files:
            break
    return files


def find_shallow_modules(py_files: list[Path], repo_path: Path) -> list[Candidate]:
    """Detect modules whose public interface and body have similar size.

    Heuristic: a module is shallow when it has between 2 and 8 public
    callables and the median callable body is fewer than three
    statements. A truly deep module concentrates substantial logic
    behind a small interface.
    """

    candidates: list[Candidate] = []
    for path in py_files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, OSError):
            continue
        publics = [
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and not node.name.startswith("_")
        ]
        if not 2 <= len(publics) <= 8:
            continue
        body_sizes = [_callable_body_size(node) for node in publics]
        if not body_sizes:
            continue
        median = sorted(body_sizes)[len(body_sizes) // 2]
        if median > 3:
            continue
        rel = str(path.relative_to(repo_path))
        candidates.append(
            Candidate(
                kind="shallow_module",
                files=[rel],
                description=(
                    f"{rel} exposes {len(publics)} public callables with median "
                    f"body size {median}. Interface is nearly as wide as the "
                    "implementation — the module gives callers little leverage."
                ),
                suggested_action="Concentrate logic behind a smaller interface, or fold into a sibling module.",
                score=10 - median,
            )
        )
    return candidates


def _callable_body_size(node: ast.AST) -> int:
    if isinstance(node, ast.ClassDef):
        return sum(_callable_body_size(child) for child in node.body)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return len([n for n in node.body if not isinstance(n, ast.Expr) or not _is_docstring(n)])
    return 0


def _is_docstring(expr: ast.Expr) -> bool:
    return isinstance(expr.value, ast.Constant) and isinstance(expr.value.value, str)


def find_hypothetical_seams(py_files: list[Path], repo_path: Path) -> list[Candidate]:
    """Detect ABCs / Protocols with exactly one concrete subclass.

    "One adapter is a hypothetical seam, two adapters is a real seam."
    The single-subclass case earns a deepening prompt because removing
    the abstraction often simplifies callers.
    """

    abc_defs: dict[str, str] = {}
    subclasses: dict[str, list[str]] = defaultdict(list)
    for path in py_files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, OSError):
            continue
        rel = str(path.relative_to(repo_path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            base_names = {_base_name(b) for b in node.bases}
            if base_names & {"ABC", "ABCMeta", "Protocol"}:
                abc_defs.setdefault(node.name, rel)
                continue
            for base in base_names:
                if base:
                    subclasses[base].append(rel)
    out: list[Candidate] = []
    for name, defined_in in abc_defs.items():
        children = subclasses.get(name, [])
        if len(children) == 1:
            out.append(
                Candidate(
                    kind="hypothetical_seam",
                    files=[defined_in, children[0]],
                    description=(
                        f"Abstract base {name} (defined in {defined_in}) has only "
                        f"one concrete implementation in {children[0]}. The seam "
                        "earns its keep only when a second adapter exists."
                    ),
                    suggested_action="Inline the single implementation or document why the seam will be re-used.",
                    score=5,
                )
            )
    return out


def _base_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


SCATTERED_PREFIX_RE = re.compile(r"^([a-z][a-z0-9]+?)_")


def find_scattered_knowledge(py_files: list[Path], repo_path: Path) -> list[Candidate]:
    """Detect groups of tiny files in one directory sharing a name stem.

    Three or more files smaller than 60 lines that share a stem
    (e.g. ``order_create.py``, ``order_persist.py``, ``order_validate.py``)
    are grouped as a single candidate; the suggestion is to fold them
    into a deeper module that owns the concept.
    """

    by_dir_prefix: dict[tuple[str, str], list[Path]] = defaultdict(list)
    for path in py_files:
        try:
            line_count = sum(1 for _ in path.read_text(encoding="utf-8", errors="replace").splitlines())
        except OSError:
            continue
        if line_count > 60:
            continue
        match = SCATTERED_PREFIX_RE.match(path.stem)
        if not match:
            continue
        by_dir_prefix[(str(path.parent), match.group(1))].append(path)

    out: list[Candidate] = []
    for (dir_str, prefix), paths in by_dir_prefix.items():
        if len(paths) < 3:
            continue
        rels = [str(p.relative_to(repo_path)) for p in paths]
        out.append(
            Candidate(
                kind="scattered_knowledge",
                files=rels,
                description=(
                    f"Directory {dir_str} holds {len(paths)} small files sharing the "
                    f"stem '{prefix}'. Knowledge about '{prefix}' is spread across "
                    "many modules instead of concentrated behind one interface."
                ),
                suggested_action=f"Fold the '{prefix}' files into a single module that owns the concept end-to-end.",
                score=4 + len(paths),
            )
        )
    return out


def render_audit_markdown(result: AuditResult) -> str:
    """Render an :class:`AuditResult` as the markdown payload that lives
    at ``findings/architecture-audit.md``.

    The format is stable so that ``agents/section-writer`` can consume it
    when checking section/audit overlap.
    """

    out: list[str] = ["# Architecture audit", ""]
    out.append(f"Total candidates: **{result.total}**")
    out.append("")
    for label, group in (
        ("Shallow modules", result.shallow_modules),
        ("Hypothetical seams", result.hypothetical_seams),
        ("Scattered knowledge", result.scattered_knowledge),
    ):
        out.append(f"## {label}")
        out.append("")
        if not group:
            out.append("None detected.")
            out.append("")
            continue
        for candidate in sorted(group, key=lambda c: -c.score):
            out.append(f"### {candidate.files[0]}")
            out.append("")
            out.append(candidate.description)
            out.append("")
            out.append(f"**Suggested action:** {candidate.suggested_action}")
            out.append("")
            if len(candidate.files) > 1:
                out.append("Files:")
                for f in candidate.files:
                    out.append(f"- `{f}`")
                out.append("")
    return "\n".join(out)
