"""Workflow issue factory for deep-plan-enhanced.

Creates structured issue hierarchies in DeepStateTracker for each
workflow type: plan, discovery, section splitting, and plan-all.

Consumes task definitions from tasks.py. Does NOT contain workflow
logic — only issue creation.
"""

from __future__ import annotations

import bisect
from pathlib import Path

from lib.deepstate import DeepStateTracker
from lib.sections import parse_manifest_with_deps
from lib.tasks import (
    TASK_IDS,
    TASK_DEFINITIONS,
    TASK_DEPENDENCIES,
)

# Reference file mapping for plan workflow steps
_REFERENCE_FILES: dict[str, str] = {
    "research-decision": "research-protocol.md",
    "execute-research": "research-protocol.md",
    "detailed-interview": "interview-protocol.md",
    "save-interview": "interview-protocol.md",
    "write-spec": "plan-writing.md",
    "generate-plan": "plan-writing.md",
    "context-check-pre-review": "context-check.md",
    "external-review": "external-review.md",
    "integrate-feedback": "external-review.md",
    "apply-tdd": "tdd-approach.md",
    "context-check-pre-split": "context-check.md",
    "create-section-index": "section-index.md",
    "generate-section-tasks": "section-index.md",
    "write-sections": "section-splitting.md",
}

# Audit workflow reference files
_AUDIT_REFERENCE_FILES: dict[str, str] = {
    "quick-scan": "audit-research-protocol.md",
    "topic-enumeration": "audit-topic-enumeration.md",
    "deep-research": "audit-research-protocol.md",
    "coverage-validation": "audit-coverage-validation.md",
    "stakeholder-interview": "audit-interview-protocol.md",
    "generate-audit-docs": "audit-doc-writing.md",
    "generate-build-vs-buy": "audit-build-vs-buy.md",
    "generate-phase-specs": "audit-phasing.md",
    "external-review": "external-review.md",
}

# Context task IDs to skip (not real workflow steps)
_CONTEXT_TASK_IDS = {
    "context-plugin-root",
    "context-planning-dir",
    "context-initial-file",
    "context-review-mode",
}


def _build_description(
    task_id: str,
    task_def,
    plugin_root: str,
    planning_dir: str,
    ref_files: dict[str, str],
) -> str:
    """Build structured issue description with reference pointer."""
    lines = [
        f"## {task_def.subject}",
        "",
        task_def.description,
        "",
    ]
    ref_file = ref_files.get(task_id)
    if ref_file:
        lines.append(f"**Reference:** {plugin_root}/references/{ref_file}")
    lines.append(f"**Planning dir:** {planning_dir}")
    lines.extend([
        "",
        "**Acceptance Criteria:**",
        f"- {task_def.subject} completed successfully",
        "",
        "**Resume Here:**",
        "- Read the reference file first",
        "- Check existing output files for partial progress",
    ])
    return "\n".join(lines)


def create_plan_workflow(
    tracker: DeepStateTracker,
    *,
    plugin_root: str,
    planning_dir: str,
    initial_file: str,
    review_mode: str,
) -> str:
    """Create epic + 17 step issues for /deep-plan.

    Returns the epic title string.
    """
    spec_name = Path(initial_file).stem
    epic_title = f"deep-plan: {spec_name}"
    tracker.init(epic_title, {
        "plugin_root": plugin_root,
        "planning_dir": planning_dir,
        "initial_file": initial_file,
        "review_mode": review_mode,
    })

    # Create step issues in dependency order
    for step_num in sorted(TASK_IDS.keys()):
        task_id = TASK_IDS[step_num]
        task_def = TASK_DEFINITIONS[task_id]
        deps = TASK_DEPENDENCIES.get(task_id, [])

        # Filter out context dependencies — context is in epic metadata now
        real_deps = [d for d in deps if d not in _CONTEXT_TASK_IDS]

        description = _build_description(
            task_id, task_def, plugin_root, planning_dir, _REFERENCE_FILES
        )
        tracker.create(task_id, task_def.subject, description=description, depends_on=real_deps)

    return epic_title


