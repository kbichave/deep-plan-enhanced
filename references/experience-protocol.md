# Experience Protocol — Mempalace Intelligence Layer

This protocol turns mempalace into an accumulating intelligence layer across sessions. Every `/deep` run gets smarter because it draws on what prior runs learned — not just about the project's code, but about what approaches worked, what failed, what the user cares about, and what patterns hide beneath the surface.

The goal: **think one step ahead of the user's ask.** Don't just answer what they asked — surface what they haven't thought to ask yet.

---

## Room Taxonomy

All mempalace storage uses the project's **wing name** (derived from the working directory name). Rooms are standardized:

| Room | What goes here | When to write |
|------|---------------|---------------|
| `codecraft` | Coding conventions, naming patterns, architectural style, framework idioms, test patterns | Discovery scan, implementation review |
| `decisions` | Architectural decisions, technology choices, tradeoffs made, rejected alternatives | Plan mode, build-vs-buy analysis |
| `experience` | What worked, what failed, approaches tried and abandoned, session retrospectives | After each workflow step, session end |
| `research` | Technical findings, ecosystem analysis, competitor capabilities, academic references | Discovery research waves |
| `domain` | Business rules, domain language, hidden constraints, user context, team dynamics | Discovery interviews, any time domain knowledge surfaces |
| `reviews` | External review feedback, code review findings, quality gate results | Plan review, implementation review |
| `risks` | Known failure modes, security concerns, scaling bottlenecks, tech debt | Discovery gaps, implementation findings |
| `implementation` | What was built, how sections were implemented, integration patterns | Implementation close |

---

## Phase 1: Experience Recall (Session Start)

Run this after mempalace init/check (SKILL.md step 3b). The goal is to build an `experience_context` block that travels with the workflow.

### Queries to run:

```
1. mempalace_search(query="architecture decisions tradeoffs patterns", wing=<wing>, limit=10)
2. mempalace_kg_query(entity=<wing>)
3. mempalace_search(query="coding conventions standards style", wing=<wing>, room="codecraft", limit=5)
4. mempalace_search(query="what worked what failed lessons learned", wing=<wing>, room="experience", limit=5)
5. mempalace_search(query="business rules domain constraints", wing=<wing>, room="domain", limit=5)
6. mempalace_search(query="known risks failure modes tech debt", wing=<wing>, room="risks", limit=3)
```

### Synthesize experience_context:

From the results, build a concise block (under 500 words) with these sections. Omit any section with no data.

```markdown
## Experience Context for <project>

### Settled Decisions
- <decision>: <rationale> (don't re-debate these)

### Coding Patterns
- <pattern observed>: <where and why>

### What Worked Before
- <approach>: <outcome>

### What Failed Before
- <approach>: <why it failed> (don't repeat these mistakes)

### Domain Knowledge
- <business rule or constraint not obvious from code>

### Known Risks
- <risk>: <status>

### User Context
- <relevant context about user's expertise, preferences, priorities>
```

Carry this block as active context. When making decisions, consult it first. When it conflicts with current observation, trust what you see now but note the discrepancy and update mempalace.

---

## Phase 2: Continuous Knowledge Mining (During Workflow)

This is NOT a batch operation at the end. Store knowledge **as you discover it**, at these specific checkpoints.

### Discovery Mode Checkpoints

| After this step | What to mine | How to store |
|---|---|---|
| Quick Scan | Tech stack, framework versions, project structure, domain classification | `kg_add(subject=<wing>, predicate="uses", object=<tech>)` for each technology. `add_drawer(wing, "codecraft", <structural patterns observed>)` |
| Deep Research (each wave) | Findings that reveal how the codebase actually works vs. how you'd expect | `add_drawer(wing, "research", <non-obvious findings>)`. Focus on surprises — things that would mislead a new reader. |
| Reflection Points | What's well-understood vs. still murky, contradictions found | `add_drawer(wing, "experience", "Wave N reflection: <what we learned, what surprised us>")` |
| Gap Identification | Each gap with its severity and why it matters | `kg_add(subject=<wing>, predicate="has_gap", object=<gap>)` per gap. `add_drawer(wing, "risks", <gap details + impact>)` |
| Build-vs-Buy | Decision + full rationale including what was rejected | `add_drawer(wing, "decisions", <decision with rejected alternatives and why>)` |
| Interview | Domain knowledge, business rules, user priorities | `add_drawer(wing, "domain", <business rules and constraints learned>)`. `kg_add(subject=<wing>, predicate="constrained_by", object=<constraint>)` |

### Plan Mode Checkpoints

