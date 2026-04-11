---
name: deep
description: Unified discovery, planning, and implementation. Modes — discovery: system audit → phase specs; plan: implementation blueprint; plan-all: batch-plan all phases; implement: execute sections; auto: autonomous end-to-end. Accepts @path, inline text, or no argument.
license: MIT
compatibility: Requires uv (Python 3.11+), optional Gemini or OpenAI API key for external review
---

# Deep Skill

Unified entry point for the full planning pipeline:

```
/deep discovery @path           → system audit + phase specs
/deep plan @spec.md             → implementation blueprint
/deep plan-all @phases/         → batch-plan all phases
/deep implement [@plan-dir/]    → execute sections
/deep auto @phases/             → autonomous end-to-end
```

Also accepts inline text or no argument — see **Resolve Input** below.

---

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

### 2. Resolve Input

Detect mode and argument:

| Argument form | Action |
|---|---|
| `discovery @path` or `@directory` (no `claude-plan.md` inside) | Mode = `audit` |
| `plan @file.md` or `@file.md` | Mode = `plan` |
| `plan-all @path` or `@directory` with `phasing-overview.md` | Mode = `plan-all` |
| `implement [@path]` or `@directory` with `claude-plan.md` + `sections/` | Mode = `implement` |
| `auto @path` | Mode = `auto` |
| Inline text (no `@`, not an existing path) | Synthesize spec first (see below) |
| No argument | Ask user: `"What do you want to build or audit?"` → treat answer as inline text |

**Inline text handling:** Read `references/auto-spec-synthesis.md` and follow it to:
1. Gather project context (git log, README, CLAUDE.md, top-level structure — no subagent)
2. Synthesize `claude-spec.md` (plan mode) or `objective.md` (discovery mode) in the planning directory
3. Confirm with user (one round)
4. Use the synthesized file as `initial_file` — proceed with the resolved mode

### 3. Setup Session

**For `discovery`, `plan`, `plan-all`, `auto` modes:**
```bash
uv run ${DEEP_PLUGIN_ROOT}/scripts/checks/setup-session.py \
  --file "<target>" --plugin-root "${DEEP_PLUGIN_ROOT}" \
  --review-mode "${review_mode}" --session-id "${DEEP_SESSION_ID}" \
  --workflow "<discovery→audit | plan | plan-all | auto>"
```

Parse JSON output:
- `mode == "new"`: print planning directory, proceed to workflow loop
- `mode == "resume"`: print ready issues, proceed to workflow loop
- `mode == "complete"`: print completion message, stop
- `success == false`: show error and stop

Store `planning_dir`, `initial_file`, `plugin_root` from the output.

**For `implement` mode:** Skip setup-session. Instead:
1. If `@path` provided: use it as `planning_dir` (or its parent if a file)
2. Otherwise: read `~/.claude/.deep-plan-active` for `planning_dir`
3. Validate: `{planning_dir}/claude-plan.md`, `{planning_dir}/sections/index.md`, `{planning_dir}/.deepstate/state.json` must all exist

---

## Workflow Loop

After setup, follow the tracker for the active mode:

```
1. Load tracker from {planning_dir}/.deepstate/
2. Call tracker.ready() → returns next unblocked step(s)
3. Read the step's reference file (see index below)
4. Execute the step
5. Call tracker.close(issue_id, reason)
6. Repeat from 2 until all steps are closed
```

---

## Reference File Index

### Discovery mode (`--workflow audit`)

| Step | Reference |
|------|-----------|
| Quick Scan | `references/audit-research-protocol.md` |
| Topic Enumeration | `references/audit-topic-enumeration.md` |
| Deep Research | `references/audit-research-protocol.md` |
| Coverage Validation | `references/audit-coverage-validation.md` |
| Auto Gap ID | Analyze findings per topic, write `current-state/` and `gaps/` |
| Stakeholder Interview | `references/audit-interview-protocol.md` |
| Generate Audit Docs | `references/audit-doc-writing.md` |
| Build-vs-Buy Analysis | `references/audit-build-vs-buy.md` |
| Phase Specs | `references/audit-phasing.md` |
| External Review | `references/external-review.md` |
| User Review | Present audit directory for review |
| Output Summary | Generate `README.md` index, print file listing |

### Plan mode (`--workflow plan`)

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
| Generate Sections | Run `generate-sections.py` (see below) |
| Write Sections | `references/section-splitting.md` |
| Final Verification | Run `check-sections.py`, confirm all sections exist |
| Output Summary | Print generated files and next steps |

For the **Generate Sections** step, run:
```bash
uv run ${DEEP_PLUGIN_ROOT}/scripts/checks/generate-sections.py \
  --planning-dir "${planning_dir}" --session-id "${DEEP_SESSION_ID}"
```

### Plan-All mode (`--workflow plan-all`)

Parse `phasing-overview.md` dependency graph. For each phase in topological order:
- First phase: full plan workflow (all steps above)
- Later phases: skip interview (pre-closed), review discovery findings instead of new research
- Reference: same as Plan mode per step

### Auto mode (`--workflow auto`)

Same as Plan-All, plus:
- Interview: replaced by self-interview subagents (no human interaction)
- User review: pre-closed
- After planning: implement all sections autonomously (see Implement mode)

### Implement mode

| Step | Reference |
|------|-----------|
| Initialize tracking | Create `impl-task-plan.md`, `impl-findings.md`, `impl-progress.md` |
| Per-section: read spec | `sections/{section-name}.md` + `claude-plan-tdd.md` |
| Per-section: code standards | `references/coding-standards.md` (read before writing any code) |
| Per-section: implement | Tests first, then implementation |
| Per-section: review | `agents/python-code-reviewer.md` (Python) or `agents/opus-plan-reviewer.md` (other) |
| Per-section: quality gate | ruff + mypy + bandit + pytest --cov (see `references/coding-standards.md`) |
| Per-section: close | `tracker.close(section_id, reason)`, update `impl-progress.md` |
| Final verification | Full test suite, no TODOs, write `impl-summary.md` |

**3-strike rule:** Same error 3 times → ask user (interactive) or log and continue (auto mode).

---

## Guardrails

1. **Always read the reference file for the current step before executing.**
2. **Never skip a step — `tracker.ready()` determines order.**
3. **Always close the step with `tracker.close()` after completing it.**
4. **For implement mode:** Do not exit until `impl-summary.md` exists (enforced by Stop hook).

---

## Resuming After Compaction

After `/clear` or context compaction:

1. Re-run `validate-env.sh` to restore `plugin_root`
2. Read `{planning_dir}/.deepstate/state.json` to restore tracker state
3. Call `tracker.ready()` — returns exactly where to continue
4. For implement mode: read `impl-progress.md` for current section status
5. Reference files are at `{plugin_root}/references/`

If `planning_dir` is unknown: check `~/.claude/.deep-plan-active` for the last active session path.
