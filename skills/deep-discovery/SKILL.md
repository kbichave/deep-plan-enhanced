---
name: deep-discovery
description: General-purpose system discovery and product planning. Works on existing codebases (audit + roadmap) or greenfield projects (ecosystem research + architecture). Produces focused per-topic files, dynamic phase specs, and granular build-vs-buy analysis. Researches deeply before asking questions — including competitors, packages, and academic papers. Use when you need to understand a system, plan a product, or create a migration roadmap.
license: MIT
compatibility: Requires uv (Python 3.11+), optional Gemini or OpenAI API key for external review
---

# Deep Discovery Skill

System audit and product planning: Research → Interview → Audit Docs → Build-vs-Buy → Phase Specs

**Key Principles:**
- Research deeply before asking questions
- Present findings before interviewing
- Write focused per-topic files, not monolithic documents
- Let research drive the structure — do not hardcode categories

## First Actions

### 1. Validate Environment

Locate `DEEP_PLUGIN_ROOT` from SessionStart hook context. Run:
```bash
bash ${DEEP_PLUGIN_ROOT}/scripts/checks/validate-env.sh
```
Parse JSON output. Store `plugin_root` and map `review_available` to `review_mode`:
- `"full"` / `"gemini_only"` / `"openai_only"` → `review_mode = "external_llm"`
- `"none"` → ask user: Opus subagent (→ `"opus_subagent"`), skip (→ `"skip"`), or exit

If `valid == false`: show errors and stop.

### 2. Determine Target

User provides `@path` — can be a directory (existing codebase) or a spec file (greenfield).

Detect mode:
- **Existing system**: `@path` is a directory with source code
- **Greenfield**: `@path` is a `.md` spec file describing what to build
- **Hybrid**: directory with partial code + spec describing additions

### 3. Setup Session

```bash
uv run ${plugin_root}/scripts/checks/setup-session.py \
  --file "<file_or_dir>" --plugin-root "${plugin_root}" \
  --review-mode "${review_mode}" --session-id "${DEEP_SESSION_ID}" \
  --workflow "audit"
```

Parse JSON output:
- `mode == "new"`: print planning directory, proceed to workflow loop
- `mode == "resume"`: print ready issues, proceed to workflow loop
- `mode == "complete"`: print completion message, stop
- `success == false`: show error and stop

Store `planning_dir`, `initial_file`, `plugin_root` from the output.

## Workflow Loop

After setup, execute steps by following the tracker via CLI:

```bash
# Get next unblocked step(s)
uv run ${plugin_root}/scripts/checks/tracker-cli.py --state-dir ${planning_dir}/.deepstate ready

# Close a completed step
uv run ${plugin_root}/scripts/checks/tracker-cli.py --state-dir ${planning_dir}/.deepstate close "<issue-id>" "reason for closing"

# Recover context after compaction
uv run ${plugin_root}/scripts/checks/tracker-cli.py --state-dir ${planning_dir}/.deepstate prime
```

Loop:
1. Call `ready` → returns next unblocked step(s)
2. Read the step's reference file (see table below)
3. Execute the step following the reference instructions
4. Call `close` with the issue ID and reason
5. Repeat from 1 until all steps are closed

## Reference File Index

| Step | Reference |
|------|-----------|
| Quick Scan | `references/audit-research-protocol.md` |
| Deep Research | `references/audit-research-protocol.md` |
| Auto Gap ID | Analyze findings, write current-state/ and gaps/ files |
| Stakeholder Interview | `references/audit-interview-protocol.md` |
| Generate Audit Docs | `references/audit-doc-writing.md` |
| Build-vs-Buy Analysis | `references/audit-build-vs-buy.md` |
| Phase Specs | `references/audit-phasing.md` |
| External Review | `references/external-review.md` |
| User Review | Present audit directory for review |
| Output Summary | Generate README.md index, print file listing |

## Guardrails

1. **Always read the reference file for the current step before executing.**
2. **Never skip a step — tracker-cli ready determines order.**
3. **Always close the step with tracker-cli close after completing it.**

## Resuming After Compaction

After `/clear` or context compaction:
1. Read `{planning_dir}/.deepstate/state.json` to restore tracker state
2. Call `tracker-cli ready` — returns exactly where to continue
3. Each step's issue description includes reference file pointers and "Resume Here" hints
4. Reference files are at `{plugin_root}/references/`
