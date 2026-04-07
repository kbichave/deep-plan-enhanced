"""Tests for generate-sections.py script.

Tests section issue creation via DeepStateTracker instead of
position-based task file writes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import importlib.util
_script = Path(__file__).parent.parent / "scripts" / "checks" / "generate-sections.py"
_spec = importlib.util.spec_from_file_location("generate_sections_mod", _script)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

generate_sections = _mod.generate_sections

from lib.deepstate import DeepStateTracker


@pytest.fixture
def planning_dir_with_index(tmp_path):
    """Create a planning dir with valid index.md, deepstate, and generate-section-tasks step."""
    planning_dir = tmp_path / "planning"
    sections_dir = planning_dir / "sections"
    sections_dir.mkdir(parents=True)

    index_content = """<!-- SECTION_MANIFEST
section-01-foundation
section-02-config  depends_on:section-01-foundation
section-03-parser
section-04-ui  depends_on:section-02-config,section-03-parser
END_MANIFEST -->

# Implementation Sections Index
"""
    (sections_dir / "index.md").write_text(index_content)

    # Initialize deepstate with a generate-section-tasks step
    state_dir = planning_dir / ".deepstate"
    tracker = DeepStateTracker(state_dir=state_dir)
    tracker.init("test-epic", {"planning_dir": str(planning_dir)})
    tracker.create("generate-section-tasks", "Generate Section Tasks")

    return planning_dir


@pytest.fixture
def planning_dir_no_index(tmp_path):
    """Planning dir with no sections/index.md."""
    planning_dir = tmp_path / "planning"
    planning_dir.mkdir(parents=True)
    return planning_dir


@pytest.fixture
def planning_dir_no_deepstate(tmp_path):
    """Planning dir with index.md but no .deepstate/."""
    planning_dir = tmp_path / "planning"
    sections_dir = planning_dir / "sections"
    sections_dir.mkdir(parents=True)
    (sections_dir / "index.md").write_text(
        "<!-- SECTION_MANIFEST\nsection-01-alpha\nEND_MANIFEST -->\n"
    )
    return planning_dir


# ── Unit Tests ─────────────────────────────────────────────────────


class TestGenerateSections:
    def test_parses_manifest_with_depends_on(self, planning_dir_with_index):
        result = generate_sections(planning_dir_with_index)
        assert result["success"] is True
        assert "section-02-config" in result["section_map"]

    def test_creates_one_issue_per_section(self, planning_dir_with_index):
        result = generate_sections(planning_dir_with_index)
        assert len(result["section_map"]) == 4

    def test_adds_dependency_edges(self, planning_dir_with_index):
        generate_sections(planning_dir_with_index)
        tracker = DeepStateTracker(state_dir=planning_dir_with_index / ".deepstate")
        config = tracker.show("section-02-config")
        assert "section-01-foundation" in config["depends_on"]

    def test_sections_without_deps_depend_on_generate_step(self, planning_dir_with_index):
        generate_sections(planning_dir_with_index)
        tracker = DeepStateTracker(state_dir=planning_dir_with_index / ".deepstate")
        alpha = tracker.show("section-01-foundation")
        assert "generate-section-tasks" in alpha["depends_on"]

    def test_outputs_json_mapping(self, planning_dir_with_index):
        result = generate_sections(planning_dir_with_index)
        assert isinstance(result["section_map"], dict)
        for key, val in result["section_map"].items():
            assert isinstance(key, str)
            assert isinstance(val, str)

    def test_handles_already_complete_sections(self, planning_dir_with_index):
        """Sections with existing .md files get their issues closed."""
        sections_dir = planning_dir_with_index / "sections"
        (sections_dir / "section-01-foundation.md").write_text("# Done")
        result = generate_sections(planning_dir_with_index)
        assert result["success"] is True
        tracker = DeepStateTracker(state_dir=planning_dir_with_index / ".deepstate")
        issue = tracker.show("section-01-foundation")
        assert issue["status"] == "closed"

    def test_creates_final_verification_and_output_summary(self, planning_dir_with_index):
        generate_sections(planning_dir_with_index)
        tracker = DeepStateTracker(state_dir=planning_dir_with_index / ".deepstate")
        fv = tracker.show("final-verification")
        os = tracker.show("output-summary")
        assert fv is not None
        assert "final-verification" in os["depends_on"]

    def test_returns_complete_when_all_sections_exist(self, planning_dir_with_index):
        sections_dir = planning_dir_with_index / "sections"
        for name in ["section-01-foundation", "section-02-config",
                      "section-03-parser", "section-04-ui"]:
            (sections_dir / f"{name}.md").write_text(f"# {name}")
        result = generate_sections(planning_dir_with_index)
        assert result["success"] is True
        assert result["state"] == "complete"
        assert result["stats"]["missing"] == 0

    def test_returns_error_if_index_missing(self, planning_dir_no_index):
        result = generate_sections(planning_dir_no_index)
        assert result["success"] is False
        assert result["state"] == "fresh"

    def test_returns_error_if_no_deepstate(self, planning_dir_no_deepstate):
        result = generate_sections(planning_dir_no_deepstate)
        assert result["success"] is False
        assert "deepstate" in result["error"].lower() or ".deepstate" in result["error"]

    def test_returns_stats(self, planning_dir_with_index):
        result = generate_sections(planning_dir_with_index)
        assert result["stats"]["total"] == 4
        assert result["stats"]["missing"] == 4
        assert result["stats"]["completed"] == 0

    def test_idempotent_on_second_call(self, planning_dir_with_index):
        """Calling twice should not create duplicate issues."""
        result1 = generate_sections(planning_dir_with_index)
        result2 = generate_sections(planning_dir_with_index)
        assert result1["section_map"] == result2["section_map"]
        tracker = DeepStateTracker(state_dir=planning_dir_with_index / ".deepstate")
        # Count section issues (exclude generate-section-tasks, final-verification, output-summary)
        all_issues = tracker.list_issues()
        section_issues = [i for i in all_issues if i["id"].startswith("section-")]
        assert len(section_issues) == 4
