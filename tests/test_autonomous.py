"""Tests for create_autonomous_workflow — fully autonomous plan+implement pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from lib.deepstate import DeepStateTracker
from lib.workflow import create_autonomous_workflow, _HUMAN_INTERACTIVE_STEPS
from lib.tasks import TASK_IDS


@pytest.fixture
def phases_dir(tmp_path):
    d = tmp_path / "phases"
    d.mkdir()
    (d / "phasing-overview.md").write_text(
        "# Phasing Overview\n\n"
        "## Dependency Graph\n\n"
        "P01 --> P02\n"
        "P01 --> P03\n"
    )
    (d / "P01-foundation.md").write_text("# P01")
    (d / "P02-auth.md").write_text("# P02")
    (d / "P03-data.md").write_text("# P03")
    return d


@pytest.fixture
def tracker(tmp_path):
    return DeepStateTracker(state_dir=tmp_path / ".deepstate")


@pytest.fixture
def auto_tracker(tracker, phases_dir):
    create_autonomous_workflow(
        tracker,
        phases_dir=str(phases_dir),
        plugin_root="/fake",
        discovery_findings="/fake/findings",
    )
    return tracker


class TestAutonomousWorkflow:
    def test_epic_title_contains_auto(self, tracker, phases_dir):
        title = create_autonomous_workflow(
            tracker,
            phases_dir=str(phases_dir),
            plugin_root="/fake",
            discovery_findings="/fake",
        )
        assert "auto-plan-implement" in title

    def test_context_has_autonomous_flag(self, auto_tracker):
        state = auto_tracker._load()
        assert state["epic"]["context"]["autonomous"] is True

    def test_review_steps_open_at_creation(self, auto_tracker):
        """User-review and context-check steps should be OPEN at creation.

        They are auto-closed at ready time by the SKILL.md workflow loop,
        NOT pre-closed at creation (which breaks the dependency chain).
        """
        state = auto_tracker._load()
        for phase in ["P01", "P02", "P03"]:
            for step_id in _HUMAN_INTERACTIVE_STEPS:
                namespaced = f"{phase}-{step_id}"
                issue = state["issues"][namespaced]
                assert issue["status"] == "open", (
                    f"{namespaced} should be open (auto-closed at ready time) "
                    f"but is {issue['status']}"
                )

    def test_interview_steps_remain_open(self, auto_tracker):
        """Interview steps should be open — handled by self-interview, not skipped."""
        state = auto_tracker._load()
        for phase in ["P01", "P02", "P03"]:
            for step_id in ("detailed-interview", "save-interview"):
                namespaced = f"{phase}-{step_id}"
                issue = state["issues"][namespaced]
                assert issue["status"] == "open", (
                    f"{namespaced} should be open for self-interview but is {issue['status']}"
                )

    def test_interview_description_says_self_interview(self, auto_tracker):
        """Interview step description should instruct self-interview, not human."""
        issue = auto_tracker.show("P01-detailed-interview")
        assert "SELF-INTERVIEW" in issue["description"]
        assert "Do NOT ask a human" in issue["description"]

    def test_all_steps_open_at_creation(self, auto_tracker):
        """ALL steps should be open at creation (no pre-closing in auto mode)."""
        state = auto_tracker._load()
        for issue_id, issue in state["issues"].items():
            if issue_id.startswith("phase-"):
                continue  # phase gates have no deps and are opened first
            assert issue["status"] == "open", (
                f"{issue_id} should be open at creation but is {issue['status']}"
            )

    def test_ready_returns_first_phase_research(self, auto_tracker):
        """First ready step should be P01's research-decision (after opening phase-P01)."""
        ready_ids = {i["id"] for i in auto_tracker.ready()}
        assert "phase-P01" in ready_ids

    def test_p02_p03_blocked_until_p01_done(self, auto_tracker):
        ready_ids = {i["id"] for i in auto_tracker.ready()}
        assert "phase-P02" not in ready_ids
        assert "phase-P03" not in ready_ids

    def test_walkthrough_interview_then_spec(self, auto_tracker):
        """Walk through P01 — interview is self-interview (open), then write-spec."""
        auto_tracker.close("phase-P01", "Starting P01")

        auto_tracker.close("P01-research-decision", "done")
        auto_tracker.close("P01-execute-research", "done")

        # Interview steps are open (self-interview), not pre-closed
        ready_ids = {i["id"] for i in auto_tracker.ready()}
        assert "P01-detailed-interview" in ready_ids

        auto_tracker.close("P01-detailed-interview", "self-interview done")
        auto_tracker.close("P01-save-interview", "transcript saved")

        ready_ids = {i["id"] for i in auto_tracker.ready()}
        assert "P01-write-spec" in ready_ids

    def test_user_review_ready_after_integrate(self, auto_tracker):
        """After integrate-feedback, user-review should be the ready step.

        In auto mode, the workflow loop auto-closes it, then apply-tdd becomes ready.
        This tests the dependency chain is intact (no skipped steps).
        """
        auto_tracker.close("phase-P01", "go")
        chain = [
            "P01-research-decision", "P01-execute-research",
            "P01-detailed-interview", "P01-save-interview",
            "P01-write-spec", "P01-generate-plan",
            "P01-context-check-pre-review",
            "P01-external-review", "P01-integrate-feedback",
        ]
        for step in chain:
            auto_tracker.close(step, "done")

        # user-review is the next ready step (auto-closed by workflow loop)
        ready_ids = {i["id"] for i in auto_tracker.ready()}
        assert "P01-user-review" in ready_ids

        # After auto-closing user-review, apply-tdd becomes ready
        auto_tracker.close("P01-user-review", "Auto mode: skipped")
        ready_ids = {i["id"] for i in auto_tracker.ready()}
        assert "P01-apply-tdd" in ready_ids
