"""Per-section context extraction from full plan and TDD documents.

Reduces section-writer token consumption by 80-90% by extracting only the
heading blocks relevant to each section, instead of passing the full plan.
"""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path

from lib.sections import parse_manifest_with_deps

logger = logging.getLogger(__name__)


def extract_section_contexts(
    planning_dir: Path,
    sections: list[str],
) -> dict[str, Path]:
    """Extract per-section context files from the full plan and TDD docs.

    Reads claude-plan.md and claude-plan-tdd.md, matches content to each
    section using heading-based keyword extraction, and writes focused
    context files to sections/.context/.

    Args:
        planning_dir: Root planning directory containing claude-plan.md,
                      claude-plan-tdd.md, and sections/index.md.
        sections: Ordered list of section names from the manifest.

    Returns:
        Mapping of section name to the Path of its written context file.
        Missing plans or TDD files result in partial context (not an error).
    """
    context_dir = planning_dir / "sections" / ".context"

    # Step 0: clean slate
    if context_dir.exists():
        shutil.rmtree(context_dir, ignore_errors=True)
    context_dir.mkdir(parents=True, exist_ok=True)

    # Load plan and TDD files
    plan_path = planning_dir / "claude-plan.md"
    tdd_path = planning_dir / "claude-plan-tdd.md"

    plan_lines = plan_path.read_text().splitlines() if plan_path.exists() else []
    tdd_lines = tdd_path.read_text().splitlines() if tdd_path.exists() else []

    # Parse headings from both files
    plan_headings = _parse_headings(plan_lines)
    tdd_headings = _parse_headings(tdd_lines)

    # Parse dependencies from index.md
    index_path = planning_dir / "sections" / "index.md"
    deps_map: dict[str, list[str]] = {}
    index_content = ""
    if index_path.exists():
        index_content = index_path.read_text()
        result = parse_manifest_with_deps(index_content)
        if result["success"]:
            deps_map = result["dependencies"]

    context_map: dict[str, Path] = {}

    for section_name in sections:
        # Match headings for this section
        matched_plan_indices = _match_headings_for_section(
            plan_headings, plan_lines, section_name,
        )
        matched_tdd_indices = _match_headings_for_section(
            tdd_headings, tdd_lines, section_name,
        )

        # Step 3b: include dependency section headings
        for dep_name in deps_map.get(section_name, []):
            dep_plan = _match_headings_for_section(
                plan_headings, plan_lines, dep_name,
            )
            dep_tdd = _match_headings_for_section(
                tdd_headings, tdd_lines, dep_name,
            )
            matched_plan_indices = sorted(set(matched_plan_indices) | set(dep_plan))
            matched_tdd_indices = sorted(set(matched_tdd_indices) | set(dep_tdd))

        # Extract blocks
        plan_blocks = _extract_blocks(plan_lines, plan_headings, matched_plan_indices)
        tdd_blocks = _extract_blocks(tdd_lines, tdd_headings, matched_tdd_indices)

        # Fallback for zero matches
        if not plan_blocks and not tdd_blocks:
            logger.warning(
                "No heading matches for section '%s' — using fallback context",
                section_name,
            )
            plan_blocks = plan_lines[:100]
            tdd_blocks = tdd_lines[:400]

        # Cap fallback total
        total = len(plan_blocks) + len(tdd_blocks)
        if total > 500 and not matched_plan_indices and not matched_tdd_indices:
            tdd_blocks = tdd_blocks[: max(0, 500 - len(plan_blocks))]

        # Extract section summary from index.md
        summary = _extract_section_summary(index_content, section_name)

        # Assemble context file
        lines_out: list[str] = []
        lines_out.append(f"# Context for {section_name}")
        lines_out.append("")
        lines_out.append("## From claude-plan.md")
        lines_out.append("")
        lines_out.extend(plan_blocks)
        lines_out.append("")
        lines_out.append("## From claude-plan-tdd.md")
        lines_out.append("")
        lines_out.extend(tdd_blocks)
        lines_out.append("")
        lines_out.append("## Section Summary (from index.md)")
        lines_out.append("")
        lines_out.append(summary)

        context_file = context_dir / f"{section_name}.md"
        context_file.write_text("\n".join(lines_out))
        context_map[section_name] = context_file

    return context_map


