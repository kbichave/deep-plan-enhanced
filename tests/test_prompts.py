"""Tests for prompt loading utilities."""

import pytest
import json
from pathlib import Path


class TestLoadPrompts:
    """Tests for load_prompts function."""

    def test_loads_system_and_user_prompts(self, sample_prompts_dir):
        """Should load both system and user prompt files."""
        from scripts.lib.prompts import load_prompts

        system, user, schema = load_prompts(sample_prompts_dir)

        assert system == "You are a test system prompt.\n"
        assert "Review this {PROJECT_TYPE} plan:" in user
        assert "{PLAN_CONTENT}" in user

    def test_returns_none_for_missing_response_schema(self, sample_prompts_dir):
        """Should return None for response_schema when response.json missing."""
        from scripts.lib.prompts import load_prompts

        system, user, schema = load_prompts(sample_prompts_dir)

        assert schema is None

    def test_loads_response_schema_when_present(self, tmp_path):
        """Should load and parse response.json when present."""
        from scripts.lib.prompts import load_prompts

        # Create prompts dir with response.json
        system_file = tmp_path / "system"
        system_file.write_text("Test system")
        user_file = tmp_path / "user"
        user_file.write_text("Test user")
        response_file = tmp_path / "response.json"
        response_file.write_text('{"type": "object", "properties": {}}')

        system, user, schema = load_prompts(str(tmp_path))

        assert schema is not None
        assert schema["type"] == "object"
        assert "properties" in schema

    def test_raises_on_missing_system_prompt(self, tmp_path):
        """Should raise FileNotFoundError if system prompt missing."""
        from scripts.lib.prompts import load_prompts

        # Create dir with only user prompt
        user_file = tmp_path / "user"
        user_file.write_text("Test user")

        with pytest.raises(FileNotFoundError):
            load_prompts(str(tmp_path))

    def test_raises_on_missing_user_prompt(self, tmp_path):
        """Should raise FileNotFoundError if user prompt missing."""
        from scripts.lib.prompts import load_prompts

        # Create dir with only system prompt
        system_file = tmp_path / "system"
        system_file.write_text("Test system")

        with pytest.raises(FileNotFoundError):
            load_prompts(str(tmp_path))


class TestFormatPrompt:
    """Tests for format_prompt function."""

    def test_replaces_single_placeholder(self):
        """Should replace {PLACEHOLDER} with value."""
        from scripts.lib.prompts import format_prompt

        result = format_prompt("Hello {NAME}", NAME="World")

        assert result == "Hello World"

    def test_replaces_multiple_placeholders(self):
        """Should replace multiple placeholders."""
        from scripts.lib.prompts import format_prompt

        result = format_prompt("{A} and {B}", A="one", B="two")

        assert result == "one and two"

    def test_raises_on_missing_placeholder_value(self):
        """Should raise KeyError if placeholder value not provided."""
        from scripts.lib.prompts import format_prompt

        with pytest.raises(KeyError):
            format_prompt("{MISSING}", OTHER="value")

    def test_preserves_text_without_placeholders(self):
        """Should return unchanged text when no placeholders."""
        from scripts.lib.prompts import format_prompt

        result = format_prompt("No placeholders here")

        assert result == "No placeholders here"
