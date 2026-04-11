#!/usr/bin/env python3
"""Validate research topic coverage for deep-discovery.

Reads research-topics.yaml and checks which topics have non-empty findings files.
Outputs a JSON coverage report for the coverage-validation workflow step.

Usage:
    uv run validate-coverage.py --topics-file YAML --findings-dir DIR

Output (stdout, JSON):
    {
        "coverage_pct": 73.3,
        "total": 15,
        "covered": 11,
        "skipped": 1,
        "missing": ["rt-04", "rt-09"],
        "covered_ids": ["rt-01", "rt-02", ...],
        "topics": [
            {
                "id": "rt-01",
                "topic": "Authentication & Authorization",
                "category": "security",
                "priority": "high",
                "status": "covered",
                "findings_file": "findings/rt-01-auth.md"
            },
            ...
        ]
    }
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load_yaml_simple(content: str) -> dict:
    """Minimal YAML loader for research-topics.yaml.

    Supports the specific schema used by this tool only.
    Uses PyYAML if available, falls back to a restricted hand-parser.
    """
    try:
        import yaml  # type: ignore[import]
        return yaml.safe_load(content)
    except ImportError:
        pass

    # Fallback: use json if the file happens to be valid JSON
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    raise RuntimeError(
        "PyYAML is not installed and the topics file is not valid JSON. "
        "Install PyYAML: pip install pyyaml"
    )


def validate_coverage(topics_file: Path, findings_dir: Path) -> dict:
    """Check which topics have non-empty findings files.

    Args:
        topics_file: Path to research-topics.yaml
        findings_dir: Path to findings/ directory

    Returns:
        Coverage report dict ready for JSON serialisation.
    """
    if not topics_file.exists():
        return {
            "error": f"Topics file not found: {topics_file}",
            "coverage_pct": 0.0,
            "total": 0,
            "covered": 0,
            "skipped": 0,
            "missing": [],
            "covered_ids": [],
            "topics": [],
        }

    content = topics_file.read_text(encoding="utf-8")
    data = _load_yaml_simple(content)
    raw_topics = data.get("topics", [])

    covered: list[str] = []
    skipped: list[str] = []
    missing: list[str] = []
    topic_details: list[dict] = []

    for t in raw_topics:
        tid = t.get("id", "")
        status = t.get("status", "pending")
        findings_rel = t.get("findings_file")

        if status == "skipped":
            skipped.append(tid)
            topic_details.append({
                "id": tid,
                "topic": t.get("topic", ""),
                "category": t.get("category", ""),
                "priority": t.get("priority", ""),
                "status": "skipped",
                "findings_file": findings_rel,
            })
            continue

        # Check if findings file exists and is non-empty
        file_covered = False
        if findings_rel:
            # findings_rel can be relative to planning_dir or to findings_dir
            candidates = [
                findings_dir.parent / findings_rel,
                findings_dir / Path(findings_rel).name,
                Path(findings_rel),
            ]
            for candidate in candidates:
                if candidate.exists() and candidate.stat().st_size > 0:
                    file_covered = True
                    break

        if file_covered or status == "covered":
            covered.append(tid)
            topic_details.append({
                "id": tid,
                "topic": t.get("topic", ""),
                "category": t.get("category", ""),
                "priority": t.get("priority", ""),
                "status": "covered",
                "findings_file": findings_rel,
            })
        else:
            missing.append(tid)
            topic_details.append({
                "id": tid,
                "topic": t.get("topic", ""),
                "category": t.get("category", ""),
                "priority": t.get("priority", ""),
                "status": "missing",
                "findings_file": findings_rel,
                "questions": t.get("questions", []),
            })

    researchable_total = len(raw_topics) - len(skipped)
    coverage_pct = (len(covered) / researchable_total * 100) if researchable_total > 0 else 100.0

    return {
        "coverage_pct": round(coverage_pct, 1),
        "total": len(raw_topics),
        "covered": len(covered),
        "skipped": len(skipped),
        "missing": missing,
        "covered_ids": covered,
        "topics": topic_details,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate research topic coverage for deep-discovery."
    )
    parser.add_argument(
        "--topics-file",
        required=True,
        help="Path to research-topics.yaml",
    )
    parser.add_argument(
        "--findings-dir",
        required=True,
        help="Path to findings/ directory",
    )
    args = parser.parse_args()

    result = validate_coverage(
        topics_file=Path(args.topics_file),
        findings_dir=Path(args.findings_dir),
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
