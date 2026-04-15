---
name: deep
description: Unified discovery, planning, and implementation. Modes — discovery: system audit → phase specs; plan: implementation blueprint; plan-all: batch-plan all phases; implement: execute sections; auto: autonomous end-to-end. Accepts @path, inline text, or no argument.
license: MIT
compatibility: Requires uv (Python 3.11+), optional Gemini or OpenAI API key for external review. Recommended: mempalace MCP for cross-session knowledge persistence
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
- `"none"` → ask user: Opus subagent (→ `"opus_subagent"`), Sonnet subagent (→ `"sonnet_subagent"`), skip (→ `"skip"`), or exit

If `valid == false`: show errors and stop.

### 1b. Check & Initialize Mempalace

1. Test if the `mempalace` MCP is connected by calling `mcp__mempalace__mempalace_status`.
2. If the tool is not available or the call errors with a non-palace error: set `mempalace_available = false`. Continue without it.
3. If the call returns `"No palace found"` or the palace has no wings for this project:
   - Run `mempalace init <project_working_directory> --yes` via Bash (auto-accepts, non-interactive)
   - Then run `mempalace mine <project_working_directory>` to seed the palace with project files
   - Re-check status to confirm initialization succeeded
4. If status succeeds: set `mempalace_available = true`. Derive a **wing name** from the project directory name (e.g., `my-service` for `/path/to/my-service`).

This is fully automatic — never ask the user to initialize mempalace.

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

**`--no-reframe` flag:** If the input text or spec file contains `--no-reframe`, skip the Premise Challenge round during the interview step. Auto mode always skips the premise challenge (no human to interact with). In plan mode, also skip if the spec contains >5 concrete file paths or function signatures (indicating the user has a highly specific, well-defined ask).

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

### 3b. Mempalace Experience Recall (ONLY if `mempalace_available == true`)

**Skip this step entirely if mempalace is not available.** Do not read the reference file.

If mempalace IS available: read `references/experience-protocol.md` and execute **Phase 1: Experience Recall**. This queries mempalace for prior decisions, coding patterns, lessons learned, domain knowledge, and known risks — then synthesizes an `experience_context` block (under 500 words) that travels with the workflow.

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
3. Auto mode only: if the ready step is a human-interactive step
   (user-review, context-check-pre-review, context-check-pre-split),
   auto-close it immediately with reason "Auto mode: skipped" and
   repeat from step 2
4. Read the step's reference file (see index below)
5. Execute the step
6. Mempalace mine (if mempalace_available) — see Knowledge Mining below
7. Call tracker.close(issue_id, reason)
8. Auto mode only: if this was an output-summary step (phase complete),
   run implement mode for this phase before continuing to next phase