def create_discovery_workflow(
    tracker: DeepStateTracker,
    *,
    plugin_root: str,
    planning_dir: str,
    initial_file: str,
    review_mode: str,
) -> str:
    """Create epic + step issues for /deep-discovery.

    Returns the epic title string.
    """
    from lib.tasks import AUDIT_TASK_IDS, AUDIT_TASK_DEFINITIONS, AUDIT_TASK_DEPENDENCIES

    spec_name = Path(initial_file).stem
    epic_title = f"deep-discovery: {spec_name}"
    tracker.init(epic_title, {
        "plugin_root": plugin_root,
        "planning_dir": planning_dir,
        "initial_file": initial_file,
        "review_mode": review_mode,
    })

    for step_num in sorted(AUDIT_TASK_IDS.keys()):
        task_id = AUDIT_TASK_IDS[step_num]
        task_def = AUDIT_TASK_DEFINITIONS[task_id]
        deps = AUDIT_TASK_DEPENDENCIES.get(task_id, [])
        real_deps = [d for d in deps if d not in _CONTEXT_TASK_IDS]

        description = _build_description(
            task_id, task_def, plugin_root, planning_dir, _AUDIT_REFERENCE_FILES
        )
        tracker.create(task_id, task_def.subject, description=description, depends_on=real_deps)

    return epic_title


def create_section_issues(
    tracker: DeepStateTracker,
    *,
    planning_dir: str,
    plugin_root: str,
) -> dict[str, str]:
    """Parse sections/index.md, create section issues with dependency edges.

    Returns {section_filename: issue_id} mapping.
    """
    index_path = Path(planning_dir) / "sections" / "index.md"
    if not index_path.exists():
        raise FileNotFoundError(f"sections/index.md not found at {index_path}")

    content = index_path.read_text()
    result = parse_manifest_with_deps(content)
    if not result["success"]:
        raise ValueError(f"Invalid SECTION_MANIFEST: {result['error']}")

    sections = result["sections"]
    dependencies = result["dependencies"]

    # The step that triggers section creation
    generate_step = "generate-section-tasks"

    mapping: dict[str, str] = {}
    for section_name in sections:
        # Skip if already exists (resume case)
        try:
            existing = tracker.show(section_name)
            mapping[section_name] = section_name
            continue
        except KeyError:
            pass

        # Build depends_on: explicit deps + the generate step
        section_deps = list(dependencies.get(section_name, []))
        # All sections depend on generate-section-tasks being done
        try:
            tracker.show(generate_step)
            section_deps.append(generate_step)
        except KeyError:
            pass  # generate step doesn't exist in tracker (standalone usage)

        # Remove duplicates
        section_deps = list(dict.fromkeys(section_deps))

        tracker.create(
            section_name,
            section_name,
            description=f"Implement section: {section_name}",
            depends_on=section_deps,
        )
        mapping[section_name] = section_name

    # Final Verification depends on all sections
    all_section_ids = list(mapping.values())
    try:
        tracker.show("final-verification")
    except KeyError:
        tracker.create(
            "final-verification",
            "Final Verification",
            description="Verify all sections are complete and tests pass",
            depends_on=all_section_ids,
        )

    # Output Summary depends on Final Verification
    try:
        tracker.show("output-summary")
    except KeyError:
        tracker.create(
            "output-summary",
            "Output Summary",
            description="Print generated files and next steps",
            depends_on=["final-verification"],
        )

    return mapping


