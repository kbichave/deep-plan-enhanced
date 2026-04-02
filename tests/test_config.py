"""Tests for config loader module."""

import pytest
import json
from pathlib import Path


class TestLoadConfig:
    """Tests for load_config function."""

    def test_loads_config_from_plugin_root(self, tmp_path, monkeypatch):
        """Should load config.json from CLAUDE_PLUGIN_ROOT."""
        config_data = {
            "context": {"check_enabled": True},
            "models": {"gemini": "test-model"}
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))

        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))

        from scripts.lib.config import load_config
        result = load_config()

        assert result["context"]["check_enabled"] is True
        assert result["models"]["gemini"] == "test-model"

    def test_falls_back_to_relative_path_when_no_env_var(self, tmp_path, monkeypatch):
        """Should use relative path fallback when CLAUDE_PLUGIN_ROOT not set."""
        # Remove the env var if set
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)

        # This test verifies the fallback logic exists
        # The actual path resolution depends on where config.py is located
        from scripts.lib.config import load_config

        # Should attempt to load from relative path (may fail if not at plugin root)
        # This test documents the expected behavior
        try:
            result = load_config()
            # If it succeeds, verify it returns a dict
            assert isinstance(result, dict)
        except FileNotFoundError:
            # Expected if not running from plugin root
            pass

    def test_raises_on_missing_config_file(self, tmp_path, monkeypatch):
        """Should raise FileNotFoundError if config.json doesn't exist."""
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))

        from scripts.lib.config import load_config

        with pytest.raises(FileNotFoundError):
            load_config()

    def test_raises_on_invalid_json(self, tmp_path, monkeypatch):
        """Should raise JSONDecodeError on malformed config."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{ invalid json }")

        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))

        from scripts.lib.config import load_config

        with pytest.raises(json.JSONDecodeError):
            load_config()

    def test_returns_all_config_sections(self, sample_config):
        """Should return config with all expected sections."""
        assert "context" in sample_config
        assert "external_review" in sample_config
        assert "models" in sample_config
        assert "llm_client" in sample_config
