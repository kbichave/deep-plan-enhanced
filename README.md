# deep-plan-enhanced

Two complementary Claude Code skills for planning and implementing complex features.

**deep-plan** creates a detailed implementation blueprint through research, stakeholder interviews, multi-LLM review, and TDD-oriented section splitting.

**deep-implement** executes that blueprint section by section with disk-based progress tracking, quality gates, and attention management hooks that prevent goal drift.

## What's Different From the Originals

This project combines patterns from [deep-plan](https://github.com/piercelamb/deep-plan) and [planning-with-files](https://github.com/OthmanAdi/planning-with-files) into a unified plan-then-execute workflow.

### Enhancements to deep-plan

| Feature | Description |
|---------|-------------|
| **Session isolation** | Concurrent `/deep-plan` sessions write to `sessions/<session-prefix>/` — no more file overwrites |
| **Attention hooks** | PreToolUse hook re-reads planning state before every Write/Edit/Bash call |
| **Progress tracking** | Human-readable `progress.md` with step checklist and error log table |
| **Stop verification** | Stop hook prevents premature exit if workflow steps are incomplete |
| **Local skill mode** | Runs as `~/.claude/skills/` instead of marketplace plugin — no CLAUDE_PLUGIN_ROOT dependency |

### deep-implement (new)

| Feature | Description |
|---------|-------------|
| **Section-by-section execution** | Reads deep-plan's `sections/index.md` and implements in dependency order |
| **3-file tracking** | `impl-task-plan.md`, `impl-findings.md`, `impl-progress.md` persist state across `/clear` and compaction |
| **Quality gates** | Tests must pass, no TODOs/stubs, section spec fully addressed before marking complete |
| **3-strike error rule** | Same error 3 times with different approaches → escalate to user |
| **Completion verification** | Stop hook auto-continues if sections remain incomplete |

## The Workflow

```
/deep-plan @spec.md           Research → Interview → Plan → Review → TDD → Sections
                               (produces the blueprint)

/deep-implement @plan-dir/    Reads sections → Implements in dependency order
                               (writes the code)
```

## Installation

### Quick Install

```bash
git clone https://github.com/kshitijbichave/deep-plan-enhanced.git
cd deep-plan-enhanced
bash install.sh
```

### Manual Install

1. Copy skills to `~/.claude/skills/`:
```bash
cp -r deep-plan ~/.claude/skills/deep-plan
cp -r deep-implement ~/.claude/skills/deep-implement
cd ~/.claude/skills/deep-plan && uv sync
```

2. Add hooks to `~/.claude/settings.json`:
```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run ~/.claude/skills/deep-plan/scripts/hooks/capture-session-id.py"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Write|Edit|Bash",
        "hooks": [
          {
            "type": "command",
            "command": "uv run ~/.claude/skills/deep-implement/scripts/hooks/pre-tool-use.py"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "uv run ~/.claude/skills/deep-implement/scripts/hooks/post-tool-use.py"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run ~/.claude/skills/deep-implement/scripts/hooks/stop.py"
          }
        ]
      }
    ],
    "SubagentStop": [
      {
        "matcher": "deep-plan:section-writer",
        "hooks": [
          {
            "type": "command",
            "command": "uv run ~/.claude/skills/deep-plan/scripts/hooks/write-section-on-stop.py"
          }
        ]
      }
    ]
  }
}
```

3. Start a new Claude Code session to activate the hooks.

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python 3.11+
- (Optional) Gemini API key or OpenAI API key for external plan review

## How the Hooks Work

| Hook | When | What |
|------|------|------|
| **SessionStart** | Session begins | Captures session ID for task isolation |
| **PreToolUse** | Before Write/Edit/Bash | Re-reads progress into context (attention manipulation) |
| **PostToolUse** | After Write/Edit | Nudges agent to update progress files |
| **Stop** | Agent tries to exit | Blocks exit if steps/sections are incomplete |
| **SubagentStop** | Section writer finishes | Extracts content and writes section file to disk |

The PreToolUse hook implements the "attention manipulation through recitation" pattern from [Manus AI](https://github.com/OthmanAdi/planning-with-files): by re-reading the current state before every tool call, goals stay in the attention window even after 50+ tool calls.

## Tests

```bash
cd deep-plan
uv run pytest tests/ -q
```

331 tests covering task storage, session isolation, section generation, hook behavior, and transcript parsing.

## Acknowledgments

- [deep-plan](https://github.com/piercelamb/deep-plan) by Pierce Lamb — the planning pipeline this project extends (MIT License)
- [planning-with-files](https://github.com/OthmanAdi/planning-with-files) by Ahmad Adi — the discipline patterns (attention manipulation, filesystem-as-memory, completion verification) that inspired the hook system
- [plan-cascade](https://github.com/Taoidle/plan-cascade) by Taoidle — quality gate and dependency-aware execution patterns

## License

MIT
