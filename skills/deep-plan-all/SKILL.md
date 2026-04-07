---
name: deep-plan-all
description: Batch-plans all phases from a deep-discovery audit. Parses phasing-overview.md, creates per-phase planning workflows with correct dependency ordering, and executes them sequentially with cross-phase awareness.
license: MIT
compatibility: Requires uv (Python 3.11+), completed deep-discovery audit with phases/ directory
---

# Deep Plan All

Orchestrates `/deep-plan` for every phase from a discovery audit.

## First Actions

### 1. Validate Environment

Locate `DEEP_PLUGIN_ROOT` from SessionStart hook context. Run:
```bash
bash ${DEEP_PLUGIN_ROOT}/scripts/checks/validate-env.sh
```
Parse JSON output. Store `plugin_root` and map `review_available` to `review_mode`.

### 2. Validate Input

User must provide `@path/to/phases/` or `@path/to/phasing-overview.md`.

Verify the phases directory contains:
- `phasing-overview.md` with a `## Dependency Graph` section
- At least one `P*.md` phase spec file

If validation fails:
```
DEEP-PLAN-ALL: Valid discovery audit required

Expected: A directory from /deep-discovery containing:
  phases/phasing-overview.md  (with Dependency Graph section)
  phases/P00-*.md, P01-*.md   (at least one phase spec)

Usage: /deep-plan-all @path/to/discovery-audit/phases/
```

### 3. Setup Session

```bash
uv run ${plugin_root}/scripts/checks/setup-session.py \
  --file "<phases_dir>" --plugin-root "${plugin_root}" \
  --review-mode "${review_mode}" --session-id "${DEEP_SESSION_ID}" \
  --workflow "plan-all"
```

The setup script initializes `.deepstate/` and creates the phase workflow hierarchy via `create_plan_all_workflow()`.

## Workflow Loop

After setup, execute phases by following the tracker:

```
1. Load tracker from {planning_dir}/.deepstate/
2. Call tracker.ready() → returns next unblocked step(s)
3. If a phase issue: print phase banner, continue
4. If a step issue: read reference file, execute, close
5. When a phase's output-summary closes, close the phase issue
6. Repeat from 2 until all phases complete
```

### Phase-Specific Behaviors

- **First phase**: Full planning — research, interview, spec, plan, review, TDD, sections
- **Later phases**: Interview steps are pre-closed (already done in discovery). Research reviews discovery findings instead of launching new subagents.

## Reference File Index

| Step | Reference |
|------|-----------|
| Research Decision | `references/research-protocol.md` |
| Generate Plan | `references/plan-writing.md` |
| External Review | `references/external-review.md` |
| TDD Approach | `references/tdd-approach.md` |
| Section Index | `references/section-index.md` |
| Write Sections | `references/section-splitting.md` |

## Guardrails

1. **Always read the reference file for the current step before executing.**
2. **Never skip a step — tracker.ready() determines order.**
3. **Always close the step with tracker.close() after completing it.**

## Resuming After Compaction

After `/clear` or context compaction:
1. Read `{planning_dir}/.deepstate/state.json` to restore tracker state
2. Call `tracker.ready()` — returns exactly where to continue
3. Each step issue description includes reference file pointers
4. Reference files are at `{plugin_root}/references/`
