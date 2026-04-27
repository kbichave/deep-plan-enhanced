"""Tests for per-section context extraction from plan and TDD docs."""

from __future__ import annotations

from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from lib.context_extraction import (
    extract_section_contexts,
    _extract_section_number,
    _extract_keywords,
    _parse_headings,
    _match_headings_for_section,
    _extract_section_summary,
)


@pytest.fixture
def planning_dir(tmp_path):
    """Create a minimal planning directory with plan, TDD, and index.md."""
    sections_dir = tmp_path / "sections"
    sections_dir.mkdir()

    # Create index.md with manifest
    (sections_dir / "index.md").write_text(
        "<!-- PROJECT_CONFIG\n"
        "runtime: python-uv\n"
        "test_command: uv run pytest\n"
        "END_PROJECT_CONFIG -->\n\n"
        "<!-- SECTION_MANIFEST\n"
        "section-01-foundation\n"
        "section-02-config\n"
        "section-03-parser          depends_on:section-01-foundation\n"
        "END_MANIFEST -->\n\n"
        "# Implementation Sections\n\n"
        "### section-01-foundation\n"
        "Project setup, directory structure, initial configuration.\n\n"
        "### section-02-config\n"
        "Configuration loading and validation logic.\n\n"
        "### section-03-parser\n"
        "Input parsing and data transformation.\n"
    )

    # Create claude-plan.md with numbered headings
    (tmp_path / "claude-plan.md").write_text(
        "# Implementation Plan\n\n"
        "## 1. Foundation\n\n"
        "Create the project directory structure.\n"
        "Set up initial files.\n\n"
        "### 1.1 Directory Layout\n\n"
        "Standard Python project layout.\n\n"
        "## 2. Configuration\n\n"
        "Config loading from YAML files.\n"
        "Validation with pydantic.\n\n"
        "## 3. Parser\n\n"
        "Parse input files and transform data.\n"
        "Handle edge cases.\n\n"
        "### 3.1 Input Formats\n\n"
        "Support JSON and YAML.\n\n"
        "## 4. API Layer\n\n"
        "REST endpoints.\n"
    )

    # Create claude-plan-tdd.md
    (tmp_path / "claude-plan-tdd.md").write_text(
        "# TDD Plan\n\n"
        "## 1. Foundation Tests\n\n"
        "- Test: project structure created correctly\n"
        "- Test: initial config exists\n\n"
        "## 2. Configuration Tests\n\n"
        "- Test: load valid YAML\n"
        "- Test: reject invalid config\n\n"
        "## 3. Parser Tests\n\n"
        "- Test: parse JSON input\n"
        "- Test: parse YAML input\n"
    )

    return tmp_path


class TestExtractSectionNumber:
    def test_extracts_single_digit(self):
        assert _extract_section_number("section-03-config") == 3

    def test_extracts_double_digit(self):
        assert _extract_section_number("section-12-integration") == 12

    def test_returns_none_for_invalid(self):
        assert _extract_section_number("not-a-section") is None


class TestExtractKeywords:
    def test_drops_section_prefix_and_number(self):
        kw = _extract_keywords("section-03-config")
        assert "section" not in kw
        assert "03" not in kw

    def test_excludes_short_keywords(self):
        kw = _extract_keywords("section-01-api-setup")
        assert "api" not in kw  # 3 chars, below min_length=4
        assert "setup" in kw

    def test_extracts_multiple_keywords(self):
        kw = _extract_keywords("section-05-prompt-builder")
        assert "prompt" in kw
        assert "builder" in kw


class TestParseHeadings:
    def test_parses_h2_headings(self):
        lines = ["## Foo", "content", "## Bar"]
        headings = _parse_headings(lines)
        assert len(headings) == 2
        assert headings[0] == (0, 2, "Foo")
        assert headings[1] == (2, 2, "Bar")

    def test_parses_h3_headings(self):
        lines = ["### Sub"]
        headings = _parse_headings(lines)
        assert headings[0][1] == 3

    def test_ignores_non_headings(self):
        lines = ["not a heading", "also not"]
        assert _parse_headings(lines) == []


