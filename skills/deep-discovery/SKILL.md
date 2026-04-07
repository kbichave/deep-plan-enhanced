---
name: deep-discovery
description: General-purpose system discovery and product planning. Works on existing codebases (audit + roadmap) or greenfield projects (ecosystem research + architecture). Produces focused per-topic files, dynamic phase specs, and granular build-vs-buy analysis. Researches deeply before asking questions — including competitors, packages, and academic papers. Use when you need to understand a system, plan a product, or create a migration roadmap.
license: MIT
compatibility: Requires uv (Python 3.11+), optional Gemini or OpenAI API key for external review
---

# Deep Discovery Skill

General-purpose system audit and product planning tool.

**Works on anything:**
- Existing codebases — audit the system, find problems, plan migration
- Greenfield projects — research ecosystem, design architecture, plan build
- Hybrid — partial codebase + new features needed

**Philosophy:**
- Understand deeply before writing anything
- Research before asking questions
- Present findings before interviewing
- Expand the user's thinking — suggest what they didn't ask for
- Every recommendation backed by ecosystem research
- Never recommend "build from scratch" without evaluating pip/npm/SaaS alternatives
- Research goes as deep as arxiv papers when the domain warrants it

```
/deep-discovery     → Understand + Plan (produces audit directory)
/deep-plan      → Detail one piece (produces implementation sections)
/deep-implement → Build it (writes code)
```

## CRITICAL: First Actions

### 1. Validate Environment

Same as deep-plan. Run validate-env.sh, parse output, store `plugin_root` and `review_mode`.

```bash
bash <DEEP_PLUGIN_ROOT value>/scripts/checks/validate-env.sh
```

Handle errors identically to deep-plan step 1-2. Store `plugin_root` and `review_mode`.

### 2. Detect Audit Mode

**If invoked with @file** (e.g., `/deep-discovery @planning/product-vision.md`):
- Read the file — it's the audit brief (vision, constraints, what to investigate)
- Check if the current working directory has a codebase (look for pyproject.toml, package.json, Cargo.toml, go.mod, Makefile, src/, or any code files)
- If codebase exists: **Existing System Mode** — audit the code + apply the brief
- If no codebase: **Greenfield Mode** — the brief IS the product, research the ecosystem

**If invoked WITHOUT @file:**
- Check if cwd has a codebase
- If yes: **Existing System Mode** — audit whatever's here
- If no: Ask what they want to build → **Greenfield Mode**

Print mode:
```
═══════════════════════════════════════════════════════════════
DEEP-DISCOVERY: System Audit & Product Planning
═══════════════════════════════════════════════════════════════
Mode: {Existing System | Greenfield | Hybrid}
Target: {cwd or brief file description}
═══════════════════════════════════════════════════════════════
```

### 3. Setup Session

Run setup-planning-session.py with `--workflow audit`:

```bash
uv run {plugin_root}/scripts/checks/setup-planning-session.py \
  --file "<file_path_or_cwd>" \
  --plugin-root "{plugin_root}" \
  --review-mode "{review_mode}" \
  --session-id "{DEEP_SESSION_ID}" \
  --workflow "audit"
```

Initialize the audit directory with:
- `findings.md` — running research accumulator (structured with YAML-like metadata per section)
- `progress.md` — workflow step checklist
- `deep_plan_config.json` — session config

---

## Workflow

**IMPORTANT — Current Date:** The system context contains the current date. Use the CURRENT YEAR in ALL web search queries. NEVER hardcode any year — always derive from the system date.

**IMPORTANT — Findings Discipline (2-Action Rule):** After every 2 subagent returns, update `findings.md` with their results. Do NOT wait for all agents to complete. Findings survive context loss because they're on disk.

**IMPORTANT — Progress Tracking:** After completing each step, update `progress.md`.

### Steps 4-6: Evolutionary Research Loop (CORAL-Inspired)

Read `{plugin_root}/references/audit-research-protocol.md` for the full protocol.

**This is NOT a linear scan→research→gaps sequence.** It is an evolutionary loop where:
- Agents share knowledge through `findings.md` (shared state on disk)
- Each wave of agents reads what previous waves discovered
- Findings drive MORE targeted research (the search evolves)
- The loop continues until diminishing returns

