---
name: deep-plan
description: Creates detailed, sectionized, TDD-oriented implementation plans through research, stakeholder interviews, and multi-LLM review. Use when planning features that need thorough pre-implementation analysis.
license: MIT
compatibility: Requires uv (Python 3.11+), Gemini or OpenAI API key for external review
---

# Deep Planning Skill

Research → Interview → External LLM Review → TDD Plan → Sectionized Implementation Blueprint

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

### 2. Validate Spec File

User must provide `@path/to/spec.md`. If no `.md` file provided, print usage and stop:
```
DEEP-PLAN requires a markdown spec file. Usage: /deep-plan @path/to/spec.md
```

### 3. Setup Session

```bash
uv run ${plugin_root}/scripts/checks/setup-session.py \
  --file "<spec_file>" --plugin-root "${plugin_root}" \
  --review-mode "${review_mode}" --session-id "${DEEP_SESSION_ID}"
```

Parse JSON output:
- `mode == "new"`: print planning directory, proceed to workflow loop
- `mode == "resume"`: print ready issues, proceed to workflow loop
- `mode == "complete"`: print completion message, stop
- `success == false`: show error and stop

Store `planning_dir`, `initial_file`, `plugin_root` from the output.

## Workflow Loop

After setup, execute steps by following the tracker:

```
1. Load tracker from {planning_dir}/.deepstate/
2. Call tracker.ready() → returns next unblocked step(s)
3. Read the step's reference file (see table below)
4. Execute the step following the reference instructions
5. Call tracker.close(issue_id, reason)
6. Repeat from 2 until all steps are closed
```

For the "Generate Sections" step, run:
```bash
uv run ${plugin_root}/scripts/checks/generate-sections.py \
  --planning-dir "${planning_dir}" --session-id "${DEEP_SESSION_ID}"
```

For "Write Section Files", read `references/section-splitting.md` for the batch subagent loop.

## Reference File Index

| Step | Reference |
|------|-----------|
| Research Decision | `references/research-protocol.md` |
| Execute Research | `references/research-protocol.md` |
| Detailed Interview | `references/interview-protocol.md` |
| Save Interview | Write Q&A to `claude-interview.md` |
| Write Spec | Combine input + research + interview into `claude-spec.md` |
| Generate Plan | `references/plan-writing.md` |
| Context Check | `references/context-check.md` |
| External Review | `references/external-review.md` |
| User Review | AskUserQuestion to review `claude-plan.md` |
| Apply TDD | `references/tdd-approach.md` |
| Create Section Index | `references/section-index.md` |
| Generate Sections | Run `generate-sections.py` (see above) |
| Write Sections | `references/section-splitting.md` |
| Final Verification | Run `check-sections.py`, confirm all sections exist |
| Output Summary | Print generated files and next steps |

## Guardrails

1. **Always read the reference file for the current step before executing.**
2. **Never skip a step — tracker.ready() determines order.**
3. **Always close the step with tracker.close() after completing it.**

## Resuming After Compaction

After `/clear` or context compaction:
1. Read `{planning_dir}/.deepstate/state.json` to restore tracker state
2. Call `tracker.ready()` — returns exactly where to continue
3. Each step's issue description includes reference file pointers and "Resume Here" hints
4. Reference files are at `{plugin_root}/references/`