def _extract_section_number(section_name: str) -> int | None:
    """Extract numeric portion from section name like 'section-03-config' -> 3."""
    match = re.match(r"section-(\d+)", section_name)
    if match:
        return int(match.group(1))
    return None


def _extract_keywords(section_name: str, min_length: int = 4) -> list[str]:
    """Extract matching keywords from section name, dropping number prefix and short words."""
    parts = section_name.split("-")
    # Drop "section" and the number prefix (e.g., "01", "02")
    keywords = []
    skip_next_number = False
    for part in parts:
        if part == "section":
            continue
        if re.match(r"^\d+$", part):
            continue
        if len(part) >= min_length:
            keywords.append(part.lower())
    return keywords


def _parse_headings(lines: list[str]) -> list[tuple[int, int, str]]:
    """Parse all markdown headings from lines.

    Returns:
        List of (line_index, level, text) where level is the heading depth
        (2 for ##, 3 for ###, etc.).
    """
    headings = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            match = re.match(r"^(#{1,6})\s+(.*)", stripped)
            if match:
                level = len(match.group(1))
                text = match.group(2).strip()
                headings.append((i, level, text))
    return headings


def _match_headings_for_section(
    headings: list[tuple[int, int, str]],
    lines: list[str],
    section_name: str,
) -> list[int]:
    """Return line indices of headings matching a section via three-tier strategy."""
    matched: set[int] = set()

    section_num = _extract_section_number(section_name)
    keywords = _extract_keywords(section_name)

    # Tier 1: number match
    if section_num is not None:
        num_str = str(section_num)
        for line_idx, level, text in headings:
            # Match headings starting with the section number
            # e.g., "3. Configuration" or "3.1 Config Loader"
            if re.match(rf"^{num_str}[\.\s]", text):
                matched.add(line_idx)

    # Tier 2: anchor match (<!-- section: section-03-config -->)
    anchor_pattern = f"<!-- section: {section_name} -->"
    for i, line in enumerate(lines):
        if anchor_pattern in line:
            # Find the next heading after this anchor
            for line_idx, level, text in headings:
                if line_idx > i:
                    matched.add(line_idx)
                    break

    # Tier 3: keyword fallback (only if no tier-1 or tier-2 matches)
    if not matched and keywords:
        for line_idx, level, text in headings:
            text_lower = text.lower()
            if any(kw in text_lower for kw in keywords):
                matched.add(line_idx)

    return sorted(matched)


def _extract_blocks(
    lines: list[str],
    headings: list[tuple[int, int, str]],
    matched_indices: list[int],
) -> list[str]:
    """Extract content blocks for matched heading indices, in document order."""
    if not matched_indices:
        return []

    blocks: list[str] = []
    heading_line_set = {h[0] for h in headings}

    for match_idx in matched_indices:
        # Find this heading's level
        match_level = None
        for line_idx, level, text in headings:
            if line_idx == match_idx:
                match_level = level
                break
        if match_level is None:
            continue

        # Extract from heading through to next heading of same/higher level
        block_lines = [lines[match_idx]]
        for j in range(match_idx + 1, len(lines)):
            # Check if this line is a heading of same or higher level
            if j in heading_line_set:
                for h_idx, h_level, h_text in headings:
                    if h_idx == j and h_level <= match_level:
                        break
                else:
                    block_lines.append(lines[j])
                    continue
                break
            else:
                block_lines.append(lines[j])

        blocks.extend(block_lines)

    return blocks


def _extract_section_summary(index_content: str, section_name: str) -> str:
    """Extract the summary line for a section from the human-readable part of index.md."""
    # Look for ### section-name followed by description text
    pattern = rf"###\s+{re.escape(section_name)}\s*\n(.*?)(?=\n###|\n##|\Z)"
    match = re.search(pattern, index_content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return f"(No summary found for {section_name})"
