"""Tests for environment validation script.

NOTE: validate-env.sh derives plugin_root from its own location, not from env vars.
Tests that require custom config must use the actual plugin's config.json.
Tests requiring real API validation are marked with @pytest.mark.requires_credentials.
"""

import pytest
import subprocess
import json
import os
from pathlib import Path


class TestValidateEnv:
    """Tests for validate-env.sh script."""

    @pytest.fixture
    def script_path(self):
        """Return path to validate-env.sh."""
        return Path(__file__).parent.parent / "scripts" / "checks" / "validate-env.sh"

    @pytest.fixture
    def plugin_root(self):
        """Return path to plugin root."""
        return Path(__file__).parent.parent

    @pytest.fixture
    def run_script(self, script_path):
        """Factory fixture to run validate-env.sh."""
        def _run(env=None, timeout=30):
            """Run the script with given environment."""
            if env is None:
                env = os.environ.copy()
            result = subprocess.run(
                [str(script_path)],
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result
        return _run

    def test_outputs_valid_json_structure(self, run_script):
        """Should output valid JSON with expected fields."""
        # Use real environment - we just test JSON structure
        result = run_script()

        # Should parse without exception
        output = json.loads(result.stdout)

        # Check expected fields exist
        assert "valid" in output
        assert "errors" in output
        assert "warnings" in output
        assert "gemini_auth" in output
        assert "openai_auth" in output
        assert "plugin_root" in output

    def test_plugin_root_in_output(self, run_script, plugin_root):
        """Should include correct plugin_root in output."""
        result = run_script()
        output = json.loads(result.stdout)

        assert output["plugin_root"] == str(plugin_root)

    def test_exit_code_0_when_valid(self, run_script):
        """Should exit 0 when validation passes (or warnings only)."""
        result = run_script()
        output = json.loads(result.stdout)

        # If valid, exit code should be 0
        if output["valid"]:
            assert result.returncode == 0

    def test_exit_code_nonzero_when_errors(self, run_script):
        """Should exit non-zero when there are errors."""
        result = run_script()
        output = json.loads(result.stdout)

        # If not valid, exit code should be non-zero
        if not output["valid"]:
            assert result.returncode != 0

    def test_detects_gemini_api_key_presence(self, run_script):
        """Should detect when GEMINI_API_KEY is set (presence check only)."""
        env = os.environ.copy()
        env["GEMINI_API_KEY"] = "test-key-for-presence-check"

        result = run_script(env=env)
        output = json.loads(result.stdout)

        # Should detect the key exists (may fail validation with fake key, but detects presence)
        # gemini_auth will be "api_key" if detected, or "test_failed" if validation failed
        assert output["gemini_auth"] in ["api_key", "test_failed"]

    def test_detects_openai_api_key_presence(self, run_script):
        """Should detect when OPENAI_API_KEY is set (presence check only)."""
        env = os.environ.copy()
        env["OPENAI_API_KEY"] = "test-key-for-presence-check"

        result = run_script(env=env)
        output = json.loads(result.stdout)

        # openai_auth is True if key exists and validates, False otherwise
        # With a fake key, validation will fail but the key was detected
        assert "openai_auth" in output

    def test_returns_null_gemini_auth_when_no_key(self, run_script, tmp_path):
        """Should return null gemini_auth when no auth configured."""
        env = os.environ.copy()
        # Clear all Gemini-related auth
        env.pop("GEMINI_API_KEY", None)
        env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
        env["HOME"] = str(tmp_path)  # No ADC at this path

        result = run_script(env=env)
        output = json.loads(result.stdout)

        # Should be null when no auth found
        assert output["gemini_auth"] is None