def _toposort(deps: dict[str, list[str]]) -> list[str]:
    """Topological sort so dependencies are created before dependents.

    Falls back to alphabetical order for phases at the same depth.
    Raises ValueError on cycles.
    """
    in_degree: dict[str, int] = {node: 0 for node in deps}
    for node, predecessors in deps.items():
        in_degree.setdefault(node, 0)
        for p in predecessors:
            in_degree.setdefault(p, 0)
            in_degree[node] = in_degree.get(node, 0)

    # Recount properly
    in_degree = {node: 0 for node in deps}
    for node, predecessors in deps.items():
        in_degree[node] = len(predecessors)
        for p in predecessors:
            in_degree.setdefault(p, 0)

    queue = sorted(n for n, d in in_degree.items() if d == 0)
    result: list[str] = []

    while queue:
        node = queue.pop(0)
        result.append(node)
        # Find nodes that depend on this one and decrement their in-degree
        for candidate, predecessors in deps.items():
            if node in predecessors:
                in_degree[candidate] -= 1
                if in_degree[candidate] == 0:
                    # Insert in sorted position to keep deterministic order
                    bisect.insort(queue, candidate)

    if len(result) != len(in_degree):
        missing = set(in_degree) - set(result)
        raise ValueError(f"Cycle detected in phase dependencies: {missing}")

    return result


def parse_phasing_overview(phases_dir: str) -> dict[str, list[str]]:
    """Parse phasing-overview.md and return phase dependency graph.

    Returns dict mapping phase ID (e.g., "P01") to list of dependency phase IDs.
    Phases with no dependencies map to empty lists.

    Raises:
        FileNotFoundError: If phasing-overview.md doesn't exist
        ValueError: If no Dependency Graph section found
    """
    import re

    overview_path = Path(phases_dir) / "phasing-overview.md"
    if not overview_path.exists():
        raise FileNotFoundError(f"phasing-overview.md not found at {overview_path}")

    content = overview_path.read_text()

    # Find the Dependency Graph section
    dep_section_match = re.search(
        r'##\s+Dependency Graph\s*\n(.*?)(?=\n##\s|\Z)',
        content,
        re.DOTALL,
    )
    if not dep_section_match:
        raise ValueError("No '## Dependency Graph' section found in phasing-overview.md")

    dep_text = dep_section_match.group(1)

    # Parse arrow lines: P00 ──→ P01 ──→ P03 or P00 --> P01
    # Also handles └──→ prefix (decorative branch indicator)
    phase_pattern = re.compile(r'P\d+')
    deps: dict[str, list[str]] = {}

    for line in dep_text.split("\n"):
        # Strip decorative chars
        clean = line.strip().lstrip("└├│─ ")
        phases_in_line = phase_pattern.findall(clean)
        if len(phases_in_line) < 2:
            # Single phase or empty line — register phase with no new deps
            if len(phases_in_line) == 1:
                deps.setdefault(phases_in_line[0], [])
            continue

        # Arrow chain: each phase depends on the previous one
        for i in range(1, len(phases_in_line)):
            src = phases_in_line[i - 1]
            dst = phases_in_line[i]
            deps.setdefault(src, [])
            deps.setdefault(dst, [])
            if src not in deps[dst]:
                deps[dst].append(src)

    if not deps:
        raise ValueError("No phase dependencies found in Dependency Graph section")

    return deps


# Steps to skip for phases after the first (interview already done in discovery)
_SKIP_STEPS_AFTER_FIRST = {"detailed-interview", "save-interview"}

# Steps requiring human interaction — pre-closed in autonomous mode
_HUMAN_INTERACTIVE_STEPS = {
    "user-review",
    "context-check-pre-review",
    "context-check-pre-split",
}


