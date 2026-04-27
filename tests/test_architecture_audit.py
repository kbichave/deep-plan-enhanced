"""Tests for scripts/lib/architecture_audit.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.lib import architecture_audit as aa


def _write(repo: Path, rel: str, body: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_shallow_module_detected(tmp_path):
    _write(
        tmp_path,
        "src/loader.py",
        '''"""Module."""

def load(x):
    return x

def store(x):
    return x

def lookup(x):
    return x
''',
    )
    py_files = aa._collect_py_files(tmp_path, max_files=10)
    candidates = aa.find_shallow_modules(py_files, tmp_path)
    assert len(candidates) == 1
    assert candidates[0].kind == "shallow_module"
    assert "src/loader.py" in candidates[0].files[0]


def test_deep_module_not_flagged(tmp_path):
    body = "\n".join(f"    x{i} = x{i-1} + 1" for i in range(1, 12))
    _write(
        tmp_path,
        "src/processor.py",
        f'''"""Deep enough — small interface, substantial bodies."""

def process(payload):
    x0 = payload
{body}
    return x11

def render(payload):
    x0 = payload
{body}
    return x11
''',
    )
    py_files = aa._collect_py_files(tmp_path, max_files=10)
    candidates = aa.find_shallow_modules(py_files, tmp_path)
    assert candidates == []


def test_hypothetical_seam_with_one_subclass(tmp_path):
    _write(
        tmp_path,
        "src/abstract.py",
        '''from abc import ABC

class Notifier(ABC):
    def send(self, msg): ...
''',
    )
    _write(
        tmp_path,
        "src/email_notifier.py",
        '''from src.abstract import Notifier

class EmailNotifier(Notifier):
    def send(self, msg):
        print(msg)
''',
    )
    py_files = aa._collect_py_files(tmp_path, max_files=10)
    seams = aa.find_hypothetical_seams(py_files, tmp_path)
    assert any("Notifier" in c.description for c in seams)


def test_real_seam_with_two_subclasses_not_flagged(tmp_path):
    _write(tmp_path, "src/abstract.py", "from abc import ABC\n\nclass Notifier(ABC):\n    pass\n")
    _write(tmp_path, "src/a.py", "from src.abstract import Notifier\n\nclass EmailNotifier(Notifier):\n    pass\n")
    _write(tmp_path, "src/b.py", "from src.abstract import Notifier\n\nclass SmsNotifier(Notifier):\n    pass\n")
    py_files = aa._collect_py_files(tmp_path, max_files=10)
    seams = aa.find_hypothetical_seams(py_files, tmp_path)
    assert seams == []


def test_scattered_knowledge_grouped(tmp_path):
    body = "def f():\n    return 1\n"
    _write(tmp_path, "src/order_create.py", body)
    _write(tmp_path, "src/order_validate.py", body)
    _write(tmp_path, "src/order_persist.py", body)
    py_files = aa._collect_py_files(tmp_path, max_files=10)
    scattered = aa.find_scattered_knowledge(py_files, tmp_path)
    assert len(scattered) == 1
    assert scattered[0].kind == "scattered_knowledge"
    assert {Path(f).name for f in scattered[0].files} == {
        "order_create.py",
        "order_validate.py",
        "order_persist.py",
    }


def test_render_audit_markdown_handles_empty_result(tmp_path):
    result = aa.AuditResult()
    body = aa.render_audit_markdown(result)
    assert "Total candidates: **0**" in body
    assert "None detected." in body


def test_run_audit_returns_combined_result(tmp_path):
    _write(tmp_path, "src/loader.py", "def a():\n    return 1\n\ndef b():\n    return 2\n\ndef c():\n    return 3\n")
    result = aa.run_audit(tmp_path)
    assert result.total >= 1
    assert any("loader.py" in c.files[0] for c in result.shallow_modules)
