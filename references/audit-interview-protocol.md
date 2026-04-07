# Audit Interview Protocol

Defines the stakeholder interview for deep-discovery step 7. This is a CONVERSATION that expands the user's thinking, not a questionnaire that extracts answers.

## Core Philosophy

The interview has three jobs:
1. **Validate** — confirm research findings match reality
2. **Expand** — suggest capabilities the user didn't ask for (teach what's possible)
3. **Extract** — get vision, priorities, constraints that research can't answer

The tool should be SMARTER than the user about what's available in the ecosystem. After deep research (step 5), it knows what competitors do, what packages exist, what academic research says. The interview surfaces this knowledge to expand scope.

---

## Round 1: Present Findings + Expand Scope

### Present (Show Homework)

Summarize what research found in 3-5 sentences. Include key numbers:

```
"I've analyzed {the codebase / your brief}. Here's what I found:

{For existing system:}
- {N} files, ~{M}K lines of {language} using {framework}
- {X} structural problems detected (biggest: {description})
- {Y} ecosystem alternatives found
- {Z} packages that could replace custom code you're maintaining

{For greenfield:}
- {N} existing solutions found that solve parts of this problem
- {M} frameworks evaluated for this domain
- {Z} papers/techniques relevant to your approach

Does this match your understanding? What am I missing?"
```

### Expand (Go Beyond Human)

Immediately after presenting, suggest 2-4 things the user DIDN'T ask for but SHOULD consider. These come directly from ecosystem research:

**Pattern: Competitor Capability Gap**
```
"I noticed that {N} of the {M} alternatives I researched all offer {capability}.
Your system doesn't have this. It's becoming an industry standard.
Should I include it in the roadmap?"
```

**Pattern: Package Replacement**
```
"You're maintaining {N} lines of custom code for {function}.
I found {package_name} ({stars} stars, last released {date}) that does the same thing.
Want me to do a detailed build-vs-buy analysis on this?"
```

**Pattern: Academic Insight**
```
"There's active research on {topic} — I found {N} recent papers.
The most relevant one ({title}, {year}) proposes {technique} that could
improve your {aspect} by {claimed improvement}.
Want me to dig deeper into this?"
```

**Pattern: Infrastructure Modernization**
```
"Your deployment uses {current_approach}. Current best practice has shifted to {modern_approach}.
{Concrete benefit}. Should I evaluate the migration cost?"
```

**Pattern: Missing Capability**
```
"Most systems in this space have {capability} — things like {examples}.
You don't have this today. Depending on your user base, this could be
table-stakes or nice-to-have. Want me to scope it?"
```

### How to Decide What to Suggest

Look at findings.md for:
- Competitor features that the current system lacks
- Packages found during build-vs-buy research that replace custom code
- Academic techniques that apply to the domain
- Infrastructure patterns more modern than what's deployed
- Capabilities that ALL competitors have (table stakes the user may not realize they need)

Suggest the 2-4 most impactful ones. Don't overwhelm — pick the ones where the delta between current state and best practice is largest.

---

## Round 2: Follow the Thread

The user's response to Round 1 determines Round 2 entirely. There is NO predetermined list of questions.

### If User Confirms + Adds Detail
```
User: "Yeah that's right, and we also need to support multi-tenancy"
→ "Tell me more about the multi-tenancy requirement. How many tenants?
   What isolation level — shared DB with row-level, or separate schemas?"
→ Probe: who needs this, by when, what's the minimum viable version
```

### If User Corrects Something
```
User: "No, we don't use that framework anymore, we migrated to X"
→ "Got it — I'll adjust my findings. When did you migrate? Is the migration complete?"
→ "Does the new framework change any of the gaps I identified?"
```

### If User Expands Scope
```
User: "Actually we're also thinking about adding a mobile app"
→ "Interesting — that changes the architecture significantly. 
   Should I research mobile frameworks and how they'd integrate?"
→ "Would the mobile app consume the same API, or does it need its own?"
```

