# deep-plan-enhanced

A Claude Code plugin for discovering, planning, and implementing complex systems — one unified `/deep` skill with five modes.

```
/deep discovery @path               → system audit + phase specs
/deep plan @spec.md                 → implementation blueprint
/deep plan-all @phases/             → batch-plan all phases
/deep implement [@plan-dir/]        → execute sections
/deep auto @phases/                 → autonomous end-to-end
```

Also accepts **inline text** or **no argument** — the plugin synthesizes a spec or objective from git history + codebase context before proceeding.

## Installation

### As a Plugin (Recommended)

```bash
claude plugin marketplace add github:kbichave/deep-plan-enhanced
claude plugin install deep-plan-enhanced
```

This registers the `/deep` skill and all hooks automatically.

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

### Optional Integrations

- **[Beads](https://github.com/plastic-labs/beads)** — richer issue tracking alongside the built-in deepstate tracker. When `bd` is on PATH, the plugin automatically mirrors issue operations. Never required.
- **[MemPalace](https://github.com/milla-jovovich/mempalace)** — cross-session intelligence layer. Installed as a dependency (`uv sync`). When the `mempalace` MCP is connected, the plugin automatically initializes and mines knowledge — no user setup required. See [Experience Protocol](#experience-protocol) below.

## The Workflow

```
/deep discovery    Scan → Topic Enumeration → Research → Coverage Validation → Gaps → Interview → Audit Docs → Build-vs-Buy → Phase Specs
                   (produces system discovery + migration roadmap)

/deep plan         Research → Interview → Spec → Plan → Review → TDD → Sections
                   (produces implementation blueprint for one phase)

/deep plan-all     Parses phasing-overview.md → Plans all phases in dependency order
                   (batch orchestration of /deep plan across phases)

/deep implement    Reads sections → Implements in dependency order with quality gates
                   (writes code, tracks progress, enforces standards)

/deep auto         Discovery → Plan-All → Implement (fully autonomous, no user interaction)
```

## What's Inside

### /deep discovery

A general-purpose system discovery that works on any project — existing codebase, greenfield, or hybrid. Uses a STORM-inspired topic enumeration pattern for guaranteed research coverage.

| Step | What Happens |
|------|-------------|
| Quick Scan | Detect tech stack, structure, domain, codebase size. Write `scan-summary.md` |
| Topic Enumeration | Simulate 3 perspectives (security auditor, new engineer, PM). Generate 12–20 research topics in `research-topics.yaml` with categories, priorities, and questions |
| Deep Research | Parallel agents assigned specific topics from the manifest (2–3 topics each). Each writes `findings/<topic-id>-<slug>.md` |
| Coverage Validation | Run `validate-coverage.py`, spawn gap agents for uncovered topics, loop until ≥80% coverage |
| Auto Gap ID | Identify structural problems, missing capabilities, infrastructure gaps from per-topic findings |
| Stakeholder Interview | Present coverage map (`research-topics.yaml`), expand scope, extract priorities |
| Generate Audit Docs | Parallel subagents write focused per-topic files (one topic per file) |
| Build-vs-Buy Analysis | Per-capability evaluation: pip install vs SaaS vs build custom |
| Phase Specs | Dynamic phases named from gaps (not hardcoded), with dependency graph |
| External Review | Multi-LLM review focused on missing gaps and wrong recommendations |

**Key features:**
- **Topic-driven research** — agents are assigned specific topics, not open-ended missions (STORM-inspired, 25% better coverage breadth)
- **3-perspective enumeration** — security auditor + new engineer + PM viewpoints ensure comprehensive topic coverage
- **Coverage validation loop** — automated gap agents fill uncovered topics until ≥80% threshold
- **Per-topic findings files** — `findings/<topic-id>-<slug>.md` instead of monolithic output
- **Cross-session intelligence** — MemPalace experience protocol recalls prior decisions, patterns, and lessons to make each session smarter (see below)
- **Dynamic research depth** — 2 agents for a small CLI, 10+ for a large platform
- **Interview expands scope** — suggests capabilities user didn't ask for based on ecosystem research
- **Build-vs-buy is granular** — real package names with real version numbers per capability
- **Eval-on-write** — auto-scores each generated file, regenerates if below quality threshold

### /deep plan

A multi-step planning pipeline that produces a complete implementation blueprint before any code is written.

| Step | What Happens |
|------|-------------|
| Research | Codebase exploration + web research via subagents |
| Interview | Structured stakeholder Q&A to surface hidden requirements |
| Spec | Synthesized specification from input + research + interview |
| Plan | Detailed implementation plan (prose, not code) |
| External Review | Parallel review by Gemini + OpenAI (or Opus fallback) |
| TDD | Test stub plan mirroring the implementation sections |
| Sections | Self-contained implementation units with dependency graph |

**Inline prompt support:** No spec file required. Run `/deep plan "add OAuth2 login"` and the plugin synthesizes a spec from git history + codebase context, confirms with you, then proceeds.

### /deep plan-all

Batch-plans all phases from a `/deep discovery` audit. Parses `phasing-overview.md` dependency graph (ASCII `-->` or Unicode `──→` arrows), creates per-phase planning workflows with correct inter-phase dependencies, and executes them sequentially.

| Feature | Description |
|---------|-------------|
| **Dependency graph parsing** | Reads `## Dependency Graph` section from phasing-overview.md |
| **Parallel phase detection** | Independent phases (e.g., P02 and P03 both depending on P01) are not mutually blocked |
| **Interview skip** | Later phases pre-close interview steps (already done in discovery) |
| **Lighter research** | Later phases review discovery findings instead of launching new research subagents |

### /deep implement

Executes the blueprint section by section with strict quality gates.

| Feature | Description |
|---------|-------------|
| **Dependency-aware execution** | Reads `sections/index.md` and implements in the right order |
| **Coding standards** | Reads `references/coding-standards.md` before each section (type-first, security-aware) |
| **Python code reviewer** | 7-criterion reviewer agent: anti-patterns, security, correctness, design, spec-compliance, type-coverage, documentation |
| **Quality gates** | `ruff check`, `mypy --strict`, `bandit -r`, `pytest --cov ≥85%` must pass per section |
| **3-file tracking** | `impl-task-plan.md`, `impl-findings.md`, `impl-progress.md` persist across `/clear` |
| **3-strike error rule** | Same error 3 times with different approaches → escalate to user |
| **Exit summary** | Stop hook requires `impl-summary.md` before allowing exit |

### /deep auto

Fully autonomous end-to-end pipeline: discovery → plan-all → implement. No user interaction required — interviews are replaced by self-interview subagents, user reviews are pre-closed, and the implement phase runs autonomously.

## Session Storage

All session state is written to `~/.claude/marketplace/deep-plan-enhanced/sessions/` — project working trees stay clean. No `.deepstate/`, `sessions/`, or `audit/` directories are created in your project.

```
~/.claude/marketplace/deep-plan-enhanced/sessions/
  <project-slug>/                    ← e.g. my-api-a3f9c1
    index.json                       ← lists all sessions for this project
    <session-prefix>/                ← first 8 chars of DEEP_SESSION_ID
      .deepstate/state.json
      deep_plan_config.json
      claude-plan.md
      sections/
      findings/
      research-topics.yaml
      ...
```

Legacy sessions that already exist inside project directories are detected via file markers and left in place — existing work is never lost.

## Hooks

| Hook | When | What |
|------|------|------|
| **SessionStart** | Session begins | Captures session ID + plugin root for task isolation |
| **PostToolUse** | After Write/Edit | Nudges agent to update progress files |
| **Stop** | Agent tries to exit | Requires implementation summary; blocks exit if sections incomplete |
| **SubagentStop** | Section/audit-doc writer finishes | Extracts content and writes file to disk |

## Architecture

### State Management

| Concern | Storage | System |
|---------|---------|--------|
| Workflow step progress | `.deepstate/state.json` | `DeepStateTracker` |
| Workflow steps → Beads CLI (optional) | Beads CLI (`bd`) | `BeadsSyncTracker` |
| Research topics + coverage + findings | MemPalace (if installed) or `research-topics.yaml` | `ResearchTopicStore` |
| Session index across projects | MemPalace (if installed) or `index.json` | `ResearchTopicStore` |
| Cross-session intelligence | MemPalace rooms: codecraft, decisions, experience, domain, risks | Experience Protocol |

### Library Modules (`scripts/lib/`)

| Module | Purpose |
|--------|---------|
| `deepstate.py` | JSON dependency graph tracker with atomic writes |
| `beads_sync.py` | Write-through wrapper that mirrors to Beads CLI |
| `research_topics.py` | `ResearchTopicStore` — MemPalace or flat-file backend for research topics |
| `workflow.py` | Workflow issue factory — creates task graphs for each mode |
| `tasks.py` | Task definitions, IDs, and dependency edges for all workflow modes |
| `config.py` | Session config (read/write `deep_plan_config.json`) |
| `sections.py` | Section manifest parser (`index.md` → section list with dependencies) |
| `prompts.py` | External review prompt templates (Gemini, OpenAI, Opus fallback) |

### Reference Files (`references/`)

| File | Used By |
|------|---------|
| `audit-research-protocol.md` | Discovery: scan + deep research waves |
| `audit-topic-enumeration.md` | Discovery: STORM-inspired 3-perspective topic generation |
| `audit-coverage-validation.md` | Discovery: coverage gap detection + targeted gap agents |
| `audit-interview-protocol.md` | Discovery: stakeholder interview |
| `audit-doc-writing.md` | Discovery: parallel audit document generation |
| `audit-build-vs-buy.md` | Discovery: build-vs-buy evaluation per capability |
| `audit-phasing.md` | Discovery: dynamic phase spec generation |
| `auto-spec-synthesis.md` | All modes: inline prompt → spec/objective synthesis |
| `coding-standards.md` | Implement: Python quality standards (types, security, testing) |
| `research-protocol.md` | Plan: codebase + web research protocol |
| `interview-protocol.md` | Plan: stakeholder interview |
| `plan-writing.md` | Plan: plan document generation |
| `external-review.md` | Plan + Discovery: multi-LLM review orchestration |
| `tdd-approach.md` | Plan: TDD stub generation |
| `section-index.md` | Plan: section index creation |
| `section-splitting.md` | Plan: section splitting with dependency graph |
| `context-check.md` | Plan: context window management |
| `experience-protocol.md` | All modes: mempalace recall, knowledge mining, proactive intelligence |

### Agent Definitions (`agents/`)

| Agent | Purpose |
|-------|---------|
| `python-code-reviewer.md` | 7-criterion Python reviewer (anti-patterns, security, correctness, design, spec, types, docs) |
| `opus-plan-reviewer.md` | Plan review fallback when external LLMs unavailable |
| `audit-doc-writer.md` | Focused audit document generation per topic |
| `section-writer.md` | Self-contained section content generation |

## Experience Protocol

When the [MemPalace](https://github.com/milla-jovovich/mempalace) MCP is connected, the plugin runs a three-phase intelligence loop — fully automatic, no user action needed:

| Phase | When | What |
|-------|------|------|
| **Recall** | Session start | Query mempalace for prior decisions, coding patterns, lessons learned, domain knowledge, and known risks. Synthesize into an `experience_context` block that travels with the workflow. |
| **Mine** | After each workflow step | Store findings, architectural decisions, quality gate results, and domain insights as they're discovered — not batched at the end. Uses structured rooms: `codecraft`, `decisions`, `experience`, `research`, `domain`, `risks`, `reviews`, `implementation`. |
| **Think Ahead** | Every decision point | Surface risks the user hasn't asked about, flag contradictions with prior decisions, enforce observed conventions, predict gaps before they become problems. |

**On first run:** If no palace exists, the plugin runs `mempalace init --yes` and `mempalace mine` automatically.

**On resume after compaction:** Experience recall restores decisions and context lost during `/clear` or context compression.

**Cross-session accumulation:** Each `/deep` run gets smarter because it draws on what prior runs learned — not just about the code, but about what approaches worked, what failed, and what the user cares about.

See [`references/experience-protocol.md`](references/experience-protocol.md) for the full protocol.

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python 3.11+
- (Optional) Gemini API key or OpenAI API key for external plan review
- (Optional) [Beads](https://github.com/plastic-labs/beads) (`brew install beads`) for enhanced issue tracking
- (Recommended) [MemPalace](https://github.com/milla-jovovich/mempalace) MCP for cross-session intelligence (installed via `uv sync`, MCP connection optional)

## Tests

```bash
uv run pytest tests/ -q
```

437 tests covering deepstate tracker, beads sync, workflow factory, session setup, section generation, hook behavior, research topic store, skill structure, integration lifecycle, and transcript parsing.

## What's Different From the Originals

This project combines patterns from [deep-plan](https://github.com/piercelamb/deep-plan), [planning-with-files](https://github.com/OthmanAdi/planning-with-files), and research from [STORM](https://arxiv.org/abs/2402.14207) (Stanford), [Deep-Research-skills](https://github.com/Weizhena/Deep-Research-skills), and [python-skills](https://github.com/wdm0006/python-skills).

| Feature | Source |
|---------|--------|
| Unified `/deep` skill replacing 5 separate skills | New (v1.5.0) |
| Inline prompt → spec synthesis (no file required) | New (v1.5.0) |
| STORM-inspired topic enumeration + coverage validation | STORM paper + Deep-Research-skills |
| Per-topic findings files with coverage tracking | New (v1.5.0) |
| Python coding standards + 7-criterion code reviewer | python-skills patterns |
| Quality gates: ruff + mypy --strict + bandit + pytest --cov ≥85% | python-skills patterns |
| Session storage isolation (`~/.claude/marketplace/...`) | New (v1.5.0) |
| MemPalace experience protocol — recall, mine, think ahead | New (v1.7.1) |
| Session isolation (concurrent sessions don't overwrite) | New |
| PostToolUse progress nudge hooks | planning-with-files pattern |
| Stop hook with exit summary requirement | planning-with-files pattern |
| Section-by-section execution in dependency order | deep-plan sections + plan-cascade pattern |
| 3-file disk tracking (task plan, findings, progress) | planning-with-files pattern |
| Quality gates per section (tests, no stubs) | plan-cascade pattern |
| 3-strike error escalation | planning-with-files pattern |

## Acknowledgments

- [deep-plan](https://github.com/piercelamb/deep-plan) by Pierce Lamb — the planning pipeline this project extends (MIT License)
- [planning-with-files](https://github.com/OthmanAdi/planning-with-files) by Ahmad Adi — discipline patterns (attention manipulation, filesystem-as-memory, completion verification)
- [plan-cascade](https://github.com/Taoidle/plan-cascade) by Taoidle — quality gate and dependency-aware execution patterns
- [STORM](https://arxiv.org/abs/2402.14207) by Stanford — outline-first research enumeration for coverage breadth
- [Deep-Research-skills](https://github.com/Weizhena/Deep-Research-skills) by Weizhena — research skill patterns for discovery agents
- [python-skills](https://github.com/wdm0006/python-skills) by wdm0006 — Python coding standards and advanced quality gates

## License

MIT