| After this step | What to mine | How to store |
|---|---|---|
| Research | Ecosystem findings, package evaluations | `add_drawer(wing, "research", <findings>)` |
| Spec Written | Core approach and architecture chosen | `kg_add(subject=<wing>, predicate="planned_with", object=<approach>)` |
| Architecture Decision | Each significant decision with tradeoffs | `add_drawer(wing, "decisions", <decision + tradeoffs + rejected alternatives>)` |
| External Review | Reviewer feedback — especially pushback or concerns raised | `add_drawer(wing, "reviews", <feedback + how addressed>)` |
| TDD Applied | Test strategy chosen, edge cases identified | `add_drawer(wing, "codecraft", <test patterns and edge case coverage strategy>)` |

### Implementation Mode Checkpoints

| After this step | What to mine | How to store |
|---|---|---|
| Section Start (read spec) | Nothing — just recall experience_context to guide implementation |  |
| Code Written | Patterns used, deviations from plan and why | `add_drawer(wing, "codecraft", <patterns applied, any plan deviations>)` — only when non-obvious patterns emerge |
| Quality Gate | Pass/fail, coverage metrics, common issues found | `add_drawer(wing, "experience", "Section <name>: <pass/fail>, coverage <N>%, issues: <summary>")` |
| Section Complete | What was actually built (may differ from plan) | `kg_add(subject=<wing>, predicate="implemented", object=<section>)` |
| Review Findings | Code quality issues, anti-patterns found | `add_drawer(wing, "risks", <issues found + severity>)` if significant |

### All Modes — Session End

Write a diary entry summarizing the session:

```
diary_write(
  agent_name="deep-plan",
  entry="SESSION:<date>|mode:<mode>|project:<wing>|accomplished:<what was done>|open:<what remains>|learned:<key insight>",
  topic=<wing>
)
```

---

## Phase 3: Proactive Intelligence — Think Ahead

This is what separates a tool from a partner. At these moments, pause and think beyond the immediate task:

### During Discovery

- **Pattern recognition across projects:** If mempalace has data from other projects, look for cross-project patterns. "This auth approach has the same weakness I saw in project X."
- **Risk anticipation:** When you find a technology choice, proactively search mempalace for prior experience with that technology. Surface known pitfalls before the user hits them.
- **Gap prediction:** Don't just identify current gaps — predict gaps that will emerge at scale or when requirements change. Store these as `tier4` insights.

### During Planning

- **Decision memory:** Before proposing an architecture, check if mempalace records a prior decision about this exact topic. If yes, reference it: "In a prior session, we decided X because Y. That still holds / has changed because Z."
- **Approach validation:** When choosing between approaches, check `experience` room for prior outcomes. If Approach A failed before, say so — and explain why this time might be different (or suggest Approach B).
- **Coding standards evolution:** If `codecraft` room has observed patterns that aren't in `coding-standards.md`, note them. The reference file is static; the experience is dynamic.

### During Implementation

- **Convention enforcement:** Before writing code, check `codecraft` room. Follow observed patterns, not just generic standards. If the codebase uses a specific error handling pattern, use it.
- **Anti-pattern avoidance:** Check `experience` room for past quality gate failures. If "mypy strict mode catches X frequently," handle X proactively.
- **Integration awareness:** Check `decisions` room for architectural constraints that affect the current section. Don't violate a prior decision without flagging it.

### The "One Step Ahead" Principle

At every decision point, ask: **"What will the user wish they had known before making this choice?"**

- If you spot a scaling bottleneck, flag it before the user asks about performance.
- If a dependency has a known CVE or is unmaintained, surface it during planning, not after implementation.
- If two sections will create a circular dependency, catch it during planning when it's cheap to fix.
- If a business rule in the code contradicts what the user described, flag it — they may not know.
- If the test strategy won't catch a failure mode you've seen before, suggest additional coverage.

Store these proactive insights in `add_drawer(wing, "risks", <insight>)` so they persist for future sessions.

---

## Storage Rules

- **Always set `added_by="deep-plan"`** on all `add_drawer` calls
- **Always set `valid_from` to today's date** on all `kg_add` calls
- **Never block the workflow on mempalace** — if a call fails, log a warning and continue
- **Be concise** — store facts and decisions, not full documents. Aim for the minimum context that lets a future session make the right call.
- **Prefer `kg_add` for relationships** (uses → X, has_gap → Y, implemented → Z) and `add_drawer` for detailed content (rationale, tradeoffs, findings)
- **Deduplicate naturally** — mempalace checks for duplicates, but avoid storing the same insight multiple times with different wording. If updating a prior finding, search first and note the update.
- **Tag with workflow context** — include mode (discovery/plan/implement), step name, and session date in stored content so future recall can filter relevance
