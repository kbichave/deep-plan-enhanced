"""Tests for scripts/lib/workflow.py — Workflow Issue Factory."""

from __future__ import annotations

import pytest
from pathlib import Path

from lib.deepstate import DeepStateTracker
from lib.workflow import (
    create_plan_workflow,
    create_discovery_workflow,
    create_section_issues,
    create_plan_all_workflow,
    _REFERENCE_FILES,
    _AUDIT_REFERENCE_FILES,
    _CONTEXT_TASK_IDS,
)
from lib.tasks import (
    TASK_IDS,
    TASK_DEFINITIONS,
    TASK_DEPENDENCIES,
    AUDIT_TASK_IDS,
    AUDIT_TASK_DEFINITIONS,
    AUDIT_TASK_DEPENDENCIES,
)


@pytest.fixture
def tracker(tmp_path):
    """Fresh DeepStateTracker backed by tmp_path."""
    return DeepStateTracker(state_dir=tmp_path / ".deepstate")


@pytest.fixture
def plan_context(tmp_path):
    """Standard context kwargs for create_plan_workflow."""
    return {
        "plugin_root": "/fake/plugin",
        "planning_dir": str(tmp_path / "planning"),
        "initial_file": str(tmp_path / "spec.md"),
        "review_mode": "external_llm",
    }


@pytest.fixture
def sections_dir(tmp_path):
    """Create a sections/index.md with depends_on syntax."""
    planning = tmp_path / "planning"
    sections = planning / "sections"
    sections.mkdir(parents=True)
    index = sections / "index.md"
    index.write_text(
        "<!-- SECTION_MANIFEST\n"
        "section-01-alpha\n"
        "section-02-beta depends_on:section-01-alpha\n"
        "section-03-gamma depends_on:section-01-alpha,section-02-beta\n"
        "END_MANIFEST -->\n\n"
        "```PROJECT_CONFIG\n"
        "runtime: python-uv\n"
        "test_command: uv run pytest\n"
        "```\n"
    )
    return planning


# ── create_plan_workflow ────────────────────────────────────────────


class TestCreatePlanWorkflow:
    def test_creates_17_step_issues(self, tracker, plan_context):
        create_plan_workflow(tracker, **plan_context)
        issues = tracker.list_issues()
        assert len(issues) == 17

    def test_epic_title_contains_spec_name(self, tracker, plan_context):
        title = create_plan_workflow(tracker, **plan_context)
        assert title == "deep-plan: spec"

    def test_stores_context_in_epic(self, tracker, plan_context):
        create_plan_workflow(tracker, **plan_context)
        state = tracker._load()
        ctx = state["epic"]["context"]
        assert ctx["plugin_root"] == plan_context["plugin_root"]
        assert ctx["planning_dir"] == plan_context["planning_dir"]
        assert ctx["initial_file"] == plan_context["initial_file"]
        assert ctx["review_mode"] == plan_context["review_mode"]

    def test_dependency_edges_match_task_dependencies(self, tracker, plan_context):
        create_plan_workflow(tracker, **plan_context)
        for task_id in TASK_IDS.values():
            issue = tracker.show(task_id)
            expected_deps = [
                d for d in TASK_DEPENDENCIES.get(task_id, [])
                if d not in _CONTEXT_TASK_IDS
            ]
            assert issue["depends_on"] == expected_deps, (
                f"{task_id}: expected deps {expected_deps}, got {issue['depends_on']}"
            )

    def test_execute_research_depends_on_research_decision(self, tracker, plan_context):
        create_plan_workflow(tracker, **plan_context)
        issue = tracker.show("execute-research")
        assert "research-decision" in issue["depends_on"]

    def test_descriptions_include_reference_pointer(self, tracker, plan_context):
        create_plan_workflow(tracker, **plan_context)
        for task_id, ref_file in _REFERENCE_FILES.items():
            issue = tracker.show(task_id)
            assert f"**Reference:**" in issue["description"]
            assert ref_file in issue["description"]

    def test_descriptions_include_acceptance_criteria(self, tracker, plan_context):
        create_plan_workflow(tracker, **plan_context)
        issue = tracker.show("research-decision")
        assert "**Acceptance Criteria:**" in issue["description"]

    def test_descriptions_include_resume_here(self, tracker, plan_context):
        create_plan_workflow(tracker, **plan_context)
        issue = tracker.show("research-decision")
        assert "**Resume Here:**" in issue["description"]

    def test_no_context_tasks_created(self, tracker, plan_context):
        create_plan_workflow(tracker, **plan_context)
        for ctx_id in _CONTEXT_TASK_IDS:
            with pytest.raises(KeyError):
                tracker.show(ctx_id)

    def test_all_issues_are_open(self, tracker, plan_context):
        create_plan_workflow(tracker, **plan_context)
        for issue in tracker.list_issues():
            assert issue["status"] == "open"


# ── create_discovery_workflow ───────────────────────────────────────


