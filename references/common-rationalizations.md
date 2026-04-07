# Common Rationalizations

LLMs (and humans) rationalize shortcuts during implementation. This reference catalogs the most frequent rationalizations encountered during deep-plan and deep-implement workflows, along with the correct response.

Read this file when you catch yourself thinking any of these thoughts.

---

## The Rationalizations

| Rationalization | Why It Feels Right | Why It Is Wrong | Correct Action |
|----------------|-------------------|-----------------|----------------|
| "I'll just do a quick implementation to show the pattern" | Concrete code feels more helpful than prose | The plan is a blueprint, not a building. Writing implementation code wastes tokens and does deep-implement's job. | Write the function signature with a docstring. Describe the algorithm in prose. Stop there. |
| "This section is simple enough to skip tests for" | The logic seems obvious | Simple code gets refactored into complex code. The test documents the contract. Without it, the next change has no safety net. | Write the test stub first. Even a one-line assertion establishes the expected behavior. |
| "I'll combine these two sections since they're related" | Fewer sections means faster completion | Combined sections are harder to review, harder to parallelize, and harder to resume if interrupted. Each section should be independently implementable. | Keep sections separate. If they share setup code, extract it into a shared fixture or utility. |
| "The reference file says X but I know a better way" | Your approach might genuinely be better | The reference file captures decisions made with full context during planning. Overriding it during implementation loses that context and creates drift between plan and code. | Follow the reference file. If it is genuinely wrong, note the disagreement and flag it -- do not silently deviate. |
| "I'll add this feature while I'm in here" | Incremental cost seems low | Unplanned features have unplanned edge cases, unplanned tests, and unplanned interactions. They also make the diff harder to review. | Finish the current task. File the new idea as a separate item. |
| "I'll clean up the error handling later" | Getting the happy path working first feels productive | "Later" never comes. Error handling discovered during implementation reflects real failure modes. Deferring it means rediscovering those failure modes. | Handle errors as you encounter them. If you write a network call, write the timeout and retry logic in the same pass. |
| "This dependency is fine to add, it's just one small library" | The library solves the problem cleanly | Every dependency is a maintenance commitment: version conflicts, security patches, API changes, install complexity. For a plugin that installs via `claude plugin add`, each dep raises the adoption barrier. | Check if stdlib can do it. If not, document the tradeoff explicitly in the plan. |
| "I'll just copy this pattern from the other module" | Consistency with existing code | If you are copying more than a function signature, you are duplicating logic. Duplicated logic means duplicated bugs and divergent fixes. | Extract the shared logic into a common module. Import it from both places. |
| "The plan doesn't mention this edge case, so I'll skip it" | Following the plan exactly as written | The plan cannot enumerate every edge case. If you discover one during implementation, handling it IS following the plan's intent. | Handle the edge case. Add a test for it. Note it in the section file so reviewers see it. |
| "I need to refactor this first before I can implement the feature" | Clean code is easier to extend | Refactoring and feature work in the same change makes both harder to review and harder to revert. It also risks breaking existing behavior while adding new behavior. | Implement the feature in the current structure. File the refactor as a separate task. Or do the refactor first as its own commit, then add the feature. |

---

## How to Use This File

1. **During plan writing**: Review this list to ensure your plan does not accidentally encourage any of these patterns. For example, if your plan lacks anti-goals, implementers will rationalize scope creep.

2. **During implementation**: If you catch yourself thinking one of these thoughts, stop. Re-read the "Correct Action" column. Then proceed.

3. **During review**: If a section submission exhibits one of these patterns, reference the specific row in this table when requesting changes.