class TestMatchHeadingsForSection:
    def test_tier1_number_match(self):
        lines = ["## 3. Parser", "content", "## 4. API"]
        headings = _parse_headings(lines)
        matched = _match_headings_for_section(headings, lines, "section-03-parser")
        assert 0 in matched

    def test_tier1_matches_subheadings(self):
        lines = ["## 3. Parser", "content", "### 3.1 Input Formats", "## 4. API"]
        headings = _parse_headings(lines)
        matched = _match_headings_for_section(headings, lines, "section-03-parser")
        assert 0 in matched
        assert 2 in matched

    def test_tier2_anchor_match(self):
        lines = [
            "<!-- section: section-02-config -->",
            "## Configuration",
            "content",
        ]
        headings = _parse_headings(lines)
        matched = _match_headings_for_section(headings, lines, "section-02-config")
        assert 1 in matched

    def test_tier3_keyword_fallback(self):
        lines = ["## Project Foundation", "content"]
        headings = _parse_headings(lines)
        matched = _match_headings_for_section(headings, lines, "section-01-foundation")
        assert 0 in matched

    def test_keywords_below_min_length_excluded(self):
        lines = ["## 4. API Layer", "content"]
        headings = _parse_headings(lines)
        # "api" is 3 chars, below min 4 — but tier-1 number match catches it
        matched = _match_headings_for_section(headings, lines, "section-04-api")
        assert 0 in matched

    def test_no_match_returns_empty(self):
        lines = ["## Unrelated Heading"]
        headings = _parse_headings(lines)
        matched = _match_headings_for_section(headings, lines, "section-99-nonexistent")
        assert matched == []


class TestExtractSectionContexts:
    def test_creates_context_files(self, planning_dir):
        sections = ["section-01-foundation", "section-02-config", "section-03-parser"]
        result = extract_section_contexts(planning_dir, sections)
        assert len(result) == 3
        for name, path in result.items():
            assert path.exists()

    def test_context_file_structure(self, planning_dir):
        result = extract_section_contexts(planning_dir, ["section-01-foundation"])
        content = result["section-01-foundation"].read_text()
        assert "# Context for section-01-foundation" in content
        assert "## From claude-plan.md" in content
        assert "## From claude-plan-tdd.md" in content
        assert "## Section Summary (from index.md)" in content

    def test_context_contains_matched_content(self, planning_dir):
        result = extract_section_contexts(planning_dir, ["section-01-foundation"])
        content = result["section-01-foundation"].read_text()
        assert "Directory Layout" in content  # from plan heading 1.1
        assert "project structure created correctly" in content  # from TDD

    def test_context_excludes_unrelated_content(self, planning_dir):
        result = extract_section_contexts(planning_dir, ["section-01-foundation"])
        content = result["section-01-foundation"].read_text()
        assert "REST endpoints" not in content  # from section 4, not section 1

    def test_dependency_inclusion(self, planning_dir):
        result = extract_section_contexts(planning_dir, [
            "section-01-foundation", "section-03-parser",
        ])
        content = result["section-03-parser"].read_text()
        # section-03 depends on section-01, should include section-01 content
        assert "Foundation" in content or "Directory Layout" in content

    def test_context_dir_cleaned_on_rerun(self, planning_dir):
        context_dir = planning_dir / "sections" / ".context"
        context_dir.mkdir(parents=True, exist_ok=True)
        stale = context_dir / "stale-file.md"
        stale.write_text("stale")

        extract_section_contexts(planning_dir, ["section-01-foundation"])
        assert not stale.exists()

    def test_missing_plan_file(self, tmp_path):
        sections_dir = tmp_path / "sections"
        sections_dir.mkdir()
        (sections_dir / "index.md").write_text(
            "<!-- SECTION_MANIFEST\nsection-01-test\nEND_MANIFEST -->\n"
            "### section-01-test\nTest section.\n"
        )
        # No claude-plan.md or claude-plan-tdd.md
        result = extract_section_contexts(tmp_path, ["section-01-test"])
        assert result["section-01-test"].exists()

    def test_context_files_under_size_limit(self, planning_dir):
        result = extract_section_contexts(planning_dir, [
            "section-01-foundation", "section-02-config", "section-03-parser",
        ])
        for name, path in result.items():
            lines = path.read_text().splitlines()
            assert len(lines) < 600, f"{name} has {len(lines)} lines (max 600)"


class TestExtractSectionSummary:
    def test_extracts_summary(self):
        content = "### section-01-foundation\nProject setup and config.\n\n### section-02\nOther."
        summary = _extract_section_summary(content, "section-01-foundation")
        assert "Project setup" in summary

    def test_missing_section_returns_placeholder(self):
        summary = _extract_section_summary("no sections here", "section-99")
        assert "No summary found" in summary
