"""Tests for BeadsSyncTracker -- optional beads write-through sync."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from lib.deepstate import DeepStateTracker
from lib.beads_sync import BeadsSyncTracker, detect_beads


@pytest.fixture
def tracker_with_beads(tmp_path):
    """BeadsSyncTracker with beads_available=True, backed by real DeepStateTracker."""
    state_dir = tmp_path / ".deepstate"
    inner = DeepStateTracker(state_dir=state_dir)
    inner.init("test-epic", {"planning_dir": str(tmp_path)})
    return BeadsSyncTracker(tracker=inner, beads_available=True, beads_cwd=tmp_path)


@pytest.fixture
def tracker_without_beads(tmp_path):
    """BeadsSyncTracker with beads_available=False."""
    state_dir = tmp_path / ".deepstate"
    inner = DeepStateTracker(state_dir=state_dir)
    inner.init("test-epic", {"planning_dir": str(tmp_path)})
    return BeadsSyncTracker(tracker=inner, beads_available=False)


class TestBdRunner:
    def test_bd_calls_subprocess_with_list_args(self, tracker_with_beads, monkeypatch):
        mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout='{}'))
        monkeypatch.setattr(subprocess, "run", mock_run)
        tracker_with_beads._bd("show", "test")
        args = mock_run.call_args
        assert isinstance(args[0][0], list)  # first positional arg is a list
        assert "shell" not in args[1] or args[1].get("shell") is not True

    def test_bd_appends_json_flag(self, tracker_with_beads, monkeypatch):
        mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout='{}'))
        monkeypatch.setattr(subprocess, "run", mock_run)
        tracker_with_beads._bd("show")
        cmd = mock_run.call_args[0][0]
        assert "--json" in cmd

    def test_bd_parses_json_stdout(self, tracker_with_beads, monkeypatch):
        mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout='{"id": "1"}'))
        monkeypatch.setattr(subprocess, "run", mock_run)
        result = tracker_with_beads._bd("show")
        assert result == {"id": "1"}

    def test_bd_returns_none_on_nonzero_exit(self, tracker_with_beads, monkeypatch):
        mock_run = MagicMock(return_value=MagicMock(returncode=1, stderr="fail"))
        monkeypatch.setattr(subprocess, "run", mock_run)
        assert tracker_with_beads._bd("show") is None

    def test_bd_returns_none_on_timeout(self, tracker_with_beads, monkeypatch):
        monkeypatch.setattr(subprocess, "run", MagicMock(side_effect=subprocess.TimeoutExpired("bd", 30)))
        assert tracker_with_beads._bd("show") is None

    def test_bd_returns_none_on_json_decode_error(self, tracker_with_beads, monkeypatch):
        mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout="not json"))
        monkeypatch.setattr(subprocess, "run", mock_run)
        assert tracker_with_beads._bd("show") is None

    def test_bd_returns_none_on_file_not_found(self, tracker_with_beads, monkeypatch):
        monkeypatch.setattr(subprocess, "run", MagicMock(side_effect=FileNotFoundError))
        assert tracker_with_beads._bd("show") is None

    def test_bd_respects_30_second_timeout(self, tracker_with_beads, monkeypatch):
        mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout='{}'))
        monkeypatch.setattr(subprocess, "run", mock_run)
        tracker_with_beads._bd("show")
        assert mock_run.call_args[1]["timeout"] == 30

    def test_bd_passes_cwd(self, tracker_with_beads, monkeypatch):
        mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout='{}'))
        monkeypatch.setattr(subprocess, "run", mock_run)
        tracker_with_beads._bd("show")
        assert mock_run.call_args[1]["cwd"] == tracker_with_beads.beads_cwd

    def test_bd_skipped_when_beads_unavailable(self, tracker_without_beads, monkeypatch):
        mock_run = MagicMock()
        monkeypatch.setattr(subprocess, "run", mock_run)
        result = tracker_without_beads._bd("show")
        assert result is None
        mock_run.assert_not_called()


class TestCreate:
    def test_create_delegates_to_deepstate(self, tracker_with_beads, monkeypatch):
        monkeypatch.setattr(subprocess, "run", MagicMock(return_value=MagicMock(returncode=0, stdout='{}')))
        result = tracker_with_beads.create("s1", "Step 1")
        assert result["id"] == "s1"
        assert result["status"] == "open"

    def test_create_mirrors_to_bd_when_available(self, tracker_with_beads, monkeypatch):
        mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout='{}'))
        monkeypatch.setattr(subprocess, "run", mock_run)
        tracker_with_beads.create("s1", "Step 1")
        assert mock_run.called
        cmd = mock_run.call_args[0][0]
        assert "create" in cmd

    def test_create_succeeds_when_bd_fails(self, tracker_with_beads, monkeypatch):
        monkeypatch.setattr(subprocess, "run", MagicMock(side_effect=subprocess.TimeoutExpired("bd", 30)))
        result = tracker_with_beads.create("s1", "Step 1")
        assert result["id"] == "s1"

    def test_create_skips_bd_when_unavailable(self, tracker_without_beads, monkeypatch):
        mock_run = MagicMock()
        monkeypatch.setattr(subprocess, "run", mock_run)
        result = tracker_without_beads.create("s1", "Step 1")
        assert result["id"] == "s1"
        mock_run.assert_not_called()


class TestReady:
    def test_ready_always_reads_from_deepstate(self, tracker_with_beads, monkeypatch):
        monkeypatch.setattr(subprocess, "run", MagicMock(return_value=MagicMock(returncode=0, stdout='{}')))
        tracker_with_beads.create("s1", "Step 1")
        ready = tracker_with_beads.ready()
        assert len(ready) == 1
        assert ready[0]["id"] == "s1"

    def test_ready_never_calls_bd(self, tracker_with_beads, monkeypatch):
        mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout='{}'))
        monkeypatch.setattr(subprocess, "run", mock_run)
        tracker_with_beads.create("s1", "Step 1")
        mock_run.reset_mock()
        tracker_with_beads.ready()
        mock_run.assert_not_called()


class TestClose:
    def test_close_delegates_to_deepstate(self, tracker_with_beads, monkeypatch):
        monkeypatch.setattr(subprocess, "run", MagicMock(return_value=MagicMock(returncode=0, stdout='{}')))
        tracker_with_beads.create("s1", "Step 1")
        result = tracker_with_beads.close("s1", "done")
        assert result["status"] == "closed"

    def test_close_mirrors_to_bd_when_available(self, tracker_with_beads, monkeypatch):
        mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout='{}'))
        monkeypatch.setattr(subprocess, "run", mock_run)
        tracker_with_beads.create("s1", "Step 1")
        mock_run.reset_mock()
        tracker_with_beads.close("s1", "done")
        assert mock_run.called

    def test_close_succeeds_when_bd_fails(self, tracker_with_beads, monkeypatch):
        # Create succeeds
        monkeypatch.setattr(subprocess, "run", MagicMock(return_value=MagicMock(returncode=0, stdout='{}')))
        tracker_with_beads.create("s1", "Step 1")
        # Close bd fails
        monkeypatch.setattr(subprocess, "run", MagicMock(side_effect=FileNotFoundError))
        result = tracker_with_beads.close("s1", "done")
        assert result["status"] == "closed"


class TestPrime:
    def test_prime_uses_bd_when_available_and_succeeds(self, tracker_with_beads, monkeypatch):
        monkeypatch.setattr(subprocess, "run", MagicMock(return_value=MagicMock(returncode=0, stdout='{}')))
        tracker_with_beads.create("s1", "Step 1")

        def mock_run_prime(cmd, **kwargs):
            return MagicMock(returncode=0, stdout="# Rich beads context")

        monkeypatch.setattr(subprocess, "run", mock_run_prime)
        result = tracker_with_beads.prime()
        assert "Rich beads context" in result

    def test_prime_falls_back_when_bd_fails(self, tracker_with_beads, monkeypatch):
        monkeypatch.setattr(subprocess, "run", MagicMock(return_value=MagicMock(returncode=0, stdout='{}')))
        tracker_with_beads.create("s1", "Step 1")
        monkeypatch.setattr(subprocess, "run", MagicMock(return_value=MagicMock(returncode=1, stdout="")))
        result = tracker_with_beads.prime()
        assert "test-epic" in result  # falls back to deepstate prime

    def test_prime_uses_deepstate_when_beads_unavailable(self, tracker_without_beads):
        tracker_without_beads.create("s1", "Step 1")
        result = tracker_without_beads.prime()
        assert "test-epic" in result


class TestBeadsDetection:
    def test_detects_bd_via_shutil_which(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda x: "/usr/local/bin/bd" if x == "bd" else None)
        from lib.beads_sync import detect_beads
        assert detect_beads() is True

    def test_missing_bd_sets_false(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda x: None)
        from lib.beads_sync import detect_beads
        assert detect_beads() is False