```
┌─────────────────────────────────────────────────────────────┐
│  EVOLUTIONARY RESEARCH LOOP                                  │
│                                                              │
│  Wave 0: Quick Scan (1 agent)                               │
│    → Detect structure, tech stack, domain                    │
│    → Write to findings.md                                    │
│    → Decide: what focused agents to launch next              │
│                                                              │
│  Wave 1: First Deep Pass (N parallel agents)                │
│    → Each agent READS findings.md before starting            │
│    → Each agent returns findings to main Claude              │
│    → Main Claude writes to findings.md (2-Action Rule)       │
│    → Main Claude evaluates: "What questions remain?"         │
│                                                              │
│  Wave 2: Targeted Follow-Up (M agents, informed by Wave 1) │
│    → Missions generated FROM Wave 1 findings                │
│    → Agents READ findings.md (includes Wave 0+1 results)    │
│    → Focus: fill holes, resolve contradictions, go deeper    │
│    → Write to findings.md                                    │
│    → Evaluate again: "Are there still unknowns?"             │
│                                                              │
│  Wave 3+: (Only if significant unknowns remain)             │
│    → Ultra-targeted: 1-2 agents on specific questions        │
│    → Usually not needed — 2 waves covers 90%+ of projects   │
│                                                              │
│  Exit: When findings are comprehensive enough to identify    │
│        gaps, or when additional agents return diminishing     │
│        new information.                                      │
│                                                              │
│  → Then: Gap Identification from accumulated findings        │
└─────────────────────────────────────────────────────────────┘
```

**Key difference from linear research:** Agents in Wave 2 have CONTEXT from Wave 1. They don't repeat work — they deepen it. Wave 1 might discover "there's a complex MCP integration." Wave 2 sends a focused agent to analyze JUST the MCP layer in depth, informed by Wave 1's overview.

#### Wave 0: Quick Scan

Launch 1 Explore agent for a 30-second structural scan:

**Existing System Mode:**
- Detect: primary language, framework, directory structure, configs, entry points
- Count: approximate codebase size
- Detect: problem domain
- Identify: what types of deep research agents to launch in Wave 1

**Greenfield Mode:** Parse the brief/user description instead.

Write initial findings to `findings.md`:
```markdown
# Audit Findings

*Running accumulator. Agents READ this before starting their work.*
*Each wave builds on previous waves' discoveries.*
*Last updated: {timestamp}*

## Wave 0: Quick Scan
<!-- source: quick-scan, confidence: high, wave: 0 -->
- Language: {detected}
- Framework: {detected}
- Codebase size: ~{N} files, ~{M} lines
- Problem domain: {detected}
- Key technologies: {list}
- Open questions for Wave 1: {list of things to investigate}
```

#### Wave 1: First Deep Pass

Launch N parallel agents. Each agent receives:
1. A focused mission (derived from Wave 0)
2. **The current contents of findings.md** (so they know what Wave 0 found)
3. Instruction: "Read findings.md first. Don't duplicate what's already known. Go DEEPER in your specific area."

**Codebase agents (Explore)** — examples, NOT a fixed list:
- Architecture & Request Flow (if web app/API)
- Domain Coupling & Code Boundaries (if multi-module)
- Tools, Integrations & Data Flow (if external services)
- Configuration & Extensibility (if config files)
- Testing & CI/CD (if test infrastructure)
- Dependencies & Framework Analysis (always)
- Database & Data Model (if DB configs)
- Security & Authentication (if auth patterns)

**Ecosystem agents (WebSearch + WebFetch)** — always at least 2:
- Competitor/Alternative Solutions (always)
- Build-vs-Buy Package Research (always — search PyPI/npm/GitHub for packages)
- Framework Latest Features (if existing codebase)
- Domain-Specific Research (industry practices, regulations)
- Academic/Technical Deep Dive (when domain warrants — arxiv, whitepapers)

**After each agent returns:** Append to findings.md with wave metadata:
```markdown
## {Finding Title}
<!-- source: {agent-id}, confidence: {high|medium|low}, topic: {category}, wave: 1 -->

{Finding content}

### Open Questions Raised
- {Question this finding raises that needs deeper investigation}
- {Another question}
```

