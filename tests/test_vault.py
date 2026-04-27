"""Tests for scripts/lib/vault.py."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from scripts.lib import vault


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    """Redirect HOME and clear vault env so each test starts clean."""

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("DEEP_OBSIDIAN_VAULT", raising=False)
    monkeypatch.setattr(vault, "DEFAULT_VAULT", tmp_path / "Obsidian" / "deep-plan")
    monkeypatch.setattr(vault, "GLOBAL_GLOSSARY_DIR", tmp_path / ".claude" / "glossary")
    return tmp_path


def test_resolve_returns_none_when_unconfigured(isolated_home):
    status = vault.resolve_vault_path()
    assert status.path is None
    assert status.source == "none"
    assert status.exists is False
    assert vault.should_prompt_for_creation(status)


def test_resolve_uses_env_when_set(isolated_home, monkeypatch):
    target = isolated_home / "vault-from-env"
    target.mkdir()
    monkeypatch.setenv("DEEP_OBSIDIAN_VAULT", str(target))
    status = vault.resolve_vault_path()
    assert status.source == "env"
    assert status.path == target
    assert status.exists is True
    assert not vault.should_prompt_for_creation(status)


def test_resolve_prefers_default_when_present(isolated_home):
    vault.DEFAULT_VAULT.mkdir(parents=True)
    status = vault.resolve_vault_path()
    assert status.source == "default"
    assert status.exists is True


def test_ensure_skeleton_is_idempotent(isolated_home):
    target = isolated_home / "fresh-vault"
    vault.ensure_vault_skeleton(target)
    expected = [
        target / ".obsidian",
        target / "projects",
        target / "glossary",
        target / "adrs",
        target / "findings",
        target / "README.md",
        target / "_index.md",
    ]
    for path in expected:
        assert path.exists(), path
    # Mutate readme; second call must NOT overwrite it.
    (target / "README.md").write_text("user notes\n", encoding="utf-8")
    vault.ensure_vault_skeleton(target)
    assert (target / "README.md").read_text(encoding="utf-8") == "user notes\n"


def test_slugify_handles_spaces_and_punctuation(isolated_home, tmp_path):
    base = tmp_path / "My Cool Project_42"
    base.mkdir()
    assert vault.slugify_project(base) == "my-cool-project-42"
    pure_punct = tmp_path / "--"
    pure_punct.mkdir()
    assert vault.slugify_project(pure_punct) == "project"


def test_project_dir_creates_per_project_subtree(isolated_home):
    target = isolated_home / "vault"
    vault.ensure_vault_skeleton(target)
    proj = vault.project_dir(target, isolated_home / "demo")
    assert proj.is_dir()
    assert proj.relative_to(target).parts[:1] == ("projects",)


def test_glossary_and_adrs_dirs_share_slug(isolated_home):
    target = isolated_home / "vault"
    vault.ensure_vault_skeleton(target)
    project = isolated_home / "Demo"
    g = vault.glossary_dir(target, project)
    a = vault.adrs_dir(target, project)
    assert g.parent.name == "glossary"
    assert a.parent.name == "adrs"
    assert g.name == a.name == vault.slugify_project(project)
