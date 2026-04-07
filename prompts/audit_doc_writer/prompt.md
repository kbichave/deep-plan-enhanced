## Task

Generate content for: `{DOC_TITLE}`
Output filename: `{DOC_FILENAME}`

## Current Date

The current year is {CURRENT_YEAR}. Use this in ALL web search queries. Never hardcode a different year.

## Context Files to Read

Read these files completely before generating content:

{CONTEXT_FILES_LIST}

## Focus

{SPECIFIC_BRIEF}

## Constraints

- **Length:** Maximum ~300 lines. If the content would be longer, focus on the most important aspects and note what was omitted.
- **Specificity:** Name files, functions, packages, versions — not vague descriptions. If you reference a package, verify it exists via WebSearch.
- **Cross-references:** Reference other audit files by relative path: `See ../gaps/tier1-blockers.md`
- **Quantitative data:** Include line counts, file counts, percentages, star counts where relevant.
- **Actionability:** Someone should be able to act on this document without asking follow-up questions.
- **Build-vs-buy:** If this is a build-vs-buy analysis file, you MUST search PyPI/npm/GitHub for real packages. Do not invent package names.

## Output

Output ONLY the raw markdown content for this document. No JSON wrapper. No code fences around the entire output. No preamble like "Here is the document:".

The SubagentStop hook will automatically write your output to:
`{AUDIT_DIR}/{DOC_FILENAME}`
