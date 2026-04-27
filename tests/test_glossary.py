"""Tests for scripts/lib/glossary.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.lib import glossary


@pytest.fixture
def fake_repo(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "models.py").write_text(
        "class CustomerOrder:\n    pass\n\nclass FuelPriceRow:\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "f_orders.sql").write_text(
        "select * from {{ ref('stg_customer_orders') }} where 1=1\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "# Demo\n\n## Pricing Engine\n\nbody\n\n## Customer Orders\n\nbody\n",
        encoding="utf-8",
    )
    return tmp_path


def test_extract_terms_finds_camelcase_and_dbt_refs(fake_repo):
    terms = glossary.extract_terms(fake_repo)
    assert "CustomerOrder" in terms
    assert "FuelPriceRow" in terms
    assert "stg_customer_orders" in terms
    assert "Pricing Engine" in terms


def test_extract_terms_caps_evidence_at_five(fake_repo):
    # Add 8 files referencing the same class
    for i in range(8):
        path = fake_repo / f"helper_{i}.py"
        path.write_text("class CustomerOrder:\n    pass\n", encoding="utf-8")
    terms = glossary.extract_terms(fake_repo)
    assert len(terms["CustomerOrder"].evidence) == 5


def test_diff_merge_adds_new_terms(tmp_path):
    target = tmp_path / "glossary"
    new = {"OrderId": glossary.Term(term="OrderId", definition="Stable order key", evidence=["src/models.py"])}
    report = glossary.diff_merge(target, new)
    assert report.added == ["OrderId"]
    assert (target / "OrderId.md").exists()


def test_diff_merge_preserves_existing_definition(tmp_path):
    target = tmp_path / "glossary"
    initial = {
        "OrderId": glossary.Term(
            term="OrderId",
            definition="Stable order key from PDI POS feed.",
            evidence=["src/models.py"],
        )
    }
    glossary.diff_merge(target, initial)
    incoming = {
        "OrderId": glossary.Term(term="OrderId", definition="", evidence=["src/api.py"])
    }
    report = glossary.diff_merge(target, incoming)
    body = (target / "OrderId.md").read_text(encoding="utf-8")
    assert "Stable order key from PDI POS feed." in body
    assert "src/api.py" in body
    assert report.updated == ["OrderId"]


def test_diff_merge_flags_definition_conflicts(tmp_path):
    target = tmp_path / "glossary"
    glossary.diff_merge(
        target,
        {"OrderId": glossary.Term(term="OrderId", definition="A", evidence=[])},
    )
    report = glossary.diff_merge(
        target,
        {"OrderId": glossary.Term(term="OrderId", definition="B", evidence=[])},
    )
    assert "OrderId" in report.conflicts
    body = (target / "OrderId.md").read_text(encoding="utf-8")
    assert "A" in body  # original preserved
    assert "B" not in body


def test_promote_to_global_copies_first_match(tmp_path):
    project_a = tmp_path / "a"
    project_b = tmp_path / "b"
    glossary.diff_merge(
        project_a,
        {"FuelPriceRow": glossary.Term(term="FuelPriceRow", definition="One row of competitor fuel pricing.")},
    )
    glossary.diff_merge(
        project_b,
        {"FuelPriceRow": glossary.Term(term="FuelPriceRow", definition="One row of competitor fuel pricing.")},
    )
    global_dir = tmp_path / "global"
    dest = glossary.promote_to_global(
        "FuelPriceRow",
        [project_a, project_b],
        global_dir=global_dir,
    )
    assert dest is not None
    assert dest.parent == global_dir
    assert "competitor fuel pricing" in dest.read_text(encoding="utf-8")


def test_promote_returns_none_when_term_missing(tmp_path):
    out = glossary.promote_to_global("Unknown", [tmp_path / "missing"], global_dir=tmp_path / "global")
    assert out is None