def create_plan_all_workflow(
    tracker: DeepStateTracker,
    *,
    phases_dir: str,
    plugin_root: str,
    discovery_findings: str,
) -> str:
    """Parse phasing-overview.md, create phase sub-epics with dependency edges.

    Returns the top-level epic title.
    """
    phase_deps = parse_phasing_overview(phases_dir)

    # Determine project name from phases_dir
    project_name = Path(phases_dir).parent.name or "project"
    epic_title = f"plan-all: {project_name}"

    tracker.init(epic_title, {
        "phases_dir": phases_dir,
        "plugin_root": plugin_root,
        "discovery_findings": discovery_findings,
    })

    # Topological sort so dependencies are created before dependents
    sorted_phases = _toposort(phase_deps)

    is_first = True

    for phase_id in sorted_phases:
        deps = phase_deps[phase_id]
        phase_issue_id = f"phase-{phase_id}"

        # Phase issue depends on predecessor phases
        phase_dep_ids = [f"phase-{d}" for d in deps]
        tracker.create(phase_issue_id, phase_id, depends_on=phase_dep_ids)

        # Create 17 step issues within this phase
        prev_step_id = None
        for step_num in sorted(TASK_IDS.keys()):
            task_id = TASK_IDS[step_num]
            task_def = TASK_DEFINITIONS[task_id]
            namespaced_id = f"{phase_id}-{task_id}"

            # First step depends on phase issue; subsequent depend on previous step
            if prev_step_id is None:
                step_deps = [phase_issue_id]
            else:
                step_deps = [prev_step_id]

            description = task_def.description
            if not is_first and task_id in {"research-decision", "execute-research"}:
                description = (
                    f"Review discovery findings from {discovery_findings}. "
                    "Conduct focused research only on phase-specific topics."
                )

            tracker.create(
                namespaced_id,
                task_def.subject,
                description=description,
                depends_on=step_deps,
            )

            # For non-first phases, pre-close interview steps
            if not is_first and task_id in _SKIP_STEPS_AFTER_FIRST:
                tracker.close(namespaced_id, "Skipped: interview completed in discovery phase")

            prev_step_id = namespaced_id

        is_first = False

    return epic_title


def create_autonomous_workflow(
    tracker: DeepStateTracker,
    *,
    phases_dir: str,
    plugin_root: str,
    discovery_findings: str,
) -> str:
    """Create plan-all workflow with human-interactive steps pre-closed.

    Same as create_plan_all_workflow but also pre-closes interview,
    user-review, and context-check steps across ALL phases. This enables
    fully autonomous execution without human interaction.

    Returns the top-level epic title.
    """
    phase_deps = parse_phasing_overview(phases_dir)

    project_name = Path(phases_dir).parent.name or "project"
    epic_title = f"auto-plan-implement: {project_name}"

    tracker.init(epic_title, {
        "phases_dir": phases_dir,
        "plugin_root": plugin_root,
        "discovery_findings": discovery_findings,
        "autonomous": True,
    })

    sorted_phases = _toposort(phase_deps)
    is_first = True

    for phase_id in sorted_phases:
        deps = phase_deps[phase_id]
        phase_issue_id = f"phase-{phase_id}"

        phase_dep_ids = [f"phase-{d}" for d in deps]
        tracker.create(phase_issue_id, phase_id, depends_on=phase_dep_ids)

        prev_step_id = None
        for step_num in sorted(TASK_IDS.keys()):
            task_id = TASK_IDS[step_num]
            task_def = TASK_DEFINITIONS[task_id]
            namespaced_id = f"{phase_id}-{task_id}"

            if prev_step_id is None:
                step_deps = [phase_issue_id]
            else:
                step_deps = [prev_step_id]

            description = task_def.description
            if not is_first and task_id in {"research-decision", "execute-research"}:
                description = (
                    f"Review discovery findings from {discovery_findings}. "
                    "Conduct focused research only on phase-specific topics."
                )
            if task_id == "detailed-interview":
                description = (
                    "SELF-INTERVIEW: Launch two subagents — one as interviewer "
                    "(reads interview-protocol.md, asks probing questions about "
                    "this phase), one as stakeholder (answers using discovery "
                    f"findings from {discovery_findings} and the phase spec). "
                    "Write the Q&A transcript. Do NOT ask a human."
                )
            if task_id == "save-interview":
                description = (
                    "Save the self-interview transcript to claude-interview.md. "
                    "The interview was conducted by subagents, not a human."
                )

            tracker.create(
                namespaced_id,
                task_def.subject,
                description=description,
                depends_on=step_deps,
            )

            # Pre-close human-interactive steps (but NOT interview — handled by self-interview)
            if task_id in _HUMAN_INTERACTIVE_STEPS:
                reason = "Skipped: autonomous mode (no human review)"
                tracker.close(namespaced_id, reason)

            prev_step_id = namespaced_id

        is_first = False

    return epic_title
