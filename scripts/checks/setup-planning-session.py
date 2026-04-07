#!/usr/bin/env python3
"""Setup planning session for deep-plan workflow.

Combined script that:
1. Validates the spec file input
2. Determines the planning directory (parent of spec file)
3. Creates the planning directory if needed
4. Checks planning state to determine new vs resume (including section progress)
5. Writes task files directly to ~/.claude/tasks/<task_list_id>/
6. Generates section tasks if sections/index.md exists

Usage:
    uv run setup-planning-session.py --file "/path/to/spec.md" --plugin-root "/path/to/plugin"
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add parent to path for lib imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.config import get_or_create_session_config, ConfigError, SESSION_CONFIG_FILENAME
from lib.transcript_validator import validate_transcript_format
from lib.sections import check_section_progress
from lib.task_reconciliation import TaskListContext
from lib.task_storage import (
    SECTION_INSERT_POSITION,
    TaskToWrite,
    build_dependency_graph,
    build_section_dependencies,
    calculate_task_positions,
    check_for_conflict,
    generate_section_tasks_to_write,
    write_tasks,
)
from lib.tasks import (
    STEP_NAMES,
    TASK_DEPENDENCIES,
    TASK_IDS,
    TaskStatus,
    generate_expected_tasks,
    # Audit workflow
    AUDIT_STEP_NAMES,
    AUDIT_TASK_DEPENDENCIES,
    AUDIT_TASK_IDS,
    generate_expected_audit_tasks,
)

# Context task IDs (positions 1-4)
CONTEXT_TASK_IDS = [
    "context-plugin-root",
    "context-planning-dir",
    "context-initial-file",
    "context-review-mode",
]


def find_existing_session_dir(spec_parent: Path, session_id: str) -> Path | None:
    """Find an existing session directory for this session ID.

    Checks by prefix match first (fast path), then scans all session configs
    for a matching session_id field (handles prefix collisions).

    Args:
        spec_parent: Parent directory of the spec file
        session_id: Current session ID (UUID string)

    Returns:
        Path to existing session directory, or None if not found
    """
    sessions_dir = spec_parent / "sessions"
    if not sessions_dir.exists():
        return None

    prefix = session_id[:8]
    candidate = sessions_dir / prefix
    if candidate.exists() and (candidate / SESSION_CONFIG_FILENAME).exists():
        return candidate

    # Fallback: scan all session dirs for matching session_id in config
    for d in sessions_dir.iterdir():
        if not d.is_dir():
            continue
        config_path = d / SESSION_CONFIG_FILENAME
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)
                if config.get("session_id") == session_id:
                    return d
            except (json.JSONDecodeError, OSError):
                continue
    return None


def resolve_planning_dir(spec_parent: Path, session_id: str | None) -> Path:
    """Resolve the planning directory for this session.

    Session isolation: each session gets its own subdirectory under
    spec_parent/sessions/<8-char-prefix>/ to prevent concurrent sessions
    from overwriting each other's planning files.

    Backwards compatibility: if spec_parent already contains planning files
    (legacy single-session layout), use spec_parent directly.

    Args:
        spec_parent: Parent directory of the spec file
        session_id: Current session ID (may be None if unavailable)

    Returns:
        Path to the planning directory (created if needed)
    """
    # Backwards compatibility: if legacy planning files exist at root, use root
    legacy_file_markers = [
        "claude-research.md", "claude-plan.md", "claude-spec.md",
        "claude-interview.md", "claude-plan-tdd.md",
        "claude-integration-notes.md", SESSION_CONFIG_FILENAME,
    ]
    legacy_dir_markers = ["reviews", "sections"]
    has_legacy_files = any((spec_parent / f).exists() for f in legacy_file_markers)
    has_legacy_dirs = any((spec_parent / d).is_dir() for d in legacy_dir_markers)
    if has_legacy_files or has_legacy_dirs:
        return spec_parent

    # No session ID available — fall back to spec_parent (legacy behavior)
    if not session_id:
        return spec_parent

    # Check for existing session dir (resume case)
    existing = find_existing_session_dir(spec_parent, session_id)
    if existing:
        return existing

    # Create new session directory
    prefix = session_id[:8]
    planning_dir = spec_parent / "sessions" / prefix
    planning_dir.mkdir(parents=True, exist_ok=True)
    return planning_dir


def scan_planning_files(planning_dir: Path) -> dict:
    """Scan planning directory for existing files."""
    files = {
        "research": (planning_dir / "claude-research.md").exists(),
        "interview": (planning_dir / "claude-interview.md").exists(),
        "spec": (planning_dir / "claude-spec.md").exists(),
        "plan": (planning_dir / "claude-plan.md").exists(),
        "integration_notes": (planning_dir / "claude-integration-notes.md").exists(),
        "plan_tdd": (planning_dir / "claude-plan-tdd.md").exists(),
        "reviews": [],
        "sections": [],
        "sections_index": False,
    }

    # Check for review files
    reviews_dir = planning_dir / "reviews"
    if reviews_dir.exists():
        files["reviews"] = [f.name for f in reviews_dir.glob("*.md")]

    # Check for section files
    sections_dir = planning_dir / "sections"
    if sections_dir.exists():
        files["sections"] = [f.name for f in sections_dir.glob("section-*.md")]
        files["sections_index"] = (sections_dir / "index.md").exists()

    return files


def infer_resume_step(files: dict, section_progress: dict) -> tuple[int | None, str]:
    """Infer which step to resume from based on files and section progress.

    Returns (resume_step, last_completed_description).
    Returns (None, "complete") if workflow is complete.
    Returns (6, "none") if fresh start.

    Step mapping (from SKILL.md):
    - 7: Execute research -> claude-research.md
    - 9: Save interview -> claude-interview.md
    - 10: Write spec -> claude-spec.md
    - 11: Generate plan -> claude-plan.md
    - 13: External review -> reviews/*.md
    - 14: Integrate feedback -> claude-integration-notes.md
    - 16: TDD approach -> claude-plan-tdd.md
    - 18: Create section index -> sections/index.md
    - 19: Generate section tasks
    - 20: Write section files -> sections/section-*.md
    - Complete: ALL sections written (not just index.md)

    IMPORTANT: Before resuming at a later step, we verify that prerequisite files
    exist. If a prerequisite is missing, we resume from the step that creates it.
    This prevents issues where Claude skipped a step but created later files.
    """
    # Check sections state - this is the final stage
    if files["sections_index"]:
        # PREREQUISITE CHECK: sections require claude-plan-tdd.md (from step 16)
        if not files["plan_tdd"]:
            # TDD plan missing but index exists - Claude skipped step 16
            # Resume at step 16 to create the TDD plan, then overwrite sections/
            return 16, "MISSING PREREQUISITE: claude-plan-tdd.md - OVERWRITE sections/ after creating TDD plan"

        section_state = section_progress["state"]

        if section_state == "complete":
            # All sections written - workflow complete
            return None, "complete"
        elif section_state in ("partial", "has_index"):
            # Index exists, sections started but not complete - resume at step 19
            # (generate section tasks, which will show progress)
            progress = section_progress["progress"]
            next_section = section_progress["next_section"]
            return 19, f"sections {progress}, next: {next_section}"

    # Check in reverse order (highest step first) for pre-section stages
    if files["sections"]:
        # PREREQUISITE CHECK: section files require claude-plan-tdd.md
        if not files["plan_tdd"]:
            return 16, "MISSING PREREQUISITE: claude-plan-tdd.md - OVERWRITE sections/ after creating TDD plan"
        # Has section files but no index - resume at 18 to create index
        return 18, "section files exist but no index"

    if files["plan_tdd"]:
        # TDD plan done - resume at 17 (context check before split)
        return 17, "TDD plan complete"

    if files["integration_notes"]:
        # PREREQUISITE CHECK: integration notes require plan
        if not files["plan"]:
            return 11, "MISSING PREREQUISITE: claude-plan.md - OVERWRITE claude-integration-notes.md after creating plan"
        # Integration done - resume at 15 (user review)
        return 15, "feedback integrated"

    if files["reviews"]:
        # PREREQUISITE CHECK: reviews require plan
        if not files["plan"]:
            return 11, "MISSING PREREQUISITE: claude-plan.md - OVERWRITE reviews/ after creating plan"
        # Reviews done - resume at 14 (integrate feedback)
        return 14, "external review complete"

    if files["plan"]:
        # PREREQUISITE CHECK: plan requires spec
        if not files["spec"]:
            return 10, "MISSING PREREQUISITE: claude-spec.md - OVERWRITE claude-plan.md after creating spec"
        # Plan done - resume at 12 (context check before review)
        return 12, "implementation plan complete"

    if files["spec"]:
        # PREREQUISITE CHECK: spec requires interview
        if not files["interview"]:
            return 9, "MISSING PREREQUISITE: claude-interview.md - OVERWRITE claude-spec.md after creating interview"
        # Spec done - resume at 11 (generate plan)
        return 11, "spec complete"

    if files["interview"]:
        # Interview done - resume at 10 (write spec)
        # Note: research is optional, so no prerequisite check here
        return 10, "interview complete"

    if files["research"]:
        # Research done - resume at 8 (interview)
        return 8, "research complete"

    # No files - fresh start at step 6
    return 6, "none"


def build_files_summary(files: dict, section_progress: dict) -> list[str]:
    """Build a list of found files for display."""
    summary = []
    if files["research"]:
        summary.append("claude-research.md")
    if files["interview"]:
        summary.append("claude-interview.md")
    if files["spec"]:
        summary.append("claude-spec.md")
    if files["plan"]:
        summary.append("claude-plan.md")
    if files["integration_notes"]:
        summary.append("claude-integration-notes.md")
    if files["plan_tdd"]:
        summary.append("claude-plan-tdd.md")
    if files["reviews"]:
        summary.append(f"reviews/ ({len(files['reviews'])} files)")
    if files["sections"] or files["sections_index"]:
        progress = section_progress["progress"]
        state = section_progress["state"]
        if state == "complete":
            summary.append(f"sections/ ({progress} complete)")
        elif files["sections_index"]:
            summary.append(f"sections/ ({progress}, {state})")
        else:
            count = len(files['sections'])
            summary.append(f"sections/ ({count} files, no index)")
    return summary


def build_semantic_to_position_map() -> dict[str, int]:
    """Build mapping from semantic task IDs to numeric positions.

    Context tasks: positions 1-4
    Workflow tasks: positions 5-21 (steps 6-22)
    """
    semantic_to_position: dict[str, int] = {}

    # Context tasks are positions 1-4
    for i, ctx_id in enumerate(CONTEXT_TASK_IDS, start=1):
        semantic_to_position[ctx_id] = i

    # Workflow tasks are positions 5-21 (steps 6-22 mapped via TASK_IDS)
    # Step 6 -> position 5, step 7 -> position 6, ..., step 22 -> position 21
    for step_num, task_id in sorted(TASK_IDS.items()):
        position = step_num - 1  # step 6 -> 5, step 22 -> 21
        semantic_to_position[task_id] = position

    return semantic_to_position


def _write_initial_progress(progress_file: Path, spec_file: str, mode: str) -> None:
    """Write initial progress.md with step checklist and error log."""
    content = f"""# Deep-Plan Progress

**Spec:** {spec_file}
**Mode:** {mode}
**Started:** (auto-filled by setup)

## Workflow Steps

- [x] Step 1-5: Environment validation and session setup
- [ ] Step 6: Research decision
- [ ] Step 7: Execute research
- [ ] Step 8: Stakeholder interview
- [ ] Step 9: Save interview transcript
- [ ] Step 10: Write initial spec
- [ ] Step 11: Generate implementation plan
- [ ] Step 12: Context check (pre-review)
- [ ] Step 13: External LLM review
- [ ] Step 14: Integrate external feedback
- [ ] Step 15: User review of integrated plan
- [ ] Step 16: Apply TDD approach
- [ ] Step 17: Context check (pre-section split)
- [ ] Step 18: Create section index
- [ ] Step 19: Generate section tasks
- [ ] Step 20: Write section files
- [ ] Step 21: Final verification
- [ ] Step 22: Output summary

## Errors Encountered

| Step | Error | Attempt | Resolution |
|------|-------|---------|------------|

## Notes

"""
    try:
        progress_file.write_text(content)
    except OSError:
        pass  # Non-critical


def scan_audit_files(planning_dir: Path) -> dict:
    """Scan audit directory for existing files."""
    files = {
        "findings": (planning_dir / "findings.md").exists(),
        "interview": (planning_dir / "interview.md").exists(),
        "current_state": [],
        "gaps": [],
        "architecture": [],
        "specs": [],
        "operations": [],
        "strategy": [],
        "phases": [],
        "build_vs_buy": [],
        "reviews": [],
    }
    for subdir in ["current-state", "gaps", "architecture", "specs",
                    "operations", "strategy", "phases", "build-vs-buy"]:
        d = planning_dir / subdir
        if d.exists():
            key = subdir.replace("-", "_")
            files[key] = [f.name for f in d.glob("*.md")]
    reviews_dir = planning_dir / "reviews"
    if reviews_dir.exists():
        files["reviews"] = [f.name for f in reviews_dir.glob("*.md")]
    return files


def infer_audit_resume_step(files: dict) -> tuple[int | None, str]:
    """Infer which audit step to resume from based on existing files.

    Returns (resume_step, last_completed_description).
    """
    if files["phases"]:
        if files["reviews"]:
            return 12, "external review complete"
        return 11, "phase specs generated"
    if files["build_vs_buy"]:
        return 10, "build-vs-buy analysis complete"
    if files["current_state"] or files["gaps"] or files["architecture"]:
        if files["interview"]:
            return 8, "audit docs partially generated"
        return 7, "auto gaps identified"
    if files["findings"] and (planning_dir := None) is None:
        # Can't check content easily here — check existence only
        if files["interview"]:
            return 8, "interview complete"
        return 6, "findings exist, gaps not yet identified"
    # Fresh start
    return 4, "none"


def _write_audit_progress(progress_file: Path, target: str, mode: str) -> None:
    """Write initial progress.md for audit workflow."""
    content = f"""# Deep-Audit Progress

**Target:** {target}
**Mode:** {mode}
**Started:** (auto-filled by setup)

## Workflow Steps

- [x] Step 1-3: Environment validation and session setup
- [ ] Step 4: Quick scan
- [ ] Step 5: Deep research (parallel subagents)
- [ ] Step 6: Auto gap identification
- [ ] Step 7: Stakeholder interview
- [ ] Step 8: Generate audit documents
- [ ] Step 9: Generate build-vs-buy analysis
- [ ] Step 10: Generate phase specs
- [ ] Step 11: External LLM review
- [ ] Step 12: User review
- [ ] Step 13: Output summary

## Errors Encountered

| Step | Error | Attempt | Resolution |
|------|-------|---------|------------|

## Notes

"""
    try:
        progress_file.write_text(content)
    except OSError:
        pass


def _write_initial_findings(findings_file: Path) -> None:
    """Write empty findings.md accumulator for audit workflow."""
    content = """# Audit Findings

*Running accumulator. Updated after every 2 subagent returns.*
*Last updated: (not yet started)*

## Quick Scan Results

(Populated in step 4)

## Codebase Findings

(Populated in step 5)

## Ecosystem Findings

(Populated in step 5)
"""
    try:
        findings_file.write_text(content)
    except OSError:
        pass


def main():
    parser = argparse.ArgumentParser(description="Setup planning session for deep-plan workflow")
    parser.add_argument(
        "--file",
        required=True,
        help="Path to spec file (planning dir is inferred from parent)"
    )
    parser.add_argument(
        "--plugin-root",
        required=True,
        help="Path to plugin root directory"
    )
    parser.add_argument(
        "--review-mode",
        default="external_llm",
        help="How plan review should be performed: external_llm, opus_subagent, or skip (default: external_llm)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite if CLAUDE_CODE_TASK_LIST_ID has existing tasks"
    )
    parser.add_argument(
        "--session-id",
        help="Session ID from hook's additionalContext (takes precedence over env vars)"
    )
    parser.add_argument(
        "--workflow",
        choices=["plan", "audit"],
        default="plan",
        help="Workflow type: plan (default) or audit"
    )
    args = parser.parse_args()

    # Normalize review_mode: map invalid values to opus_subagent
    # Claude sometimes passes validate-env.sh's review_available value ("none", "full")
    # instead of the resolved review_mode
    VALID_REVIEW_MODES = {"external_llm", "opus_subagent", "skip"}
    if args.review_mode not in VALID_REVIEW_MODES:
        args.review_mode = "opus_subagent"

    file_path = Path(args.file)
    plugin_root = Path(args.plugin_root)

    # Handle relative paths
    if not file_path.is_absolute():
        file_path = Path.cwd() / file_path

    # Validate transcript format if path available (fail fast)
    transcript_path = os.environ.get("CLAUDE_TRANSCRIPT_PATH")
    transcript_validation = None

    if transcript_path:
        validation = validate_transcript_format(transcript_path)

        if not validation.valid:
            result = {
                "success": False,
                "mode": "transcript_format_error",
                "error": "Transcript format validation failed - Claude Code format may have changed",
                "error_details": {
                    "cause": "Our parsing assumptions no longer match the actual transcript format",
                    "transcript_path": validation.transcript_path,
                    "line_count": validation.line_count,
                    "errors": list(validation.errors),
                    "warnings": list(validation.warnings),
                    "troubleshooting": [
                        "Check if Claude Code was updated recently",
                        f"Examine transcript file manually: {transcript_path}",
                        "Compare against expected format in research/claude-code-jsonl-transcripts.md",
                        "Update lib/transcript_validator.py and transcript parsing code"
                    ]
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        transcript_validation = {
            "valid": True,
            "line_count": validation.line_count,
            "user_messages": validation.user_messages,
            "assistant_messages": validation.assistant_messages,
            "warnings": list(validation.warnings) if validation.warnings else []
        }

    is_audit = args.workflow == "audit"

    # For audit workflow, --file can be a directory (the codebase root)
    # For plan workflow, --file must be a .md spec file
    if file_path.is_dir():
        if not is_audit:
            result = {
                "success": False,
                "error": f"Expected a spec file (.md), got a directory: {file_path}. "
                         f"Use /deep-plan @path/to/spec.md or /deep-audit for directory-based workflows.",
                "mode": "error",
            }
            print(json.dumps(result, indent=2))
            return 1
        # Audit mode with directory: planning dir resolution handles subdir creation below
    elif not file_path.exists():
        result = {
            "success": False,
            "error": f"File not found: {file_path}",
            "mode": "error",
        }
        print(json.dumps(result, indent=2))
        return 1
    elif file_path.stat().st_size == 0:
        result = {
            "success": False,
            "error": f"Spec file is empty: {file_path}",
            "mode": "error",
        }
        print(json.dumps(result, indent=2))
        return 1

    # Get task list context from CLI args and environment (needed early for conflict check)
    # --session-id from hook's additionalContext takes precedence over env vars
    context = TaskListContext.from_args_and_env(context_session_id=args.session_id)

    # Resolve planning dir with session isolation
    # Each session gets its own subdirectory to prevent concurrent overwrites
    if file_path.is_dir():
        # Audit mode with directory target: planning files go under <dir>/audit/
        spec_parent = file_path / "audit"
        spec_parent.mkdir(parents=True, exist_ok=True)
    else:
        spec_parent = file_path.parent
    planning_dir = resolve_planning_dir(spec_parent, context.task_list_id)

    # Check for conflict BEFORE doing any work (if CLAUDE_CODE_TASK_LIST_ID is set)
    if context.task_list_id and context.is_user_specified and not args.force:
        conflict = check_for_conflict(context.task_list_id, context.is_user_specified)
        if conflict:
            result = {
                "success": False,
                "mode": "conflict",
                "planning_dir": str(planning_dir),
                "initial_file": str(file_path),
                "plugin_root": str(plugin_root),
                "task_list_id": context.task_list_id,
                "task_list_source": str(context.source),
                "tasks_written": 0,
                "conflict": conflict.to_dict(),
                "message": f"CLAUDE_CODE_TASK_LIST_ID has {conflict.existing_task_count} existing tasks. Use --force to overwrite.",
            }
            print(json.dumps(result, indent=2))
            return 1

    # Create or validate session config
    try:
        session_config, config_created = get_or_create_session_config(
            planning_dir=planning_dir,
            plugin_root=str(plugin_root),
            initial_file=str(file_path),
        )
    except ConfigError as e:
        result = {
            "success": False,
            "error": f"Session config error: {e}",
            "mode": "error",
        }
        print(json.dumps(result, indent=2))
        return 1

    # Handle review_mode: use stored value on resume, CLI arg for new sessions
    if config_created:
        # New session - use CLI arg and store it
        review_mode = args.review_mode
        session_config["review_mode"] = review_mode
        # Store session_id for resume matching
        if context.task_list_id:
            session_config["session_id"] = context.task_list_id
        # Re-save config with review_mode and session_id
        from lib.config import save_session_config
        save_session_config(planning_dir, session_config)
    else:
        # Resume - use stored value if present, otherwise CLI arg
        review_mode = session_config.get("review_mode", args.review_mode)

    # Scan for existing files (audit vs plan have different file sets)
    if is_audit:
        files_found = scan_audit_files(planning_dir)
        resume_step, last_completed = infer_audit_resume_step(files_found)
        files_summary = [
            f for subdir in ["current_state", "gaps", "architecture", "specs",
                             "operations", "strategy", "phases", "build_vs_buy"]
            if files_found.get(subdir)
            for f in [f"{subdir.replace('_', '-')}/ ({len(files_found[subdir])} files)"]
        ]
        if files_found.get("findings"):
            files_summary.insert(0, "findings.md")
        if files_found.get("interview"):
            files_summary.insert(0, "interview.md")
        fresh_step = 4  # Audit starts at step 4
        complete_step = 13  # Audit ends at step 13
        step_names = AUDIT_STEP_NAMES
    else:
        files_found = scan_planning_files(planning_dir)
        section_progress = check_section_progress(planning_dir)
        resume_step, last_completed = infer_resume_step(files_found, section_progress)
        files_summary = build_files_summary(files_found, section_progress)
        fresh_step = 6  # Plan starts at step 6
        complete_step = 22  # Plan ends at step 22
        step_names = STEP_NAMES

    # Determine mode
    if resume_step is None:
        mode = "complete"
    elif resume_step == fresh_step and not files_summary:
        mode = "new"
    else:
        mode = "resume"

    # Build message
    if mode == "resume":
        step_name = step_names.get(resume_step, f"Step {resume_step}")
        message = f"Resuming from step {resume_step} ({step_name}). Last completed: {last_completed}"
    elif mode == "complete":
        message = f"{'Audit' if is_audit else 'Planning'} workflow complete"
    elif not file_path.exists():
        message = f"Starting new session. File will be created: {file_path}"
    else:
        message = f"Starting new {'audit' if is_audit else 'planning'} session in: {planning_dir}"

    # Generate expected tasks for Claude to reconcile
    current_step = resume_step if resume_step is not None else complete_step
    if is_audit:
        expected_tasks = generate_expected_audit_tasks(
            resume_step=current_step,
            plugin_root=str(plugin_root),
            planning_dir=str(planning_dir),
            initial_file=str(file_path),
            review_mode=review_mode,
        )
    else:
        expected_tasks = generate_expected_tasks(
            resume_step=current_step,
            plugin_root=str(plugin_root),
            planning_dir=str(planning_dir),
            initial_file=str(file_path),
            review_mode=review_mode,
        )

    # Check if sections exist FIRST to determine task structure
    # Audit workflow doesn't use sections — skip section task logic
    has_sections = False if is_audit else files_found.get("sections_index", False)
    section_tasks: list[TaskToWrite] = []
    section_deps: dict[str, list[str]] = {}
    section_task_count = 0

    if has_sections:
        # Generate section tasks to know how many there are
        section_tasks, section_deps, section_task_count = generate_section_tasks_to_write(
            planning_dir=planning_dir,
            start_position=SECTION_INSERT_POSITION,  # INSERT at position 19
        )

    # Calculate positions with shifts based on section count
    positions = calculate_task_positions(section_task_count)

    # Build semantic_id -> position mapping for dependency graph
    semantic_to_position = build_semantic_to_position_map()

    # Update semantic_to_position with calculated positions (may be shifted)
    semantic_to_position["final-verification"] = positions["final-verification"]
    semantic_to_position["output-summary"] = positions["output-summary"]
    if section_task_count == 0:
        semantic_to_position["write-sections"] = positions["write-sections"]

    # Build list of tasks to write
    tasks_to_write: list[TaskToWrite] = []

    # Determine if we're actually using section tasks
    # Only use INSERT behavior if we have actual section tasks to insert
    use_section_insert = has_sections and section_task_count > 0

    # Add tasks from expected_tasks up to position 18 (or 21 if no sections)
    # When sections are inserted, we stop at position 18 (generate-section-tasks)
    # When no sections (or empty section tasks), we include all 21 tasks
    stop_position = 18 if use_section_insert else 21

    for position, task in enumerate(expected_tasks, start=1):
        if position <= stop_position:
            # When section tasks are being inserted, position 18 (generate-section-tasks)
            # should be COMPLETED since the script already generated them
            if use_section_insert and position == 18:
                status = TaskStatus.COMPLETED
            else:
                status = TaskStatus(task["status"])
            tasks_to_write.append(
                TaskToWrite(
                    position=position,
                    subject=task["subject"],
                    status=status,
                    description=task.get("description", ""),
                    active_form=task.get("activeForm", ""),
                )
            )

    if use_section_insert and section_tasks:
        # INSERT section tasks at position 19+
        tasks_to_write.extend(section_tasks)

        # Add batch and section positions to semantic mapping
        for task in section_tasks:
            if task.subject.startswith("Run batch "):
                # Extract batch number from subject "Run batch N section subagents"
                batch_num = task.subject.split()[2]
                semantic_to_position[f"batch-{batch_num}"] = task.position
            else:
                # Section task
                semantic_to_position[f"section-{task.position}"] = task.position

        # Add Final Verification at shifted position
        final_ver_pos = positions["final-verification"]
        # Determine status: pending unless all sections complete
        final_ver_status = TaskStatus.PENDING
        tasks_to_write.append(
            TaskToWrite(
                position=final_ver_pos,
                subject="Final Verification",
                status=final_ver_status,
                description="Run check-sections.py to verify all sections complete",
                active_form="Running final verification",
            )
        )

        # Add Output Summary at shifted position
        output_summary_pos = positions["output-summary"]
        tasks_to_write.append(
            TaskToWrite(
                position=output_summary_pos,
                subject="Output Summary",
                status=TaskStatus.PENDING,
                description="Print generated files and next steps",
                active_form="Outputting summary",
            )
        )

        # Build section dependencies for shifted tasks
        shifted_deps = build_section_dependencies(
            section_tasks,
            final_ver_pos,
            output_summary_pos,
        )
        section_deps = {**section_deps, **shifted_deps}

    # Build complete dependency graph
    base_deps = AUDIT_TASK_DEPENDENCIES if is_audit else TASK_DEPENDENCIES
    all_dependencies = {**base_deps, **section_deps}
    dependency_graph = build_dependency_graph(
        tasks_to_write,
        all_dependencies,
        semantic_to_position,
    )

    # Write tasks directly to disk with dependencies
    tasks_written = 0
    task_write_error = None

    # CRITICAL: Must have task_list_id to proceed
    if not context.task_list_id:
        result = {
            "success": False,
            "mode": "no_task_list",
            "planning_dir": str(planning_dir),
            "initial_file": str(file_path),
            "plugin_root": str(plugin_root),
            "error": "No task list ID available. Cannot write tasks.",
            "error_details": {
                "cause": "Neither CLAUDE_CODE_TASK_LIST_ID nor DEEP_SESSION_ID is set.",
                "likely_reason": "The SessionStart hook did not run or failed to capture the session ID.",
                "troubleshooting": [
                    "1. Verify the plugin is loaded: check that /deep-plan skill is available",
                    "2. Check hooks/hooks.json exists in the plugin directory",
                    "3. Try starting a fresh Claude session (the hook runs on session start)",
                ],
            },
        }
        print(json.dumps(result, indent=2))
        return 1

    write_result = write_tasks(
        context.task_list_id,
        tasks_to_write,
        dependency_graph=dependency_graph,
    )
    if write_result.success:
        tasks_written = write_result.tasks_written
    else:
        task_write_error = write_result.error

    # Write active session marker for discipline hooks (PreToolUse, PostToolUse, Stop)
    marker_file = Path.home() / ".claude" / ".deep-plan-active"
    try:
        marker_file.write_text(str(planning_dir))
    except OSError:
        pass  # Non-critical — hooks just won't fire

    # Generate or update progress.md for human-readable step tracking
    progress_file = planning_dir / "progress.md"
    if not progress_file.exists():
        if is_audit:
            _write_audit_progress(progress_file, str(file_path), mode)
            # Also create findings.md accumulator for audit workflow
            findings_file = planning_dir / "findings.md"
            if not findings_file.exists():
                _write_initial_findings(findings_file)
        else:
            _write_initial_progress(progress_file, str(file_path), mode)

    # Build output
    result = {
        "success": True,
        "mode": mode,
        "planning_dir": str(planning_dir),
        "initial_file": str(file_path),
        "plugin_root": str(plugin_root),
        "workflow": args.workflow,
        "review_mode": review_mode,
        "resume_from_step": resume_step,
        "message": message,
        "files_found": files_summary,
        # Task writing results
        "task_list_id": context.task_list_id,
        "task_list_source": str(context.source),
        "session_id_matched": context.session_id_matched,  # True/False/None diagnostic
        "tasks_written": tasks_written,
        # Transcript validation (if available)
        "transcript_validation": transcript_validation,
    }

    # Add error if task writing failed
    if task_write_error:
        result["task_write_error"] = task_write_error

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
