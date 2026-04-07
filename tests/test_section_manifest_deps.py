"""Tests for enhanced SECTION_MANIFEST parsing with depends_on syntax."""

from __future__ import annotations

import pytest

from lib.sections import parse_manifest_block, parse_manifest_with_deps


class TestParseManifestWithDeps:
    """Tests for the depends_on-aware manifest parser."""

    def test_plain_names_no_depends_on(self):
        content = """<!-- SECTION_MANIFEST
section-01-foundation
section-02-config
section-03-parser
END_MANIFEST -->"""
        result = parse_manifest_with_deps(content)
        assert result["success"]
        assert result["sections"] == [
            "section-01-foundation",
            "section-02-config",
            "section-03-parser",
        ]
        assert result["dependencies"] == {
            "section-01-foundation": [],
            "section-02-config": [],
            "section-03-parser": [],
        }

    def test_single_dependency(self):
        content = """<!-- SECTION_MANIFEST
section-01-foundation
section-02-config  depends_on:section-01-foundation
END_MANIFEST -->"""
        result = parse_manifest_with_deps(content)
        assert result["success"]
        assert result["dependencies"]["section-02-config"] == ["section-01-foundation"]

    def test_multiple_dependencies(self):
        content = """<!-- SECTION_MANIFEST
section-01-foundation
section-02-config
section-03-parser  depends_on:section-01-foundation,section-02-config
END_MANIFEST -->"""
        result = parse_manifest_with_deps(content)
        assert result["success"]
        assert set(result["dependencies"]["section-03-parser"]) == {
            "section-01-foundation",
            "section-02-config",
        }

    def test_blank_lines_and_whitespace_ignored(self):
        content = """<!-- SECTION_MANIFEST

section-01-foundation

section-02-config    depends_on:section-01-foundation

END_MANIFEST -->"""
        result = parse_manifest_with_deps(content)
        assert result["success"]
        assert len(result["sections"]) == 2

    def test_returns_dict_with_name_to_deps_mapping(self):
        content = """<!-- SECTION_MANIFEST
section-01-a
section-02-b  depends_on:section-01-a
END_MANIFEST -->"""
        result = parse_manifest_with_deps(content)
        assert isinstance(result["dependencies"], dict)
        assert "section-01-a" in result["dependencies"]
        assert "section-02-b" in result["dependencies"]

    def test_invalid_depends_on_target_raises_error(self):
        content = """<!-- SECTION_MANIFEST
section-01-foundation
section-02-config  depends_on:section-99-nonexistent
END_MANIFEST -->"""
        result = parse_manifest_with_deps(content)
        assert not result["success"]
        assert "section-99-nonexistent" in result["error"]

    def test_self_dependency_raises_error(self):
        content = """<!-- SECTION_MANIFEST
section-01-foundation  depends_on:section-01-foundation
END_MANIFEST -->"""
        result = parse_manifest_with_deps(content)
        assert not result["success"]
        assert "self" in result["error"].lower() or "section-01-foundation" in result["error"]

    def test_backward_compatible_with_existing_parse_manifest_block(self):
        content = """<!-- SECTION_MANIFEST
section-01-foundation
section-02-config  depends_on:section-01-foundation
END_MANIFEST -->"""
        result = parse_manifest_block(content)
        assert result["success"]
        assert result["sections"] == ["section-01-foundation", "section-02-config"]

    def test_mixed_with_and_without_deps(self):
        content = """<!-- SECTION_MANIFEST
section-01-a
section-02-b
section-03-c  depends_on:section-01-a
section-04-d  depends_on:section-02-b,section-03-c
END_MANIFEST -->"""
        result = parse_manifest_with_deps(content)
        assert result["success"]
        assert result["dependencies"]["section-01-a"] == []
        assert result["dependencies"]["section-02-b"] == []
        assert result["dependencies"]["section-03-c"] == ["section-01-a"]
        assert set(result["dependencies"]["section-04-d"]) == {"section-02-b", "section-03-c"}

    def test_sections_list_preserves_order(self):
        content = """<!-- SECTION_MANIFEST
section-03-c
section-01-a  depends_on:section-03-c
section-02-b
END_MANIFEST -->"""
        result = parse_manifest_with_deps(content)
        assert result["success"]
        assert result["sections"] == ["section-01-a", "section-02-b", "section-03-c"]
