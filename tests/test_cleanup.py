"""Tests verifying the old task system is fully removed and tasks.py/config.py are clean."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ── tasks.py: kept data, removed functions ──────────────────────────


def test_task_ids_still_exist():
    """TASK_IDS dict must survive cleanup — workflow.py depends on it."""
    from lib.tasks import TASK_IDS
    assert isinstance(TASK_IDS, dict)
    assert 6 in TASK_IDS


def test_task_dependencies_still_exist():
    from lib.tasks import TASK_DEPENDENCIES
    assert isinstance(TASK_DEPENDENCIES, dict)
    assert "research-decision" in TASK_DEPENDENCIES


def test_task_definitions_still_exist():
    from lib.tasks import TASK_DEFINITIONS
    assert isinstance(TASK_DEFINITIONS, dict)
    assert "research-decision" in TASK_DEFINITIONS


def test_audit_task_ids_still_exist():
    from lib.tasks import AUDIT_TASK_IDS
    assert isinstance(AUDIT_TASK_IDS, dict)
    assert 4 in AUDIT_TASK_IDS


def test_generate_expected_tasks_removed():
    """generate_expected_tasks() must be deleted — replaced by workflow.py."""
    from lib import tasks
    assert not hasattr(tasks, "generate_expected_tasks")


def test_generate_expected_audit_tasks_removed():
    from lib import tasks
    assert not hasattr(tasks, "generate_expected_audit_tasks")


def test_create_context_tasks_removed():
    """create_context_tasks() must be deleted — context is deepstate epic metadata."""
    from lib import tasks
    assert not hasattr(tasks, "create_context_tasks")


def test_task_status_removed():
    """TaskStatus enum must be deleted — deepstate uses its own status strings."""
    from lib import tasks
    assert not hasattr(tasks, "TaskStatus")


# ── config.py: legacy rejection ────────────────────────────────────


def test_config_rejects_legacy_configs(tmp_path):
    """A config with task_list_id but no deepstate_epic_id should raise."""
    from lib.config import load_session_config, ConfigError
    config_file = tmp_path / "deep_plan_config.json"
    config_file.write_text(json.dumps({
        "plugin_root": "/fake",
        "planning_dir": str(tmp_path),
        "initial_file": "/fake/spec.md",
        "task_list_id": "old-session-id",
    }))
    with pytest.raises(ConfigError, match="[Ll]egacy"):
        load_session_config(tmp_path)


def test_config_accepts_deepstate_epic_id(tmp_path):
    from lib.config import load_session_config
    config_file = tmp_path / "deep_plan_config.json"
    config_file.write_text(json.dumps({
        "plugin_root": "/fake",
        "planning_dir": str(tmp_path),
        "initial_file": "/fake/spec.md",
        "deepstate_epic_id": "epic-001",
    }))
    config = load_session_config(tmp_path)
    assert config["deepstate_epic_id"] == "epic-001"


# ── deleted modules must not exist ─────────────────────────────────


PLUGIN_ROOT = Path(__file__).parent.parent


def test_task_storage_module_deleted():
    assert not (PLUGIN_ROOT / "scripts" / "lib" / "task_storage.py").exists()


def test_task_reconciliation_module_deleted():
    assert not (PLUGIN_ROOT / "scripts" / "lib" / "task_reconciliation.py").exists()


def test_old_setup_script_deleted():
    assert not (PLUGIN_ROOT / "scripts" / "checks" / "setup-planning-session.py").exists()


def test_old_generate_script_deleted():
    assert not (PLUGIN_ROOT / "scripts" / "checks" / "generate-section-tasks.py").exists()


def test_old_test_files_deleted():
    for name in ["test_task_storage.py", "test_task_reconciliation.py",
                  "test_setup_planning_session.py", "test_generate_section_tasks.py"]:
        assert not (PLUGIN_ROOT / "tests" / name).exists(), f"Should be deleted: {name}"
