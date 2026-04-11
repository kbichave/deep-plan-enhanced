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
    create_autonomous_workflow,
    _toposort,
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
    def test_creates_12_step_issues(self, tracker, plan_context):
        # 10 original steps + topic-enumeration + coverage-validation = 12
        create_discovery_workflow(tracker, **plan_context)
        issues = tracker.list_issues()
        assert len(issues) == 12

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

    def test_deep_research_depends_on_topic_enumeration(self, tracker, plan_context):
        # deep-research now depends on topic-enumeration, not directly on quick-scan
        create_discovery_workflow(tracker, **plan_context)
        issue = tracker.show("deep-research")
        assert "topic-enumeration" in issue["depends_on"]

    def test_topic_enumeration_depends_on_quick_scan(self, tracker, plan_context):
        create_discovery_workflow(tracker, **plan_context)
        issue = tracker.show("topic-enumeration")
        assert "quick-scan" in issue["depends_on"]

    def test_coverage_validation_depends_on_deep_research(self, tracker, plan_context):
        create_discovery_workflow(tracker, **plan_context)
        issue = tracker.show("coverage-validation")
        assert "deep-research" in issue["depends_on"]

    def test_auto_gaps_depends_on_coverage_validation(self, tracker, plan_context):
        create_discovery_workflow(tracker, **plan_context)
        issue = tracker.show("auto-gaps")
        assert "coverage-validation" in issue["depends_on"]

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


class TestToposort:
    def test_linear_chain(self):
        deps = {"P00": [], "P01": ["P00"], "P02": ["P01"]}
        assert _toposort(deps) == ["P00", "P01", "P02"]

    def test_forward_reference(self):
        """P01 depends on P08 — lower number depends on higher."""
        deps = {"P00": [], "P01": ["P08"], "P08": ["P00"]}
        result = _toposort(deps)
        assert result.index("P00") < result.index("P08")
        assert result.index("P08") < result.index("P01")

    def test_diamond(self):
        deps = {"P00": [], "P01": ["P00"], "P02": ["P00"], "P03": ["P01", "P02"]}
        result = _toposort(deps)
        assert result.index("P00") < result.index("P01")
        assert result.index("P00") < result.index("P02")
        assert result.index("P01") < result.index("P03")
        assert result.index("P02") < result.index("P03")

    def test_deterministic_order_for_independent_phases(self):
        deps = {"P03": [], "P01": [], "P02": []}
        assert _toposort(deps) == ["P01", "P02", "P03"]

    def test_cycle_raises(self):
        deps = {"P00": ["P01"], "P01": ["P00"]}
        with pytest.raises(ValueError, match="Cycle"):
            _toposort(deps)


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

    def test_forward_dependency_succeeds(self, tracker, tmp_path):
        """P01 depends on P08 — must not fail with 'dependency does not exist'."""
        phases_dir = tmp_path / "phases"
        phases_dir.mkdir()
        (phases_dir / "phasing-overview.md").write_text(
            "## Dependency Graph\n\n"
            "P00 ──→ P08 ──→ P01\n"
        )
        create_plan_all_workflow(
            tracker,
            phases_dir=str(phases_dir),
            plugin_root="/fake",
            discovery_findings="/fake",
        )
        p01 = tracker.show("phase-P01")
        assert "phase-P08" in p01["depends_on"]

    def test_autonomous_forward_dependency_succeeds(self, tmp_path):
        """Same forward-dependency bug fix applies to autonomous workflow."""
        tracker = DeepStateTracker(state_dir=tmp_path / ".deepstate")
        phases_dir = tmp_path / "phases"
        phases_dir.mkdir()
        (phases_dir / "phasing-overview.md").write_text(
            "## Dependency Graph\n\n"
            "P00 ──→ P08 ──→ P01\n"
        )
        create_autonomous_workflow(
            tracker,
            phases_dir=str(phases_dir),
            plugin_root="/fake",
            discovery_findings="/fake",
        )
        p01 = tracker.show("phase-P01")
        assert "phase-P08" in p01["depends_on"]
