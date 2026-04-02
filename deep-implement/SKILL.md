---
name: deep-implement
description: Executes deep-plan implementation plans section by section with progress tracking, error logging, and quality gates. Use after /deep-plan to implement the generated blueprint.
---

# Deep Implement

Executes a deep-plan blueprint section by section, tracking progress on disk.

## CRITICAL: First Actions

### 1. Locate the Planning Directory

The user must provide the planning directory path (where deep-plan wrote its output).

**If invoked with @path:** Use the provided path. If it points to a file, use its parent directory.
**If invoked without a path:**
- Check `~/.claude/.deep-plan-active` for the last active planning directory
- If not found, ask the user for the path

### 2. Validate the Planning Directory

Check that required files exist:
```
<planning_dir>/claude-plan.md          (required)
<planning_dir>/sections/index.md       (required)
<planning_dir>/claude-plan-tdd.md      (optional but recommended)
```

If `claude-plan.md` or `sections/index.md` is missing:
```
deep-implement requires a completed deep-plan output.
Missing: {list of missing files}

Run /deep-plan @path/to/spec.md first to generate the implementation plan.
```
**Stop and wait for user.**

### 3. Parse Section Index

Read `sections/index.md` and extract:
1. **SECTION_MANIFEST block** — ordered list of section filenames
2. **Dependency graph** — which sections depend on which
3. **PROJECT_CONFIG block** — runtime, test_command

Store these for the execution loop.

### 4. Initialize Tracking Files

Create three tracking files in the planning directory (skip if they already exist for resume):

**`<planning_dir>/impl-task-plan.md`:**
```markdown
# Implementation Plan

**Goal:** Implement all sections from deep-plan blueprint
**Planning Dir:** {planning_dir}
**Started:** {timestamp}

## Phases

{For each section from SECTION_MANIFEST:}
### Phase {N}: {section-name}
**Status:** pending
**File:** sections/{section-name}.md
**Depends On:** {dependencies from index.md}

- [ ] Read section specification
- [ ] Implement code changes
- [ ] Run tests ({test_command from PROJECT_CONFIG})
- [ ] Verify no TODOs or stub code left
- [ ] Mark complete
```

**`<planning_dir>/impl-findings.md`:**
```markdown
# Implementation Findings

## Technical Decisions
| Decision | Rationale | Section |
|----------|-----------|---------|

## Issues Encountered
| Issue | Section | Resolution |
|-------|---------|------------|

## Resources
- Planning dir: {planning_dir}
- Test command: {test_command}
```

**`<planning_dir>/impl-progress.md`:**
```markdown
# Implementation Progress

## Section Checklist
{For each section:}
- [ ] {section-name}

## Error Log
| Timestamp | Section | Error | Attempt | Resolution |
|-----------|---------|-------|---------|------------|

## Session Log
```

### 5. Write Active Marker

Write the planning directory path to `~/.claude/.deep-implement-active`:
```python
Path.home() / ".claude" / ".deep-implement-active"
```
This enables the discipline hooks (PreToolUse, PostToolUse, Stop) to find the tracking files.

### 6. Check for Resume

If tracking files already exist, scan `impl-progress.md` for checked-off sections.
Resume from the first unchecked section.

Print:
```
Sections: {total} total, {completed} done, {remaining} remaining
Next: {next_section_name}
```

---

## Execution Loop

For each section in dependency order (from index.md):

### A. Check Dependencies

Verify all blocking sections are complete (checked in impl-progress.md).
If a dependency is incomplete, skip this section and move to the next unblocked one.

### B. Read Section Spec

Read `sections/{section-name}.md` — this contains the implementation specification
from deep-plan, including what to build, design decisions, and interfaces.

Also read the corresponding test stubs from `claude-plan-tdd.md` if it exists.

### C. Implement

Write the code. Follow these rules:
1. **Tests first** — write tests from TDD stubs before implementation code
2. **One section at a time** — don't look ahead or modify code from other sections
3. **Log errors** — if something fails, add a row to the Error Log in impl-progress.md
4. **3-strike rule** — if the same error occurs 3 times with different approaches, log it and ask the user for guidance

### D. Quality Gate

After implementing the section:

1. **Run tests:**
   ```bash
   {test_command from PROJECT_CONFIG}
   ```

2. **Check for stub code:**
   - Search for `TODO`, `FIXME`, `pass  #`, `raise NotImplementedError` in changed files
   - If found, fix them before marking complete

3. **Verify section completeness:**
   - All items from the section spec are addressed
   - Tests pass
   - No regressions in other sections' tests

### E. Update Progress

1. Check off the section in `impl-progress.md`: `- [ ]` → `- [x]`
2. Update the phase status in `impl-task-plan.md`: `**Status:** pending` → `**Status:** complete`
3. Add a session log entry: `- Completed {section-name}: {brief summary}`
4. Log any technical decisions to `impl-findings.md`

### F. Next Section

Move to the next unblocked section. If all sections are complete, proceed to Final Verification.

---

## Final Verification

After all sections are implemented:

1. Run the full test suite
2. Check for any remaining TODOs/FIXMEs across the codebase
3. Verify all phases in impl-task-plan.md are marked complete
4. Print summary:

```
Implementation Complete

Sections: {total}/{total} done
Tests: {pass/fail}
Files modified: {list}

Next steps:
- Review the changes
- Commit when satisfied
```

5. Remove the active marker: delete `~/.claude/.deep-implement-active`

---

## Resuming After /clear or Compaction

The tracking files on disk are the source of truth. After context loss:

1. Read `~/.claude/.deep-implement-active` to find the planning directory
2. Read `impl-progress.md` to see which sections are done
3. Read `impl-task-plan.md` for the current phase status
4. Read `impl-findings.md` for accumulated technical decisions
5. Resume from the first incomplete section

The PreToolUse hook automatically injects the first 30 lines of impl-progress.md
into context before every Write/Edit/Bash call, keeping goals attended.
