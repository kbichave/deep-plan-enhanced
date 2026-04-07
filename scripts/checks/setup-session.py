#!/usr/bin/env python3
"""Setup planning session using DeepStateTracker.

Replaces setup-planning-session.py. Uses deepstate for state management
instead of position-based task files.

Usage:
    uv run setup-session.py --file "/path/to/spec.md" --plugin-root "/path/to/plugin"
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.config import (
    ConfigError,
    SESSION_CONFIG_FILENAME,
    get_or_create_session_config,
    save_session_config,
)
from lib.deepstate import DeepStateTracker
from lib.beads_sync import BeadsSyncTracker, detect_beads
from lib.workflow import create_plan_workflow, create_discovery_workflow, create_plan_all_workflow, create_autonomous_workflow


VALID_REVIEW_MODES = {"external_llm", "opus_subagent", "skip"}


def find_existing_session_dir(spec_parent: Path, session_id: str) -> Path | None:
    """Find an existing session directory for this session ID.

    Checks by prefix match first (fast path), then scans all session configs
    for a matching session_id field.
    """
    sessions_dir = spec_parent / "sessions"
    if not sessions_dir.exists():
        return None

    prefix = session_id[:8]
    candidate = sessions_dir / prefix
    if candidate.exists() and (candidate / SESSION_CONFIG_FILENAME).exists():
        return candidate

    for d in sessions_dir.iterdir():
        if not d.is_dir():
            continue
        config_path = d / SESSION_CONFIG_FILENAME
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text())
                if config.get("session_id") == session_id:
                    return d
            except (json.JSONDecodeError, OSError):
                continue
    return None


def resolve_planning_dir(spec_parent: Path, session_id: str | None) -> Path:
    """Resolve the planning directory with session isolation.

    Each session gets its own subdirectory under spec_parent/sessions/<8-char-prefix>/.
    Legacy single-session layouts are detected and used directly.
    """
    legacy_file_markers = [
        "claude-research.md", "claude-plan.md", "claude-spec.md",
        "claude-interview.md", "claude-plan-tdd.md",
        "claude-integration-notes.md", SESSION_CONFIG_FILENAME,
    ]
    legacy_dir_markers = ["reviews", "sections"]
    has_legacy = (
        any((spec_parent / f).exists() for f in legacy_file_markers)
        or any((spec_parent / d).is_dir() for d in legacy_dir_markers)
    )
    if has_legacy:
        return spec_parent

    if not session_id:
        return spec_parent

    existing = find_existing_session_dir(spec_parent, session_id)
    if existing:
        return existing

    prefix = session_id[:8]
    planning_dir = spec_parent / "sessions" / prefix
    planning_dir.mkdir(parents=True, exist_ok=True)
    return planning_dir


def is_legacy_config(config: dict) -> bool:
    """Check if config was created by the old task-based system."""
    return "task_list_id" in config and "deepstate_epic_id" not in config


def determine_mode(tracker: DeepStateTracker) -> tuple[str, dict]:
    """Determine session mode from deepstate.

    Returns (mode, info) where mode is 'new', 'resume', or 'complete'.
    """
    state_file = tracker.state_dir / "state.json"
    if not state_file.exists():
        return "new", {}

    try:
        state = tracker._load()
    except (json.JSONDecodeError, OSError):
        return "new", {}

    if not state.get("epic"):
        return "new", {}

    ready = tracker.ready()
    all_issues = tracker.list_issues()
    closed = [i for i in all_issues if i["status"] == "closed"]
    open_issues = [i for i in all_issues if i["status"] == "open"]

    if not all_issues:
        return "new", {}

    if ready:
        return "resume", {
            "ready_issues": [{"id": i["id"], "title": i["title"]} for i in ready],
            "closed_count": len(closed),
            "open_count": len(open_issues),
        }

    if not open_issues:
        return "complete", {
            "closed_count": len(closed),
        }

    # Open issues exist but none are ready — blocked state
    return "resume", {
        "ready_issues": [],
        "closed_count": len(closed),
        "open_count": len(open_issues),
    }


def check_partial_setup(tracker: DeepStateTracker, expected_count: int | None) -> bool:
    """Return True if deepstate exists but issue count is inconsistent."""
    state_file = tracker.state_dir / "state.json"
    if not state_file.exists():
        return False
    if expected_count is None:
        return False  # Dynamic workflow — can't validate count
    try:
        state = tracker._load()
        if not state.get("epic"):
            return True
        actual_count = len(state.get("issues", {}))
        return actual_count > 0 and actual_count != expected_count
    except (json.JSONDecodeError, OSError):
        return True


def setup_session(
    file_path: Path,
    plugin_root: Path,
    review_mode: str,
    session_id: str | None,
    workflow: str,
    force: bool,
) -> dict:
    """Core setup logic. Returns JSON-serializable result dict."""
    is_audit = workflow == "audit"
    is_plan_all = workflow in ("plan-all", "auto")

    # Input validation
    if file_path.is_dir():
        if not is_audit and not is_plan_all:
            return {
                "success": False,
                "error": f"Expected a spec file (.md), got a directory: {file_path}. "
                         f"Use /deep-plan @path/to/spec.md or /deep-discovery for directory-based workflows.",
                "mode": "error",
            }
    elif not file_path.exists():
        return {"success": False, "error": f"File not found: {file_path}", "mode": "error"}
    elif file_path.stat().st_size == 0:
        return {"success": False, "error": f"Spec file is empty: {file_path}", "mode": "error"}

    # Resolve planning directory
    if is_plan_all and file_path.is_dir():
        # For plan-all/auto, state lives alongside the phases dir — no session nesting
        subdir = "auto" if workflow == "auto" else "plan-all"
        planning_dir = file_path.parent / subdir
        planning_dir.mkdir(parents=True, exist_ok=True)
    elif file_path.is_dir():
        spec_parent = file_path / "audit"
        spec_parent.mkdir(parents=True, exist_ok=True)
        planning_dir = resolve_planning_dir(spec_parent, session_id)
    else:
        spec_parent = file_path.parent
        planning_dir = resolve_planning_dir(spec_parent, session_id)

    # Create or load session config
    try:
        session_config, config_created = get_or_create_session_config(
            planning_dir=planning_dir,
            plugin_root=str(plugin_root),
            initial_file=str(file_path),
        )
    except ConfigError as e:
        if "legacy" in str(e).lower():
            return {
                "success": False,
                "mode": "legacy_config",
                "error": "This session was created with the old task-based system. deepstate requires a fresh session.",
                "migration": "Start a new session with /deep-plan @spec.md. Old planning files are preserved.",
            }
        return {"success": False, "error": f"Session config error: {e}", "mode": "error"}

    # Legacy config detection
    if not config_created and is_legacy_config(session_config):
        return {
            "success": False,
            "mode": "legacy_config",
            "error": "This session was created with the old task-based system. deepstate requires a fresh session.",
            "migration": "Start a new session with /deep-plan @spec.md. Old planning files are preserved.",
        }

    # Handle review_mode
    if config_created:
        session_config["review_mode"] = review_mode
        if session_id:
            session_config["session_id"] = session_id
        save_session_config(planning_dir, session_config)
    else:
        review_mode = session_config.get("review_mode", review_mode)

    # Initialize tracker
    from lib.tasks import TASK_IDS, AUDIT_TASK_IDS
    if is_plan_all:
        expected_count = None  # Dynamic — depends on number of phases
    elif is_audit:
        expected_count = len(AUDIT_TASK_IDS)
    else:
        expected_count = len(TASK_IDS)

    state_dir = planning_dir / ".deepstate"
    base_tracker = DeepStateTracker(state_dir=state_dir)

    # Check for partial setup BEFORE determine_mode (corrupted state can crash ready())
    if check_partial_setup(base_tracker, expected_count):
        if not force:
            return {
                "success": False,
                "mode": "partial_setup",
                "error": "Inconsistent deepstate (partial setup detected). Use --force to reinitialize.",
                "planning_dir": str(planning_dir),
            }
        # Force: tear down and recreate
        if state_dir.exists():
            shutil.rmtree(state_dir)
        base_tracker = DeepStateTracker(state_dir=state_dir)

    # Now safe to determine mode (state is consistent or fresh)
    mode, mode_info = determine_mode(base_tracker)

    if mode == "complete":
        return {
            "success": True,
            "mode": "complete",
            "planning_dir": str(planning_dir),
            "initial_file": str(file_path),
            "plugin_root": str(plugin_root),
            "workflow": workflow,
            "review_mode": review_mode,
            "message": f"{'Audit' if is_audit else 'Planning'} workflow complete",
            **mode_info,
        }

    if mode == "resume":
        return {
            "success": True,
            "mode": "resume",
            "planning_dir": str(planning_dir),
            "initial_file": str(file_path),
            "plugin_root": str(plugin_root),
            "workflow": workflow,
            "review_mode": review_mode,
            "message": f"Resuming session in: {planning_dir}",
            **mode_info,
        }

    # New session — create workflow
    beads_available = detect_beads()
    if beads_available:
        tracker = BeadsSyncTracker(
            tracker=base_tracker,
            beads_available=True,
            beads_cwd=planning_dir,
        )
    else:
        tracker = base_tracker

    context = {
        "plugin_root": str(plugin_root),
        "planning_dir": str(planning_dir),
        "initial_file": str(file_path),
        "review_mode": review_mode,
    }

    if is_audit:
        epic_title = create_discovery_workflow(
            tracker, **context,
        )
    elif workflow == "auto":
        epic_title = create_autonomous_workflow(
            tracker,
            phases_dir=str(file_path),
            plugin_root=str(plugin_root),
            discovery_findings=str(file_path.parent),
        )
    elif is_plan_all:
        epic_title = create_plan_all_workflow(
            tracker,
            phases_dir=str(file_path),
            plugin_root=str(plugin_root),
            discovery_findings=str(file_path.parent),
        )
    else:
        epic_title = create_plan_workflow(
            tracker, **context,
        )

    # Store epic reference in config
    session_config["deepstate_epic_id"] = epic_title
    save_session_config(planning_dir, session_config)

    # Write active session marker
    marker_file = Path.home() / ".claude" / ".deep-plan-active"
    try:
        marker_file.write_text(str(planning_dir))
    except OSError:
        pass

    return {
        "success": True,
        "mode": "new",
        "planning_dir": str(planning_dir),
        "initial_file": str(file_path),
        "plugin_root": str(plugin_root),
        "workflow": workflow,
        "review_mode": review_mode,
        "epic_id": epic_title,
        "beads_available": beads_available,
        "message": f"Starting new {'audit' if is_audit else 'plan-all' if is_plan_all else 'planning'} session in: {planning_dir}",
    }


def main():
    parser = argparse.ArgumentParser(description="Setup planning session")
    parser.add_argument("--file", required=True, help="Path to spec file")
    parser.add_argument("--plugin-root", required=True, help="Path to plugin root directory")
    parser.add_argument(
        "--review-mode", default="external_llm",
        help="Review mode: external_llm, opus_subagent, or skip",
    )
    parser.add_argument("--force", action="store_true", help="Force overwrite of existing state")
    parser.add_argument("--session-id", help="Session ID from hook's additionalContext")
    parser.add_argument(
        "--workflow", choices=["plan", "audit", "plan-all", "auto"], default="plan",
        help="Workflow type: plan (default), audit, plan-all, or auto",
    )
    args = parser.parse_args()

    # Normalize review_mode
    if args.review_mode not in VALID_REVIEW_MODES:
        args.review_mode = "opus_subagent"

    file_path = Path(args.file)
    if not file_path.is_absolute():
        file_path = Path.cwd() / file_path

    try:
        result = setup_session(
            file_path=file_path,
            plugin_root=Path(args.plugin_root),
            review_mode=args.review_mode,
            session_id=args.session_id,
            workflow=args.workflow,
            force=args.force,
        )
    except Exception as e:
        result = {"success": False, "error": str(e), "mode": "error"}

    print(json.dumps(result, indent=2))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
