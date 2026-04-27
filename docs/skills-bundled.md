# Bundled Skills

`deep-plan-enhanced` vendors a curated subset of
[mattpocock/skills](https://github.com/mattpocock/skills) (MIT). Full
attribution and the upstream license text live in
[`NOTICE`](../NOTICE).

The seven vendored skills sit alongside `skills/deep/` and are
auto-discovered by Claude Code — no extra registration is required.

| Skill | Auto-invoked by `/deep` | Manually invocable | Notes |
|---|---|---|---|
| `grill-me` | Yes — drives every interview round in `/deep plan` and `/deep discovery`. | `/grill-me` for ad-hoc plan stress-tests. | Sequential decision-tree walk with recommended answers. |
| `tdd` | No — its principles feed `references/coding-standards.md` and `agents/section-writer.md`. | `/tdd` for standalone TDD work outside `/deep`. | Tracer-bullet cadence, anti-horizontal-slice. |
| `ubiquitous-language` | Yes — added as an always-on audit topic during `/deep discovery`. | `/ubiquitous-language` for ad-hoc glossary extraction. | Output flows through `scripts/lib/glossary.py` and the vault curator. |
| `improve-codebase-architecture` | Yes — `/deep plan` runs a lightweight audit and offers to fold a deepening into the plan; `/deep implement` warns when a section overlaps an audit candidate. | `/improve-codebase-architecture` for standalone audits. | Shares vocabulary with `references/coding-standards.md`. |
| `obsidian-vault` | Yes — invoked by the `vault-curator` subagent at end of every mode. | `/obsidian-vault` for direct note management. | Backing store for the knowledge vault. |
| `write-a-skill` | No. | `/write-a-skill` for extending the plugin with new skills. | Meta-skill. |
| `zoom-out` | No. | `/zoom-out` for strategic step-back during long `/deep auto` runs. | Strategic reframing. |

## Slash commands

Each vendored skill exposes its standard upstream slash command. The
plugin does not rename them. If two skills share a name (the plugin's
own `deep` skill and a user-installed one), Claude Code's resolution
order is **project > plugin > user**.

## Cross-references in protocol files

The vendored skills are also cited from existing `references/` files
to keep `/deep`'s in-flow prompts sharp:

* `references/interview-protocol.md` and
  `references/audit-interview-protocol.md` make the `grill-me`
  sequential walk the default interview style.
* `references/coding-standards.md` cites `tdd` for the tracer-bullet
  rule and `request-refactor-plan` for tiniest-possible-commit shape.
* `references/audit-topic-enumeration.md` adds `ubiquitous-language`
  as an always-on topic.
* `references/plan-writing.md` cites `improve-codebase-architecture`
  and `tdd/deep-modules.md` for module-design-first guidance.
* `references/audit-research-protocol.md` documents the
  architecture-audit run and where its output lands.
* `agents/section-writer.md` and `agents/opus-plan-reviewer.md` cite
  `tdd` for cadence and `request-refactor-plan` for vertical-slice
  integrity.

These citations are surgical — no upstream content is copied into the
references; the references point at the vendored `SKILL.md` files
inside this plugin.