**CRITICAL: 2-Action Rule** — update findings.md after every 2 agent returns, not after all complete.

**CRITICAL: Do NOT idle while background agents run.** Keep working in the foreground — read prior files, update progress.md, prepare reflection template, draft gap categories. If nothing productive remains, tell the user what you're waiting for and what happens next. Never silently stop generating.

**CRITICAL: Current Year** — all web searches use current year from system context.

#### Reflection Point: What Remains Unknown?

After Wave 1 agents complete, main Claude reads the full findings.md and evaluates:

1. **What questions did Wave 1 raise?** (Look at "Open Questions Raised" sections)
2. **What contradictions exist?** (Agent 2 says X, Agent 5 says Y)
3. **What areas are shallow?** (Only surface-level understanding, no depth)
4. **What ecosystem gaps were discovered but not researched?** (Found a gap but didn't search for packages)
5. **Did any agent discover something that changes the scope?** (e.g., "this isn't just a web app, it's also a data pipeline")

Write the reflection to findings.md:
```markdown
## Wave 1 Reflection
<!-- source: main-claude, wave: 1-reflection -->

### Resolved
- {What we now understand well}

### Open Questions (Drive Wave 2)
- {Question 1 — needs a focused codebase agent}
- {Question 2 — needs a web search agent}
- {Question 3 — needs an academic research agent}

### Contradictions to Resolve
- {Agent X says A, Agent Y says B — needs targeted investigation}

### Decision: {Launch Wave 2 / Proceed to Gaps}
{If open questions are significant → Wave 2. If diminishing returns → proceed.}
```

#### Wave 2: Targeted Follow-Up (If Needed)

Launch M agents — **each mission derived from Wave 1's open questions**:
- Each agent receives findings.md (now includes Wave 0 + Wave 1 + reflection)
- Missions are ultra-targeted: "Investigate specifically whether {X}" or "Resolve contradiction between {A} and {B}"
- Fewer agents than Wave 1 (usually 2-4, not 6-8)

Examples of Wave 2 missions:
- "Wave 1 found an MCP integration but didn't analyze the lifecycle management. Read the MCP-specific files and document the subprocess handling."
- "Wave 1 found 3 competitor platforms. Search for the specific pip packages they use for guardrails — I need package names and versions."
- "Wave 1 identified a data pipeline. Search arxiv for recent papers on {specific technique} that could improve it."
- "Wave 1 agents disagree on whether the auth system is custom or library-based. Read auth-related files and resolve."

After Wave 2, repeat the reflection. Usually 2 waves is sufficient. Continue to Wave 3 only if genuinely significant unknowns remain.

#### Gap Identification (From Accumulated Findings)

When the research loop exits (usually after 2 waves), main Claude reads the FULL findings.md and produces:

**Existing System Mode:**
- `current-state/` files — one per major system aspect discovered
- `gaps/` files — tiered gap analysis (blockers → table stakes → differentiators → nice-to-have)
- Draft list of capabilities needing build-vs-buy evaluation
- Each finding → its own focused file

**Greenfield Mode:**
- `architecture/` draft — initial system design from ecosystem research
- `gaps/` files — what to build vs buy/install
- Draft technology decision list

**Both Modes:**
Each finding gets its own file. DO NOT create mega-files. If a file would exceed ~300 lines, split it.

**CRITICAL — The gap identification ALSO iterates.** After writing gap files, re-read them:
- "Do these gaps suggest areas I should have researched but didn't?"
- "Are there competitor capabilities I missed?"
- "Are there packages that solve these gaps that I didn't search for?"

If yes: launch 1-2 more targeted agents (mini Wave 3), update findings, revise gaps.

### Step 7: Stakeholder Interview (Organic Conversation)

Read `{plugin_root}/references/audit-interview-protocol.md` for the full protocol.

**THIS IS A CONVERSATION, NOT A QUESTIONNAIRE.**

**Round 1 — Present Findings + Expand Scope:**

Show the user what you learned. Summarize key findings in 3-5 sentences. Then PROACTIVELY suggest capabilities or approaches the user may not have considered:

- "State-of-the-art systems in this domain have {X}. Your system doesn't. Want me to evaluate it?"
- "I found {N} packages that solve {problem} you're doing manually. Should I analyze them?"
- "There's active research on {topic} (I found papers on arxiv). Want me to dig deeper?"
- "Most competitors offer {feature}. This isn't in your roadmap. Should it be?"

The goal is to TEACH the user what's possible based on what you've researched, not just ask what they want.

**Round 2 — Follow the Thread:**

React to what the user said. Probe for things research cannot answer:
- Vision and priorities (what matters most NOW)
- Constraints (budget, timeline, team size, politics)
- Stakeholder requirements (what leadership or users are asking for)
- What they'd cut if forced to ship in half the time

**Round 3 (if needed) — Confirm:**
"Let me confirm the scope: [expanded list including things you suggested]. Right?"

**Rules:**
- NEVER ask what the code already told you
- ALWAYS suggest at least 2-3 capabilities the user didn't mention (from competitor/ecosystem research)
- Follow-ups driven by user responses, not a script
- Maximum 3 ROUNDS — could be done in 1 if user gives rich answers
- Write full transcript to `interview.md` including your expansion suggestions and the user's responses

### Step 8: Generate Audit Documents (Parallel Subagents)

Read `{plugin_root}/references/audit-doc-writing.md` for the full protocol.

Determine which files to generate based on everything collected. The file list is DYNAMIC.

**Standard categories (adapt per project — not all are needed for every project):**

```
current-state/  — What exists today (one file per major finding)
gaps/           — What's missing (one file per gap tier)
architecture/   — Target state (one file per architectural concern)
specs/          — Implementation details (only what's actually needed)
operations/     — How to run it (deployment, testing, infra)
strategy/       — Why and what order (competitor research, enablement)
```

Launch parallel audit-doc-writer subagents — one per file:

```
Task(
  subagent_type: "audit-doc-writer",
  prompt: "Read {prompt_file} and execute the instructions."
)
```

Each prompt file provides:
- Relevant sections of findings.md (filtered by topic metadata)
- Interview transcript
- Auto-gaps relevant to their topic
- Focused brief: "Write {filename} covering {specific_topics}"

The SubagentStop hook automatically writes the output to the correct file path.

**Eval-on-Write Quality Gate:** After each subagent returns and the hook writes the file, evaluate the output:

```
Quick evaluation (main Claude or cheap LLM):
  "Score this audit document 1-10 on: completeness, specificity, actionability."
  
  If score < 7: 
    Regenerate with feedback: "The file scored {score}. Issues: {issues}. Rewrite with more depth."
  If score >= 7:
    Accept the file.
```

This prevents shallow/incomplete docs from reaching the user.

**Reflection Nudge:** After every batch of 3-4 docs is written, pause and synthesize:
"Read the docs generated so far. Are there contradictions? Missing cross-references? Gaps between docs?" Fix before continuing.

### Step 9: Generate Build-vs-Buy Analysis (Parallel Subagents)

Read `{plugin_root}/references/audit-build-vs-buy.md` for the full protocol.

For every capability gap where alternatives exist, generate a focused analysis file in `build-vs-buy/`.

Each file evaluates:
1. Available packages (pip/npm/cargo install) — with version, stars, last release, license
2. Available SaaS/managed services — with pricing, integration effort
3. Build custom — effort estimate, maintenance burden
4. **Recommendation** with clear reasoning

Launch parallel subagents — one per capability. Each MUST use WebSearch to find real packages with real version numbers. No invented package names.

### Step 10: Generate Phase Specs (Parallel Subagents)

Read `{plugin_root}/references/audit-phasing.md` for the full protocol.

From gaps + architecture + build-vs-buy analysis, determine:
1. How many phases are needed (could be 3, could be 25)
2. What each phase contains (name derived from the gap it addresses)
3. Dependencies between phases
4. Which phases can run in parallel
5. Milestone grouping (natural shipping points)

Generate:
- `phases/phasing-overview.md` — dependency graph, milestones, timeline
- `phases/P{NN}-{discovered-name}.md` — one per phase

Phase names come from the audit findings. They are NEVER hardcoded. Different projects produce completely different phases.

### Step 11: External LLM Review

Same as deep-plan step 13. Check `review_mode` and follow the appropriate path.

Focus the review on:
- "What gaps did the audit miss?"
- "What should be pip-installed instead of built from scratch?"
- "Are there academic papers or techniques the audit should reference?"
- "Is the phasing order correct? What dependencies are wrong?"
- "What would an experienced engineer push back on?"

### Step 12: User Review

```
AskUserQuestion:
  question: "Audit complete. {count} files generated in {audit_dir}/.
             Review and edit anything, then confirm."
  options: ["Done reviewing", "I have feedback (will type it)"]
```

If feedback: incorporate and regenerate affected files.

### Step 13: Generate README + Output Summary

Generate `{audit_dir}/README.md` — index of all generated files with one-line descriptions and status.

Print:
```
═══════════════════════════════════════════════════════════════
DEEP-DISCOVERY: Complete
═══════════════════════════════════════════════════════════════

Audit Directory: {audit_dir}/
Files Generated: {count}

{category}: {list of files}
...

Next steps:
  1. Review the audit files
  2. Pick a phase to start with
  3. Run: /deep-plan @{audit_dir}/phases/{first-phase}.md
  4. Then: /deep-implement to build it
═══════════════════════════════════════════════════════════════
```

---

## Key Principles

### 1. Research Before Conclusions
Never write an audit finding until you've read the code. Never recommend "build X" until you've searched for packages that do X. Never ask the user what they want until you've shown them what you found.

### 2. Dynamic, Not Hardcoded
The number of research agents, audit files, phases, and build-vs-buy evaluations are ALL determined at runtime based on what's discovered. Nothing is fixed. A 500-line CLI tool gets a different audit than a 50,000-line platform.

### 3. Focused Files, Not Mega-Documents
Each file covers ONE topic. If a file would be 300+ lines, split it. The directory structure is the table of contents. README.md is the index.

### 4. Build-vs-Buy is Granular
Not "should we use {platform}?" but "for THIS specific capability, should we pip install X, subscribe to Y, or build custom?" Real package names, real version numbers, real evaluation.

### 5. Interview Expands, Not Just Clarifies
Present findings first. Suggest capabilities the user didn't ask for based on competitor and ecosystem research. Teach the user what's possible. Follow their thread. Stop when you have enough.

### 6. Findings Accumulate on Disk (2-Action Rule)
Write to findings.md after every 2 subagent returns. Each section gets metadata (source, confidence, topic). If context is lost mid-research, findings survive.

### 7. Eval-on-Write Quality Gate
After each audit doc is generated, score it (completeness, specificity, actionability). Regenerate if below threshold. Don't ship shallow work.

### 8. Reflection Nudges
After every batch of docs, pause to synthesize: check for contradictions, missing cross-references, gaps between docs. Fix before continuing.

### 9. Use Current Date
All web searches use the current year from system context. Never hardcode a year.

### 10. Research Goes Deep
When the domain warrants it, research includes arxiv papers, technical whitepapers, and conference proceedings — not just blog posts and GitHub repos.

### 11. Iterative Refinement, Not One-Shot Generation
Strong solutions are discovered through proposal → testing → revision → progress. The audit is NOT a single pass:
- **Research iterates:** Quick scan → deep scan → gaps identified → MORE targeted research on gaps → refined gaps. If the deep scan reveals something the quick scan missed, launch additional focused agents.
- **Documents iterate:** First draft → eval score → feedback → revision. No document ships after a single generation pass.
- **Phases iterate:** Initial phasing → review against build-vs-buy → reorder/merge/split phases → final phasing. Dependencies discovered late may restructure the entire plan.
- **Interview iterates with the audit:** If later research (ecosystem, build-vs-buy) reveals something that changes the scope, go BACK to the user: "I found something that changes the picture. {description}. Should we adjust scope?"
The audit is a living document set that improves through cycles, not a waterfall of one-shot file generation.

---

## Resuming After Compaction

1. Read progress.md — find current step
2. Read findings.md — recover research context (structured metadata helps filter)
3. Read interview.md — recover stakeholder context
4. ls the audit directory — see what's been generated
5. Resume from first incomplete step

**5-Question Reboot Test:**
1. Where am I? → progress.md current step
2. What's the vision? → interview.md
3. What have I found? → findings.md
4. What have I written? → ls audit directory
5. What's next? → progress.md first unchecked item
