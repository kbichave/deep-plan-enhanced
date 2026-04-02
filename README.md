# deep-plan-enhanced

A Claude Code plugin with two skills for planning and implementing complex features.

**`/deep-plan`** creates a detailed implementation blueprint through research, stakeholder interviews, multi-LLM review, and TDD-oriented section splitting.

**`/deep-implement`** executes that blueprint section by section with disk-based progress tracking, quality gates, and hooks that prevent goal drift.

## Installation

### As a Plugin (Recommended)

```bash
claude plugin add --from github:kbichave/deep-plan-enhanced
```

This registers both skills and all hooks automatically.

### As Local Skills

```bash
# Clone
git clone https://github.com/kbichave/deep-plan-enhanced.git ~/.claude/plugins/deep-plan-enhanced

# Install Python dependencies
cd ~/.claude/plugins/deep-plan-enhanced && uv sync

# Enable the plugin
# Add to ~/.claude/settings.json:
# "enabledPlugins": { "deep-plan-enhanced@kbichave-plugins": true }
```

## The Workflow

```
/deep-plan @spec.md           Research -> Interview -> Plan -> Review -> TDD -> Sections
                               (produces the implementation blueprint)

/deep-implement @plan-dir/    Reads sections -> Implements in dependency order
                               (writes the code, tracks progress, enforces quality)
```

## What's Inside

### /deep-plan

A 22-step planning pipeline that produces a complete implementation blueprint before any code is written.

| Step | What Happens |
|------|-------------|
| Research | Codebase exploration + web research via subagents |
| Interview | Structured stakeholder Q&A to surface hidden requirements |
| Spec | Synthesized specification from input + research + interview |
| Plan | Detailed implementation plan (prose, not code) |
| External Review | Parallel review by Gemini + OpenAI (or Opus fallback) |
| TDD | Test stub plan mirroring the implementation sections |
| Sections | Self-contained implementation units with dependency graph |

**Session isolation:** Concurrent `/deep-plan` sessions write to `sessions/<prefix>/` subdirectories — no file overwrites.

### /deep-implement

Executes the blueprint section by section with discipline hooks.

| Feature | Description |
|---------|-------------|
| **Dependency-aware execution** | Reads `sections/index.md` and implements in the right order |
| **3-file tracking** | `impl-task-plan.md`, `impl-findings.md`, `impl-progress.md` persist across `/clear` |
| **Quality gates** | Tests must pass, no TODOs/stubs, section spec fully addressed |
| **3-strike error rule** | Same error 3 times with different approaches -> escalate to user |
| **Exit summary** | Stop hook requires `impl-summary.md` before allowing exit |

## Hooks

| Hook | When | What |
|------|------|------|
| **SessionStart** | Session begins | Captures session ID + plugin root for task isolation |
| **PostToolUse** | After Write/Edit | Nudges agent to update progress files |
| **Stop** | Agent tries to exit | Requires implementation summary; blocks exit if sections incomplete |
| **SubagentStop** | Section writer finishes | Extracts content and writes section file to disk |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python 3.11+
- (Optional) Gemini API key or OpenAI API key for external plan review

## What's Different From the Originals

This project combines patterns from [deep-plan](https://github.com/piercelamb/deep-plan) and [planning-with-files](https://github.com/OthmanAdi/planning-with-files).

### Enhancements to deep-plan

| Feature | Source |
|---------|--------|
| Session isolation (concurrent sessions don't overwrite) | New |
| PostToolUse progress nudge hooks | planning-with-files pattern |
| Stop hook with exit summary requirement | planning-with-files pattern |
| `progress.md` with step checklist and error log | planning-with-files pattern |

### deep-implement (new skill)

| Feature | Source |
|---------|--------|
| Section-by-section execution in dependency order | deep-plan sections + plan-cascade pattern |
| 3-file disk tracking (task plan, findings, progress) | planning-with-files pattern |
| Quality gates per section (tests, no stubs) | plan-cascade pattern |
| 3-strike error escalation | planning-with-files pattern |
| Mandatory exit summary (`impl-summary.md`) | New |

## Tests

```bash
uv run pytest tests/ -q
```

331 tests covering task storage, session isolation, section generation, hook behavior, and transcript parsing.

## Acknowledgments

- [deep-plan](https://github.com/piercelamb/deep-plan) by Pierce Lamb — the planning pipeline this project extends (MIT License)
- [planning-with-files](https://github.com/OthmanAdi/planning-with-files) by Ahmad Adi — the discipline patterns (attention manipulation, filesystem-as-memory, completion verification) that inspired the hook system
- [plan-cascade](https://github.com/Taoidle/plan-cascade) by Taoidle — quality gate and dependency-aware execution patterns

## License

MIT
