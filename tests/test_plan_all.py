"""Tests for /deep-plan-all: phasing-overview parsing and workflow creation."""

from __future__ import annotations

from pathlib import Path

import pytest

from lib.deepstate import DeepStateTracker
from lib.workflow import create_plan_all_workflow, parse_phasing_overview
from lib.tasks import TASK_IDS


@pytest.fixture
def phases_dir(tmp_path):
    """Create a phases/ dir with phasing-overview.md and phase spec files."""
    d = tmp_path / "phases"
    d.mkdir()
    (d / "phasing-overview.md").write_text(
        "# Phasing Overview\n\n"
        "## Dependency Graph\n\n"
        "P01 --> P02 --> P04\n"
        "P01 --> P03 --> P04\n"
    )
    (d / "P01-foundation.md").write_text("# P01 Foundation")
    (d / "P02-auth.md").write_text("# P02 Auth")
    (d / "P03-data.md").write_text("# P03 Data Layer")
    (d / "P04-ui.md").write_text("# P04 UI")
    return d


@pytest.fixture
def tracker(tmp_path):
    return DeepStateTracker(state_dir=tmp_path / ".deepstate")


# ── parse_phasing_overview ──────────────────────────────────────────


class TestParsePhaseOverview:
    def test_parses_dependency_graph(self, phases_dir):
        deps = parse_phasing_overview(str(phases_dir))
        assert deps["P01"] == []
        assert "P01" in deps["P02"]
        assert "P01" in deps["P03"]
        assert "P02" in deps["P04"]
        assert "P03" in deps["P04"]

    def test_unicode_arrows(self, tmp_path):
        d = tmp_path / "phases"
        d.mkdir()
        (d / "phasing-overview.md").write_text(
            "# Overview\n\n## Dependency Graph\n\n"
            "P00 ──→ P01 ──→ P03\n"
            "  └──→ P02 ──→ P04\n"
        )
        deps = parse_phasing_overview(str(d))
        assert deps["P00"] == []
        assert "P00" in deps["P01"]

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            parse_phasing_overview(str(tmp_path))

    def test_no_dependency_graph_section_raises(self, tmp_path):
        d = tmp_path / "phases"
        d.mkdir()
        (d / "phasing-overview.md").write_text("# Overview\nNo graph here.")
        with pytest.raises(ValueError, match="Dependency Graph"):
            parse_phasing_overview(str(d))

    def test_single_phase_no_deps(self, tmp_path):
        d = tmp_path / "phases"
        d.mkdir()
        (d / "phasing-overview.md").write_text(
            "# Overview\n\n## Dependency Graph\n\n"
            "P01 --> P02\n"
        )
        deps = parse_phasing_overview(str(d))
        assert deps["P01"] == []
        assert deps["P02"] == ["P01"]


# ── create_plan_all_workflow ────────────────────────────────────────


class TestCreatePlanAllWorkflow:
    def test_creates_phase_issues_and_step_issues(self, tracker, phases_dir):
        create_plan_all_workflow(
            tracker,
            phases_dir=str(phases_dir),
            plugin_root="/fake",
            discovery_findings="/fake/findings",
        )
        all_issues = tracker.list_issues()
        # 4 phase issues + 4 * 17 step issues = 72
        assert len(all_issues) == 72

    def test_inter_phase_deps(self, tracker, phases_dir):
        create_plan_all_workflow(
            tracker,
            phases_dir=str(phases_dir),
            plugin_root="/fake",
            discovery_findings="/fake/findings",
        )
        p02 = tracker.show("phase-P02")
        assert "phase-P01" in p02["depends_on"]
        p04 = tracker.show("phase-P04")
        assert "phase-P02" in p04["depends_on"]
        assert "phase-P03" in p04["depends_on"]

    def test_independent_phases_not_mutually_blocked(self, tracker, phases_dir):
        create_plan_all_workflow(
            tracker,
            phases_dir=str(phases_dir),
            plugin_root="/fake",
            discovery_findings="/fake/findings",
        )
        # P02 and P03 both depend on P01, not on each other
        p02 = tracker.show("phase-P02")
        p03 = tracker.show("phase-P03")
        assert "phase-P03" not in p02["depends_on"]
        assert "phase-P02" not in p03["depends_on"]

    def test_interview_uses_discovery_bridge_for_later_phases(self, tracker, phases_dir):
        create_plan_all_workflow(
            tracker,
            phases_dir=str(phases_dir),
            plugin_root="/fake",
            discovery_findings="/fake/findings",
        )
        # First phase (P01) interview is open with standard description
        p01_interview = tracker.show("P01-detailed-interview")
        assert p01_interview["status"] == "open"
        assert "discovery-bridge.md" not in p01_interview["description"]

        # Later phases have interview open with discovery bridge reference
        p02_interview = tracker.show("P02-detailed-interview")
        assert p02_interview["status"] == "open"
        assert "discovery interview" in p02_interview["description"].lower() or "interview.md" in p02_interview["description"]
        p03_interview = tracker.show("P03-detailed-interview")
        assert p03_interview["status"] == "open"

    def test_lighter_research_for_later_phases(self, tracker, phases_dir):
        create_plan_all_workflow(
            tracker,
            phases_dir=str(phases_dir),
            plugin_root="/fake",
            discovery_findings="/fake/findings",
        )
        # First phase has standard research description
        p01_research = tracker.show("P01-research-decision")
        assert "discovery findings" not in p01_research["description"].lower()

        # Later phases reference discovery findings
        p02_research = tracker.show("P02-research-decision")
        assert "discovery findings" in p02_research["description"].lower()

    def test_returns_epic_title(self, tracker, phases_dir):
        title = create_plan_all_workflow(
            tracker,
            phases_dir=str(phases_dir),
            plugin_root="/fake",
            discovery_findings="/fake/findings",
        )
        assert title.startswith("plan-all:")

    def test_ready_returns_first_phase_steps_only(self, tracker, phases_dir):
        create_plan_all_workflow(
            tracker,
            phases_dir=str(phases_dir),
            plugin_root="/fake",
            discovery_findings="/fake/findings",
        )
        ready = tracker.ready()
        ready_ids = [i["id"] for i in ready]
        # Only P01 phase issue should be ready (no deps)
        assert "phase-P01" in ready_ids
        # P02, P03, P04 should NOT be ready
        assert "phase-P02" not in ready_ids
        assert "phase-P03" not in ready_ids
