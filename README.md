# deep-plan-enhanced

A Claude Code plugin with four skills for discovering, planning, and implementing complex systems.

**`/deep-discovery`** deeply researches an existing system or greenfield project. Produces a comprehensive discovery directory with focused per-topic files, dynamic phase specs, granular build-vs-buy analysis, and a migration roadmap. Researches competitors, packages, and academic papers before asking questions.

**`/deep-plan`** takes one piece of the audit roadmap and creates a detailed implementation blueprint through research, stakeholder interviews, multi-LLM review, and TDD-oriented section splitting.

**`/deep-plan-all`** batch-plans all phases from a discovery audit. Parses the phasing-overview dependency graph and orchestrates `/deep-plan` for each phase in the correct order.

**`/deep-implement`** executes that blueprint section by section with disk-based progress tracking, quality gates, and hooks that prevent goal drift.

## Installation

### As a Plugin (Recommended)

```bash
claude plugin add --from github:kbichave/deep-plan-enhanced
```

This registers all four skills and hooks automatically.

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

### Optional: Beads Integration

[Beads](https://github.com/plastic-labs/beads) provides richer issue tracking alongside the built-in deepstate tracker. Install it for optional sync:

```bash
brew install beads
```

When `bd` is on PATH, the plugin automatically mirrors issue operations to beads. If beads is unavailable or fails, the plugin continues normally — beads is never required.

## The Workflow

```
/deep-discovery                    Scan -> Research -> Interview -> Audit Docs -> Phase Specs -> Build-vs-Buy
                               (produces the system discovery + migration roadmap)

/deep-plan @phase-spec.md     Research -> Interview -> Plan -> Review -> TDD -> Sections
                               (produces the implementation blueprint for one phase)

/deep-plan-all @phases/       Parses phasing-overview.md -> Plans all phases in dependency order
                               (batch orchestration of /deep-plan across phases)

/deep-implement @plan-dir/    Reads sections -> Implements in dependency order
                               (writes the code, tracks progress, enforces quality)
```

The four skills form a complete pipeline: **discover → plan (or plan-all) → implement**.

## What's Inside

### /deep-discovery

A general-purpose system discovery that works on any project — existing codebase, greenfield, or hybrid.

| Step | What Happens |
|------|-------------|
| Quick Scan | Detect tech stack, structure, domain, codebase size |
| Deep Research | Parallel codebase agents + ecosystem agents (competitors, packages, arxiv papers) |
| Auto Gaps | Identify structural problems, missing capabilities, infrastructure gaps |
| Interview | Present findings, expand scope (suggest what user didn't ask for), extract priorities |
| Audit Docs | Parallel subagents write focused per-topic files (one topic per file) |
| Build-vs-Buy | Per-capability evaluation: pip install vs SaaS vs build custom |
| Phase Specs | Dynamic phases named from gaps (not hardcoded), with dependency graph |
| External Review | Multi-LLM review focused on missing gaps and wrong recommendations |

**Key features:**
- **Dynamic research depth** — 2 agents for a small CLI, 10+ for a large platform
- **Interview expands scope** — suggests capabilities user didn't ask for based on ecosystem research
- **Build-vs-buy is granular** — real package names with real version numbers per capability
- **Eval-on-write** — auto-scores each generated file, regenerates if below quality threshold
- **Findings accumulate on disk** — survives context loss via 2-Action Rule
- **Works on greenfield** — no code needed, researches ecosystem from a brief

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

### /deep-plan-all

Batch-plans all phases from a `/deep-discovery` audit. Parses `phasing-overview.md` dependency graph (ASCII `-->` or Unicode `──→` arrows), creates per-phase planning workflows with correct inter-phase dependencies, and executes them sequentially.

| Feature | Description |
|---------|-------------|
| **Dependency graph parsing** | Reads `## Dependency Graph` section from phasing-overview.md |
| **Parallel phase detection** | Independent phases (e.g., P02 and P03 both depending on P01) are not mutually blocked |
| **Interview skip** | Later phases pre-close interview steps (already done in discovery) |
| **Lighter research** | Later phases review discovery findings instead of launching new research subagents |

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
| **SubagentStop** | Section/audit-doc writer finishes | Extracts content and writes file to disk |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python 3.11+
- (Optional) Gemini API key or OpenAI API key for external plan review
- (Optional) [Beads](https://github.com/plastic-labs/beads) (`brew install beads`) for enhanced issue tracking

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

398 tests covering deepstate tracker, beads sync, workflow factory, session setup, section generation, hook behavior, integration lifecycle, and transcript parsing.

## Acknowledgments

- [deep-plan](https://github.com/piercelamb/deep-plan) by Pierce Lamb — the planning pipeline this project extends (MIT License)
- [planning-with-files](https://github.com/OthmanAdi/planning-with-files) by Ahmad Adi — the discipline patterns (attention manipulation, filesystem-as-memory, completion verification) that inspired the hook system
- [plan-cascade](https://github.com/Taoidle/plan-cascade) by Taoidle — quality gate and dependency-aware execution patterns

## License

MIT
