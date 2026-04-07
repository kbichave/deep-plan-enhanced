"""Tests for reference file enhancements (Section 12)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCES_DIR = REPO_ROOT / "references"


class TestPlanWritingAntiGoals:
    def test_plan_writing_contains_anti_goals_requirement(self):
        content = (REFERENCES_DIR / "plan-writing.md").read_text()
        assert "Anti-Goals" in content
        assert "## Anti-Goals" in content or "### Anti-Goals" in content


class TestCommonRationalizations:
    def test_common_rationalizations_exists_with_table_entries(self):
        path = REFERENCES_DIR / "common-rationalizations.md"
        assert path.exists()
        content = path.read_text()
        assert "|" in content
        assert "---" in content
        table_rows = [
            line for line in content.splitlines()
            if line.strip().startswith("|") and "---" not in line
        ]
        data_rows = table_rows[1:] if table_rows else []
        assert len(data_rows) >= 5, f"Expected at least 5 entries, found {len(data_rows)}"


class TestSectionIndexDependsOnSyntax:
    def test_section_index_documents_depends_on_syntax(self):
        content = (REFERENCES_DIR / "section-index.md").read_text()
        assert "depends_on" in content
        assert "depends_on:" in content