### If User Narrows Scope
```
User: "We don't care about that, we just need the core to work"
→ "Understood. What's 'the core' in your mind? The top 3 things."
→ "If you had to ship in 2 months, what would you cut?"
```

### Probing for What Research Can't Answer

These are the things you SHOULD ask — they require human judgment:

- **Priorities:** "Of everything we've discussed, what would you tackle first?"
- **Constraints:** "Any hard constraints? Budget ceiling? Team size? Deadline?"
- **Politics:** "Are there teams or stakeholders who would resist any of these changes?"
- **Timeline:** "What's realistic — 3 months? 6 months? A year?"
- **Users:** "Who actually uses this system today? Who will use it after the changes?"
- **Risk tolerance:** "Are you comfortable with breaking changes, or does everything need to be backward-compatible?"

Only ask these if they haven't already been answered by the user's earlier responses.

---

## Round 3: Confirm (If Needed)

Only needed if the conversation surfaced significant scope changes:

```
"Let me summarize what I'll include in the audit:

Vision: {1-2 sentences}
Scope: {what's in}
Out of scope: {what's explicitly out}
Priorities: {ordered list}
Constraints: {budget, timeline, team}
Expanded capabilities: {things you suggested that user accepted}

Is this right? Anything to add or remove?"
```

If the user confirmed everything in Rounds 1-2, skip Round 3.

---

## Rules

1. **NEVER ask what the code already told you.** If you know the framework, don't ask "what framework do you use?"
2. **ALWAYS suggest at least 2 capabilities the user didn't mention.** These come from competitor research, package discovery, or academic findings.
3. **Follow-ups are driven by user responses, not a script.** If the user mentions something unexpected, follow that thread.
4. **Maximum 3 ROUNDS** — could be done in 1 if user gives rich answers with clear vision.
5. **Write full transcript to interview.md** including your suggestions and the user's responses to them.
6. **If later research changes the picture, come BACK to the user.** The interview isn't a one-time event if step 9 (build-vs-buy) reveals something significant.

---

## Anti-Patterns (What NOT To Do)

| Anti-Pattern | Why It's Wrong | What To Do Instead |
|---|---|---|
| "What's your tech stack?" | You already know from research | "I see you're using {X}. Is that the production setup?" |
| "Are there any problems?" | You already found them | "I found {N} problems. Which hurts most?" |
| "What features do you want?" | Too generic, lazy | "Competitors have {X,Y,Z}. Which of these matter?" |
| Asking exactly 6 questions | Feels robotic | Ask what's needed, stop when you have enough |
| Asking the same questions regardless of project | One-size-fits-all | Tailor to what research found |
| Not suggesting anything new | Just a passive listener | Teach the user what's possible based on research |
| Ignoring user's tangent | Miss important context | Follow every thread, then redirect if needed |

---

## Output: interview.md

```markdown
# Stakeholder Interview

**Date:** {date}
**Mode:** {Existing System | Greenfield}
**Duration:** {rounds} rounds

## Round 1: Findings Presentation + Scope Expansion

**Auditor:** {summary of findings presented}

**Expansion suggestions:**
1. {suggestion 1} — User response: {accepted/declined/modified}
2. {suggestion 2} — User response: {accepted/declined/modified}
3. {suggestion 3} — User response: {accepted/declined/modified}

**User:** {verbatim response}

## Round 2: Follow-Up

{Q&A driven by Round 1 responses}

## Round 3: Confirmation (if needed)

{Final scope confirmation}

## Captured Context

- **Vision:** {1-2 sentences}
- **Priorities:** {ordered}
- **Constraints:** {budget, timeline, team, politics}
- **Expanded scope:** {capabilities added from suggestions}
- **Out of scope:** {explicitly excluded}
- **Stakeholder requirements:** {if any}
```
