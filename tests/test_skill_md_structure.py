"""Tests for SKILL.md structural invariants.

Each rewritten SKILL.md must:
1. Contain the 3 inline guardrails
2. Reference the correct reference files
3. Include the tracker.ready() -> execute -> close loop
4. Stay under 150 lines
5. Preserve frontmatter (name, description)
"""

from __future__ import annotations

import pathlib

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL_PATHS = [
    PLUGIN_ROOT / "skills" / "deep-plan" / "SKILL.md",
    PLUGIN_ROOT / "skills" / "deep-discovery" / "SKILL.md",
    PLUGIN_ROOT / "skills" / "deep-implement" / "SKILL.md",
]

GUARDRAILS = [
    "Always read the reference file for the current step before executing",
    "Never skip a step",
    "Always close the step",
]


@pytest.fixture(params=SKILL_PATHS, ids=lambda p: p.parent.name)
def skill_content(request):
    """Read a SKILL.md and return its text."""
    return request.param.read_text()


def test_each_skill_md_contains_three_inline_guardrails(skill_content):
    """Each SKILL.md must contain the three guardrail phrases."""
    for guardrail in GUARDRAILS:
        assert guardrail in skill_content, f"Missing guardrail: {guardrail}"


def test_each_skill_md_references_correct_reference_files(skill_content):
    """Each SKILL.md must reference files from references/ or sections/."""
    # deep-implement uses sections/ as its reference source
    assert "references/" in skill_content or "sections/" in skill_content


def test_each_skill_md_has_tracker_ready_loop(skill_content):
    """Each SKILL.md must describe the tracker.ready() loop."""
    assert "tracker.ready()" in skill_content


def test_each_skill_md_has_tracker_close(skill_content):
    """Each SKILL.md must reference tracker.close()."""
    assert "tracker.close(" in skill_content


def test_each_skill_md_is_under_150_lines(skill_content):
    """SKILL.md files must be concise routing layers."""
    lines = skill_content.split("\n")
    assert len(lines) <= 150, f"SKILL.md has {len(lines)} lines, max is 150"


def test_frontmatter_preserved(skill_content):
    """YAML frontmatter with name and description must be present."""
    assert skill_content.startswith("---")
    assert "name:" in skill_content
    assert "description:" in skill_content


def test_deep_plan_references_setup_session():
    """deep-plan SKILL.md must reference setup-session.py (new name)."""
    content = (PLUGIN_ROOT / "skills" / "deep-plan" / "SKILL.md").read_text()
    assert "setup-session.py" in content


def test_deep_plan_references_generate_sections():
    """deep-plan SKILL.md must reference generate-sections.py."""
    content = (PLUGIN_ROOT / "skills" / "deep-plan" / "SKILL.md").read_text()
    assert "generate-sections.py" in content


def test_deep_discovery_passes_workflow_audit():
    """deep-discovery SKILL.md must pass --workflow audit."""
    content = (PLUGIN_ROOT / "skills" / "deep-discovery" / "SKILL.md").read_text()
    assert '--workflow "audit"' in content


def test_deep_implement_reads_existing_deepstate():
    """deep-implement should read existing .deepstate/ state."""
    content = (PLUGIN_ROOT / "skills" / "deep-implement" / "SKILL.md").read_text()
    assert ".deepstate" in content


def test_no_skill_references_old_scripts():
    """No SKILL.md should reference the old script names."""
    old_names = ["setup-planning-session.py", "generate-section-tasks.py"]
    for path in SKILL_PATHS:
        content = path.read_text()
        for old_name in old_names:
            assert old_name not in content, (
                f"{path.parent.name}/SKILL.md still references old script: {old_name}"
            )


def test_no_skill_references_position_based_tasks():
    """No SKILL.md should reference TaskList or position-based tracking."""
    for path in SKILL_PATHS:
        content = path.read_text()
        assert "TaskList" not in content, f"{path.parent.name}/SKILL.md references TaskList"
        # deep-implement uses impl-progress.md (implementation tracking, not old workflow progress)
        if "deep-implement" not in str(path):
            assert "progress.md" not in content, f"{path.parent.name}/SKILL.md references progress.md"
