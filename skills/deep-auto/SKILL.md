---
name: deep-auto
description: Fully autonomous plan-and-implement pipeline. Plans all phases from a discovery audit and implements each one — no human review, no interviews, no pauses. Use after /deep-discovery when you want end-to-end autonomous execution.
license: MIT
compatibility: Requires uv (Python 3.11+), completed deep-discovery audit with phases/ directory
---

# Deep Auto

Autonomous end-to-end: plan every phase, then implement every phase. No human interaction.

Skips: interviews, user review, context checks. Keeps: research, spec writing, external LLM review, TDD, section splitting, implementation.

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
DEEP-AUTO: Valid discovery audit required

Expected: A directory from /deep-discovery containing:
  phases/phasing-overview.md  (with Dependency Graph section)
  phases/P00-*.md, P01-*.md   (at least one phase spec)

Usage: /deep-auto @path/to/discovery-audit/phases/
```

### 3. Setup Session

```bash
uv run ${plugin_root}/scripts/checks/setup-session.py \
  --file "<phases_dir>" --plugin-root "${plugin_root}" \
  --review-mode "${review_mode}" --session-id "${DEEP_SESSION_ID}" \
  --workflow "auto"
```

The setup script creates the full workflow with human-interactive steps pre-closed (interview, user-review, context-checks).

## Phase 1: Plan All Phases

Walk the tracker. For each phase, the remaining (non-skipped) steps are:

| Step | What To Do |
|------|-----------|
| Research Decision | Read `references/research-protocol.md`. Pick research topics from the phase spec. |
| Execute Research | Launch codebase + web research subagents. Later phases: review discovery findings instead. |
| Write Spec | Combine phase spec + research into `claude-spec.md` |
| Generate Plan | Read `references/plan-writing.md`. Write `claude-plan.md` |
| External Review | Read `references/external-review.md`. Run external LLM review based on review_mode. |
| Integrate Feedback | Update plan with review feedback |
| Apply TDD | Read `references/tdd-approach.md`. Create `claude-plan-tdd.md` |
| Section Index | Read `references/section-index.md`. Create `sections/index.md` with SECTION_MANIFEST |
| Generate Sections | Run `generate-sections.py` |
| Write Sections | Read `references/section-splitting.md`. Write section files via subagents |
| Final Verification | Verify all section files exist and plan is complete |
| Output Summary | Write phase planning summary |

After a phase's output-summary closes, close the phase issue itself.

## Phase 2: Implement All Phases

After ALL phases are planned, implement each phase in dependency order:

For each phase directory (containing `sections/index.md`):
1. Read `sections/index.md` to get implementation order
2. For each section in dependency order:
   - Read the section spec from `sections/section-NN-*.md`
   - Implement the code changes described
   - Run tests after each section
   - Write results to `impl-progress.md`
3. After all sections pass: write `impl-summary.md`

## Tracker Operations

Use the CLI helper for all tracker operations:
```bash
# See what's next
uv run ${plugin_root}/scripts/checks/tracker-cli.py --state-dir ${planning_dir}/.deepstate ready

# Close a completed step
uv run ${plugin_root}/scripts/checks/tracker-cli.py --state-dir ${planning_dir}/.deepstate close "<issue-id>" "reason"

# Check progress
uv run ${plugin_root}/scripts/checks/tracker-cli.py --state-dir ${planning_dir}/.deepstate prime
```

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
4. **No human interaction — do not ask questions, do not wait for approval.**
5. **If external LLM review fails (no API key), skip it and continue.**

## Resuming After Compaction

After `/clear` or context compaction:
1. Read `{planning_dir}/.deepstate/state.json` to restore tracker state
2. Call `tracker.ready()` — returns exactly where to continue
3. Each step issue description includes reference file pointers
4. Reference files are at `{plugin_root}/references/`
