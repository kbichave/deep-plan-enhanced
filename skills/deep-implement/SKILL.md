---
name: deep-implement
description: Executes deep-plan implementation plans section by section with progress tracking, error logging, and quality gates. Use after /deep-plan to implement the generated blueprint.
---

# Deep Implement

Executes a deep-plan blueprint section by section, driven by tracker.ready().

## First Actions

### 1. Locate the Planning Directory

**If invoked with @path:** Use the provided path. If it points to a file, use its parent directory.
**If invoked without a path:**
- Check `~/.claude/.deep-plan-active` for the last active planning directory
- If not found, ask the user for the path

### 2. Validate Planning Directory

Check that required files exist:
```
{planning_dir}/claude-plan.md          (required)
{planning_dir}/sections/index.md       (required)
{planning_dir}/.deepstate/state.json   (required)
```

If any are missing, tell the user to run `/deep-plan @spec.md` first.

### 3. Initialize Tracking Files

Create in the planning directory (skip if they already exist for resume):

- **`impl-task-plan.md`**: Phase-by-phase plan with status per section
- **`impl-findings.md`**: Technical decisions and issues encountered
- **`impl-progress.md`**: Section checklist, error log, session log

### 4. Check for Resume

Load the tracker from `{planning_dir}/.deepstate/`. Call `tracker.ready()` to find the next unblocked section. If sections are already complete (closed in tracker), skip them.

Print: `Sections: {total} total, {completed} done, {remaining} remaining`

## Execution Loop

For each section returned by `tracker.ready()`:

### A. Check Dependencies
Verify all blocking sections are closed in the tracker. `tracker.ready()` handles this automatically — it only returns unblocked sections.

### B. Read Section Spec
Read `sections/{section-name}.md` — the implementation specification from deep-plan.
Also read corresponding test stubs from `claude-plan-tdd.md` if it exists.

### C. Implement
1. **Tests first** — write tests from TDD stubs before implementation
2. **One section at a time** — don't modify code from other sections
3. **Log errors** — add rows to Error Log in `impl-progress.md`
4. **3-strike rule** — if same error occurs 3 times, ask the user

### D. Quality Gate
1. Run tests: `{test_command from PROJECT_CONFIG}`
2. Check for `TODO`, `FIXME`, `raise NotImplementedError` in changed files
3. Verify section spec is fully addressed

### E. Update Progress
1. Check off section in `impl-progress.md`: `- [ ]` → `- [x]`
2. Update phase status in `impl-task-plan.md`
3. Call `tracker.close(section_id, reason)` to mark complete
4. Log decisions to `impl-findings.md`

### F. Next Section
Call `tracker.ready()` for next unblocked section. Repeat until all done.

## Final Verification

After all sections complete:
1. Run full test suite
2. Check for remaining TODOs/FIXMEs
3. Write `impl-summary.md` (required before exit)

## Guardrails

1. **Always read the reference file for the current step before executing.** For /deep-implement, the "reference" is `sections/{section-name}.md`.
2. **Never skip a step — tracker.ready() determines order.**
3. **Always close the step with tracker.close() after completing it.**

## Resuming After Compaction

After `/clear` or context compaction:
1. Read `{planning_dir}/.deepstate/state.json` to restore tracker state
2. Call `tracker.ready()` — returns exactly where to continue
3. Read `impl-progress.md` for completed sections and error history
4. Read `impl-findings.md` for accumulated technical decisions