class TestCreateDiscoveryWorkflow:
    def test_creates_10_step_issues(self, tracker, plan_context):
        create_discovery_workflow(tracker, **plan_context)
        issues = tracker.list_issues()
        assert len(issues) == 10

    def test_epic_title_contains_spec_name(self, tracker, plan_context):
        title = create_discovery_workflow(tracker, **plan_context)
        assert title == "deep-discovery: spec"

    def test_dependency_chain_matches_audit_dependencies(self, tracker, plan_context):
        create_discovery_workflow(tracker, **plan_context)
        for task_id in AUDIT_TASK_IDS.values():
            issue = tracker.show(task_id)
            expected_deps = [
                d for d in AUDIT_TASK_DEPENDENCIES.get(task_id, [])
                if d not in _CONTEXT_TASK_IDS
            ]
            assert issue["depends_on"] == expected_deps

    def test_deep_research_depends_on_quick_scan(self, tracker, plan_context):
        create_discovery_workflow(tracker, **plan_context)
        issue = tracker.show("deep-research")
        assert "quick-scan" in issue["depends_on"]

    def test_descriptions_include_audit_reference_files(self, tracker, plan_context):
        create_discovery_workflow(tracker, **plan_context)
        for task_id, ref_file in _AUDIT_REFERENCE_FILES.items():
            issue = tracker.show(task_id)
            assert ref_file in issue["description"]


# ── create_section_issues ───────────────────────────────────────────


class TestCreateSectionIssues:
    def test_creates_one_issue_per_section_plus_two(self, tracker, sections_dir):
        """3 sections + final-verification + output-summary = 5 issues."""
        tracker.init("test", {"planning_dir": str(sections_dir)})
        # Pre-create the generate-section-tasks step so deps can reference it
        tracker.create("generate-section-tasks", "Generate Section Tasks")
        mapping = create_section_issues(
            tracker, planning_dir=str(sections_dir), plugin_root="/fake"
        )
        # 3 sections + generate-section-tasks (pre-existing) + final-verification + output-summary
        issues = tracker.list_issues()
        assert len(issues) == 6

    def test_returns_section_mapping(self, tracker, sections_dir):
        tracker.init("test", {"planning_dir": str(sections_dir)})
        tracker.create("generate-section-tasks", "Generate Section Tasks")
        mapping = create_section_issues(
            tracker, planning_dir=str(sections_dir), plugin_root="/fake"
        )
        assert "section-01-alpha" in mapping
        assert "section-02-beta" in mapping
        assert "section-03-gamma" in mapping

    def test_dependency_edges_from_depends_on(self, tracker, sections_dir):
        tracker.init("test", {"planning_dir": str(sections_dir)})
        tracker.create("generate-section-tasks", "Generate Section Tasks")
        create_section_issues(
            tracker, planning_dir=str(sections_dir), plugin_root="/fake"
        )
        beta = tracker.show("section-02-beta")
        assert "section-01-alpha" in beta["depends_on"]

    def test_section_without_explicit_deps_depends_on_generate_step(self, tracker, sections_dir):
        tracker.init("test", {"planning_dir": str(sections_dir)})
        tracker.create("generate-section-tasks", "Generate Section Tasks")
        create_section_issues(
            tracker, planning_dir=str(sections_dir), plugin_root="/fake"
        )
        alpha = tracker.show("section-01-alpha")
        assert "generate-section-tasks" in alpha["depends_on"]

    def test_final_verification_blocked_by_all_sections(self, tracker, sections_dir):
        tracker.init("test", {"planning_dir": str(sections_dir)})
        tracker.create("generate-section-tasks", "Generate Section Tasks")
        mapping = create_section_issues(
            tracker, planning_dir=str(sections_dir), plugin_root="/fake"
        )
        fv = tracker.show("final-verification")
        for section_name in mapping:
            assert section_name in fv["depends_on"]

    def test_output_summary_blocked_by_final_verification(self, tracker, sections_dir):
        tracker.init("test", {"planning_dir": str(sections_dir)})
        tracker.create("generate-section-tasks", "Generate Section Tasks")
        create_section_issues(
            tracker, planning_dir=str(sections_dir), plugin_root="/fake"
        )
        os = tracker.show("output-summary")
        assert "final-verification" in os["depends_on"]

    def test_resume_skips_existing_issues(self, tracker, sections_dir):
        """If an issue already exists, create_section_issues skips it."""
        tracker.init("test", {"planning_dir": str(sections_dir)})
        tracker.create("generate-section-tasks", "Generate Section Tasks")
        # First call creates all
        create_section_issues(
            tracker, planning_dir=str(sections_dir), plugin_root="/fake"
        )
        # Close one section
        tracker.close("section-01-alpha", "done")
        # Second call should not re-create it
        mapping = create_section_issues(
            tracker, planning_dir=str(sections_dir), plugin_root="/fake"
        )
        alpha = tracker.show("section-01-alpha")
        assert alpha["status"] == "closed"

    def test_missing_index_raises_file_not_found(self, tracker, tmp_path):
        tracker.init("test", {"planning_dir": str(tmp_path / "nonexistent")})
        with pytest.raises(FileNotFoundError):
            create_section_issues(
                tracker, planning_dir=str(tmp_path / "nonexistent"), plugin_root="/fake"
            )

    def test_gamma_depends_on_both_alpha_and_beta(self, tracker, sections_dir):
        tracker.init("test", {"planning_dir": str(sections_dir)})
        tracker.create("generate-section-tasks", "Generate Section Tasks")
        create_section_issues(
            tracker, planning_dir=str(sections_dir), plugin_root="/fake"
        )
        gamma = tracker.show("section-03-gamma")
        assert "section-01-alpha" in gamma["depends_on"]
        assert "section-02-beta" in gamma["depends_on"]


# ── create_plan_all_workflow ────────────────────────────────────────


class TestCreatePlanAllWorkflow:
    def test_requires_valid_phases_dir(self, tracker):
        """parse_phasing_overview raises FileNotFoundError for missing dir."""
        with pytest.raises(FileNotFoundError):
            create_plan_all_workflow(
                tracker,
                phases_dir="/nonexistent",
                plugin_root="/fake",
                discovery_findings="/fake",
            )