9. Repeat from 2 until all steps are closed
```

### Mempalace Knowledge Mining (ONLY if `mempalace_available == true`)

**Skip entirely if mempalace is not available.** Do not read the reference file.

If mempalace IS available: follow `references/experience-protocol.md` **Phase 2** (store findings at each checkpoint) and **Phase 3** (proactive intelligence — surface risks, flag contradictions with prior decisions, predict gaps). Do NOT ask the user — store and surface intelligence silently.

---

## Reference File Index

### Cross-cutting (all modes)

| Concern | Reference |
|---------|-----------|
| Mempalace experience recall, knowledge mining, proactive intelligence | `references/experience-protocol.md` |
| Discovery bridge for plan-all/auto research + interview reuse | `references/discovery-bridge.md` |
| Plan mutation during implementation (split/skip/reorder/insert/amend) | `references/plan-mutation-protocol.md` |

### Discovery mode (`--workflow audit`)

| Step | Reference |
|------|-----------|
| Quick Scan | `references/audit-research-protocol.md` |
| Empirical Data Collection | `references/audit-data-collection.md` |
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
- Later phases: research and interview steps use `references/discovery-bridge.md` — reads discovery findings (max 5 per phase), identifies gaps, only researches gaps. Discovery interview is passed through to all phases.
- Reference: same as Plan mode per step, except research/interview for non-first phases

### Auto mode (`--workflow auto`)

Same as Plan-All, plus:
- Interview: replaced by self-interview subagents (no human interaction)
- User review: auto-closed when step becomes ready (do NOT pre-close — breaks dependency chain)
- **Implement after each phase:** After a phase's planning pipeline completes (sections written), run the implement workflow for that phase BEFORE starting the next dependent phase. This ensures later phases plan against the actual post-implementation codebase.

**Auto mode execution order (example with P01→P03→P05 chain):**
```
plan P01 → implement P01 → plan P03 → implement P03 → plan P05 → implement P05
```

Independent chains can interleave but each chain completes plan+implement before its dependents start planning:
```
Chain 1: plan P01 → implement P01 → plan P03 → ...
Chain 2: plan P02 → implement P02 → plan P04 → ...
```

### Implement mode

| Step | Reference |
|------|-----------|
| Initialize tracking | Create `impl-task-plan.md`, `impl-findings.md`, `impl-progress.md`, `impl-mutations.md` |
| Per-section: confidence gate | Rate 1-10 before coding (see Confidence Gate below) |
| Per-section: read spec | `sections/{section-name}.md` + `claude-plan-tdd.md` |
| Per-section: code standards | `references/coding-standards.md` (read before writing any code) |
| Per-section: implement | Tests first, then implementation |
| Per-section: eval check | Verify capability evals pass (new tests) and regression evals pass (existing tests) |
| Per-section: review | `agents/python-code-reviewer.md` (Python) or `agents/opus-plan-reviewer.md` (other) |
| Per-section: quality gate | ruff + mypy + bandit + pytest --cov (see `references/coding-standards.md`) |
| Per-section: close | `tracker.close(section_id, reason)`, update `impl-progress.md` |
| Plan mutation | `references/plan-mutation-protocol.md` — formal split/skip/reorder/insert/amend when reality diverges from plan |
| Final verification | Full test suite, no TODOs, write `impl-summary.md` |

#### Confidence Gate

Before coding each section, assess readiness on a 1-10 scale:

| Factor | Question |
|--------|----------|
| Spec clarity | Are the eval definitions, test stubs, and function signatures specific enough to implement without guessing? |
| Dependency readiness | Are all `depends_on` sections complete and their interfaces available? |
| Codebase context | Can you locate the files and modules this section integrates with? |
| Scope | Is this section implementable in a single pass (< 500 lines of changes)? |

**Score interpretation:**
- **8-10:** Proceed normally
- **5-7:** Proceed with caveats — log concerns in `impl-findings.md`, consider AMEND mutation
- **1-4:** Do NOT proceed — in interactive mode: ask user. In auto mode: log reason, apply SKIP or SPLIT mutation per `references/plan-mutation-protocol.md`, move to next section

#### Eval Check

After implementation, before review, verify against the section's eval definitions:
- **Capability evals:** Each checkbox item must have a corresponding passing test
- **Regression evals:** Run existing test suite — zero new failures allowed
- If any eval fails: fix before proceeding to review. If unfixable: log in `impl-findings.md` with reason

#### Rollback

If a section fails quality gates after 3 attempts (3-strike rule), consult the section's **Rollback Strategy** to undo changes cleanly before moving on.

**3-strike rule:** Same error 3 times → ask user (interactive) or log and continue with rollback (auto mode).

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
2. Check mempalace (step 1b) — if available, run recall (step 3b) to recover prior context
3. Call `tracker.prime()` and read `{planning_dir}/.deepstate/prime.md` for a compact status summary
4. Call `tracker.ready()` — returns exactly where to continue
5. For implement mode: read `impl-progress.md` for current section status
6. Reference files are at `{plugin_root}/references/`

If `planning_dir` is unknown: check `~/.claude/.deep-plan-active` for the last active session path.

Mempalace recall after compaction is especially valuable — it restores decisions, tradeoffs, and findings that were in the compacted context.
