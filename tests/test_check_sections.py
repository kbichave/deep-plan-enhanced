"""Tests for check-sections.py script."""

import pytest
import subprocess
import json
import os
from pathlib import Path


class TestCheckSections:
    """Tests for check-sections.py script."""

    @pytest.fixture
    def script_path(self):
        """Return path to check-sections.py."""
        return Path(__file__).parent.parent / "scripts" / "checks" / "check-sections.py"

    @pytest.fixture
    def plugin_root(self):
        """Return path to plugin root."""
        return Path(__file__).parent.parent

    @pytest.fixture
    def run_script(self, script_path, plugin_root):
        """Factory fixture to run check-sections.py."""
        def _run(planning_dir: Path, timeout=10):
            """Run the script with given planning directory."""
            env = os.environ.copy()
            env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)

            result = subprocess.run(
                ["uv", "run", str(script_path), "--planning-dir", str(planning_dir)],
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result
        return _run

    @pytest.fixture
    def sample_index_content(self):
        """Sample index.md content with SECTION_MANIFEST block."""
        return """<!-- SECTION_MANIFEST
section-01-setup
section-02-api
section-03-database
section-04-integration
END_MANIFEST -->

# Implementation Sections Index

## Dependency Graph

| Section | Depends On | Blocks | Parallelizable |
|---------|------------|--------|----------------|
| section-01-setup | - | section-02, section-03 | Yes |
| section-02-api | section-01 | section-04 | No |
| section-03-database | section-01 | section-04 | No |
| section-04-integration | section-02, section-03 | - | No |

## Execution Order

1. section-01-setup (no dependencies)
2. section-02-api, section-03-database (parallel after section-01)
3. section-04-integration (requires section-02 AND section-03)

## Section Summaries

### section-01-setup
Initial project setup and configuration.

### section-02-api
API endpoint implementation.

### section-03-database
Database schema and migrations.

### section-04-integration
Integration and final wiring.
"""

    def test_fresh_state_no_sections_dir(self, run_script, tmp_path):
        """Should return 'fresh' when no sections directory exists."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()

        result = run_script(planning_dir)

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["state"] == "fresh"
        assert output["index_exists"] is False
        assert output["defined_sections"] == []
        assert output["completed_sections"] == []
        assert output["missing_sections"] == []
        assert output["next_section"] is None
        assert output["progress"] == "0/0"

    def test_fresh_state_empty_sections_dir(self, run_script, tmp_path):
        """Should return 'fresh' when sections directory is empty."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        sections_dir = planning_dir / "sections"
        sections_dir.mkdir()

        result = run_script(planning_dir)

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["state"] == "fresh"
        assert output["index_exists"] is False

    def test_has_index_state(self, run_script, tmp_path, sample_index_content):
        """Should return 'has_index' when index.md exists but no section files."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        sections_dir = planning_dir / "sections"
        sections_dir.mkdir()

        index_file = sections_dir / "index.md"
        index_file.write_text(sample_index_content)

        result = run_script(planning_dir)

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["state"] == "has_index"
        assert output["index_exists"] is True
        assert len(output["defined_sections"]) == 4
        assert "section-01-setup" in output["defined_sections"]
        assert "section-02-api" in output["defined_sections"]
        assert "section-03-database" in output["defined_sections"]
        assert "section-04-integration" in output["defined_sections"]
        assert output["completed_sections"] == []
        assert output["next_section"] == "section-01-setup"
        assert output["progress"] == "0/4"

    def test_partial_state(self, run_script, tmp_path, sample_index_content):
        """Should return 'partial' when some section files exist."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        sections_dir = planning_dir / "sections"
        sections_dir.mkdir()

        index_file = sections_dir / "index.md"
        index_file.write_text(sample_index_content)

        # Create first two section files
        (sections_dir / "section-01-setup.md").write_text("# Section 1")
        (sections_dir / "section-02-api.md").write_text("# Section 2")

        result = run_script(planning_dir)

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["state"] == "partial"
        assert output["index_exists"] is True
        assert len(output["completed_sections"]) == 2
        assert "section-01-setup" in output["completed_sections"]
        assert "section-02-api" in output["completed_sections"]
        assert len(output["missing_sections"]) == 2
        assert "section-03-database" in output["missing_sections"]
        assert "section-04-integration" in output["missing_sections"]
        assert output["next_section"] == "section-03-database"
        assert output["progress"] == "2/4"

    def test_complete_state(self, run_script, tmp_path, sample_index_content):
        """Should return 'complete' when all section files exist."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        sections_dir = planning_dir / "sections"
        sections_dir.mkdir()

        index_file = sections_dir / "index.md"
        index_file.write_text(sample_index_content)

        # Create all section files
        (sections_dir / "section-01-setup.md").write_text("# Section 1")
        (sections_dir / "section-02-api.md").write_text("# Section 2")
        (sections_dir / "section-03-database.md").write_text("# Section 3")
        (sections_dir / "section-04-integration.md").write_text("# Section 4")

        result = run_script(planning_dir)

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["state"] == "complete"
        assert output["index_exists"] is True
        assert len(output["completed_sections"]) == 4
        assert output["missing_sections"] == []
        assert output["next_section"] is None
        assert output["progress"] == "4/4"

    def test_sections_sorted_by_number(self, run_script, tmp_path):
        """Should sort sections by number, not alphabetically."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        sections_dir = planning_dir / "sections"
        sections_dir.mkdir()

        # Index with sections that would sort differently alphabetically vs numerically
        index_content = """<!-- SECTION_MANIFEST
section-01-aaa
section-02-zzz
section-10-bbb
section-03-ccc
END_MANIFEST -->

# Index
"""
        index_file = sections_dir / "index.md"
        index_file.write_text(index_content)

        result = run_script(planning_dir)

        assert result.returncode == 0
        output = json.loads(result.stdout)
        # Should be sorted by number: 01, 02, 03, 10 (not 01, 02, 10, 03 alphabetically)
        assert output["defined_sections"] == [
            "section-01-aaa",
            "section-02-zzz",
            "section-03-ccc",
            "section-10-bbb",
        ]

    def test_invalid_index_without_manifest(self, run_script, tmp_path):
        """Should return 'invalid_index' when index.md lacks SECTION_MANIFEST block."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        sections_dir = planning_dir / "sections"
        sections_dir.mkdir()

        # Old-style index without manifest block
        index_content = """# Index

| Section | Depends On |
|---------|------------|
| section-01 | - |
| section-02 | section-01 |
"""
        index_file = sections_dir / "index.md"
        index_file.write_text(index_content)

        result = run_script(planning_dir)

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["state"] == "invalid_index"
        assert output["defined_sections"] == []
        assert output["index_format"]["has_manifest"] is False
        assert output["index_format"]["manifest_valid"] is False
        assert "SECTION_MANIFEST" in output["index_format"]["error"]

    # --- SECTION_MANIFEST block tests ---

    def test_manifest_block_parsing(self, run_script, tmp_path):
        """Should parse sections from SECTION_MANIFEST block."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        sections_dir = planning_dir / "sections"
        sections_dir.mkdir()

        index_content = """<!-- SECTION_MANIFEST
section-01-foundation
section-02-config
section-03-parser
END_MANIFEST -->

# Implementation Sections Index

Some human-readable content here.
"""
        (sections_dir / "index.md").write_text(index_content)

        result = run_script(planning_dir)

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["state"] == "has_index"
        assert output["defined_sections"] == [
            "section-01-foundation",
            "section-02-config",
            "section-03-parser",
        ]
        assert output["index_format"]["has_manifest"] is True
        assert output["index_format"]["manifest_valid"] is True
        assert output["index_format"]["warnings"] == []

    def test_manifest_block_with_empty_lines(self, run_script, tmp_path):
        """Should handle empty lines in SECTION_MANIFEST block."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        sections_dir = planning_dir / "sections"
        sections_dir.mkdir()

        index_content = """<!-- SECTION_MANIFEST

section-01-setup

section-02-api

END_MANIFEST -->
"""
        (sections_dir / "index.md").write_text(index_content)

        result = run_script(planning_dir)

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["defined_sections"] == ["section-01-setup", "section-02-api"]
        assert output["index_format"]["manifest_valid"] is True

    def test_manifest_block_missing_end_marker(self, run_script, tmp_path):
        """Should report error when END_MANIFEST is missing."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        sections_dir = planning_dir / "sections"
        sections_dir.mkdir()

        index_content = """<!-- SECTION_MANIFEST
section-01-setup
section-02-api

# Forgot to close the manifest block
"""
        (sections_dir / "index.md").write_text(index_content)

        result = run_script(planning_dir)

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["state"] == "invalid_index"
        assert output["index_format"]["has_manifest"] is True
        assert output["index_format"]["manifest_valid"] is False
        assert "not closed" in output["index_format"]["error"]

    def test_manifest_block_invalid_section_name(self, run_script, tmp_path):
        """Should report error for invalid section name format."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        sections_dir = planning_dir / "sections"
        sections_dir.mkdir()

        index_content = """<!-- SECTION_MANIFEST
section-01-foundation
invalid-section-name
section-03-parser
END_MANIFEST -->
"""
        (sections_dir / "index.md").write_text(index_content)

        result = run_script(planning_dir)

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["state"] == "invalid_index"
        assert output["index_format"]["manifest_valid"] is False
        assert "Invalid section name" in output["index_format"]["error"]
        assert "invalid-section-name" in output["index_format"]["error"]

    def test_manifest_block_duplicate_section_number(self, run_script, tmp_path):
        """Should report error for duplicate section numbers."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        sections_dir = planning_dir / "sections"
        sections_dir.mkdir()

        index_content = """<!-- SECTION_MANIFEST
section-01-foundation
section-02-config
section-02-duplicate
END_MANIFEST -->
"""
        (sections_dir / "index.md").write_text(index_content)

        result = run_script(planning_dir)

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["state"] == "invalid_index"
        assert output["index_format"]["manifest_valid"] is False
        assert "Duplicate section number" in output["index_format"]["error"]

    def test_manifest_block_gap_warning(self, run_script, tmp_path):
        """Should warn about gaps in section numbering."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        sections_dir = planning_dir / "sections"
        sections_dir.mkdir()

        index_content = """<!-- SECTION_MANIFEST
section-01-foundation
section-03-parser
section-05-api
END_MANIFEST -->
"""
        (sections_dir / "index.md").write_text(index_content)

        result = run_script(planning_dir)

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["index_format"]["manifest_valid"] is True
        assert len(output["index_format"]["warnings"]) >= 2
        assert any("gap" in w.lower() for w in output["index_format"]["warnings"])

    def test_manifest_block_empty(self, run_script, tmp_path):
        """Should report error when SECTION_MANIFEST block is empty."""
        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        sections_dir = planning_dir / "sections"
        sections_dir.mkdir()

        index_content = """<!-- SECTION_MANIFEST
END_MANIFEST -->

# Index with empty manifest
"""
        (sections_dir / "index.md").write_text(index_content)

        result = run_script(planning_dir)

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["state"] == "invalid_index"
        assert output["index_format"]["manifest_valid"] is False
        assert "empty" in output["index_format"]["error"].lower()
