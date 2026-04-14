"""Task definitions and generation for deep-plan workflow.

Replaces the legacy TodoWrite system with Claude Code Tasks (v2.1.16+).
Provides native dependency tracking, persistence, and subagent visibility.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskDefinition:
    """Definition of a workflow task."""

    subject: str
    description: str
    active_form: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output."""
        return {
            "subject": self.subject,
            "description": self.description,
            "activeForm": self.active_form,
        }


# Maximum concurrent subagents supported by Claude Code
BATCH_SIZE = 7

# Task IDs mapped to workflow step numbers
# Steps 0-4 are setup (not tracked as tasks)
# Steps 6-22 are the main workflow
TASK_IDS: dict[int, str] = {
    6: "research-decision",
    7: "execute-research",
    8: "detailed-interview",
    9: "save-interview",
    10: "write-spec",
    11: "generate-plan",
    12: "context-check-pre-review",
    13: "external-review",
    14: "integrate-feedback",
    15: "user-review",
    16: "apply-tdd",
    17: "context-check-pre-split",
    18: "create-section-index",
    19: "generate-section-tasks",
    20: "write-sections",
    21: "final-verification",
    22: "output-summary",
}

# Reverse mapping for lookup
TASK_ID_TO_STEP: dict[str, int] = {v: k for k, v in TASK_IDS.items()}

# Step names for display
STEP_NAMES: dict[int, str] = {
    0: "Context check",
    1: "Print intro and validate environment",
    2: "Handle environment errors",
    3: "Validate spec file input",
    4: "Setup planning session",
    6: "Research decision",
    7: "Execute research",
    8: "Detailed interview",
    9: "Save interview transcript",
    10: "Write initial spec",
    11: "Generate implementation plan",
    12: "Context check (pre-review)",
    13: "External LLM review",
    14: "Integrate external feedback",
    15: "User review of integrated plan",
    16: "Apply TDD approach",
    17: "Context check (pre-split)",
    18: "Create section index",
    19: "Generate section tasks",
    20: "Write section files",
    21: "Final status and cleanup",
    22: "Output summary",
}

# Explicit dependency graph (replaces step ordering)
# Each task lists the task IDs it is blocked by
TASK_DEPENDENCIES: dict[str, list[str]] = {
    # Context items - each blocked by final step, stays visible throughout workflow
    # Values are stored in subject field for visibility after compaction
    "context-plugin-root": ["output-summary"],
    "context-planning-dir": ["output-summary"],
    "context-initial-file": ["output-summary"],
    "context-review-mode": ["output-summary"],
    # Main workflow
    "research-decision": [],  # Can start immediately
    "execute-research": ["research-decision"],
    "detailed-interview": ["execute-research"],  # Depends on research (even if skipped)
    "save-interview": ["detailed-interview"],
    "write-spec": ["save-interview"],
    "generate-plan": ["write-spec"],
    "context-check-pre-review": ["generate-plan"],
    "external-review": ["context-check-pre-review"],
    "integrate-feedback": ["external-review"],
    "user-review": ["integrate-feedback"],
    "apply-tdd": ["user-review"],
    "context-check-pre-split": ["apply-tdd"],
    "create-section-index": ["context-check-pre-split"],
    "generate-section-tasks": ["create-section-index"],
    "write-sections": ["generate-section-tasks"],
    "final-verification": ["write-sections"],
    "output-summary": ["final-verification"],
}

# Task definitions with subject, description, and activeForm
# Note: Context tasks are NOT in this dict - they're generated dynamically
# with values in the subject field by create_context_tasks()
TASK_DEFINITIONS: dict[str, TaskDefinition] = {
    "research-decision": TaskDefinition(
        subject="Research Decision",
        description="Read research-protocol.md and decide on research approach",
        active_form="Deciding on research approach",
    ),
    "execute-research": TaskDefinition(
        subject="Execute Research",
        description="Launch research subagents based on decisions from previous step",
        active_form="Executing research",
    ),
    "detailed-interview": TaskDefinition(
        subject="Detailed Interview",
        description="Read interview-protocol.md and conduct stakeholder interview",
        active_form="Conducting detailed interview",
    ),
    "save-interview": TaskDefinition(
        subject="Save Interview Transcript",
        description="Write Q&A to claude-interview.md",
        active_form="Saving interview transcript",
    ),
    "write-spec": TaskDefinition(
        subject="Write Initial Spec",
        description="Combine input, research, and interview into claude-spec.md",
        active_form="Writing initial spec",
    ),
    "generate-plan": TaskDefinition(
        subject="Generate Implementation Plan",
        description="Create detailed plan in claude-plan.md. Write for unfamiliar reader.",
        active_form="Generating implementation plan",
    ),
    "context-check-pre-review": TaskDefinition(
        subject="Context Check (Pre-Review)",
        description="Run check-context-decision.py before external review",
        active_form="Checking context (pre-review)",
    ),
    "external-review": TaskDefinition(
        subject="External LLM Review",
        description="Read external-review.md and run review based on review_mode",
        active_form="Running external LLM review",
    ),
    "integrate-feedback": TaskDefinition(
        subject="Integrate External Feedback",
        description="Apply substantive review feedback directly to claude-plan.md",
        active_form="Integrating external feedback",
    ),
    "user-review": TaskDefinition(
        subject="User Review of Integrated Plan",
        description="Wait for user to review and approve claude-plan.md",
        active_form="Waiting for user review",
    ),
    "apply-tdd": TaskDefinition(
        subject="Apply TDD Approach",
        description="Read tdd-approach.md and create claude-plan-tdd.md",
        active_form="Applying TDD approach",
    ),
    "context-check-pre-split": TaskDefinition(
        subject="Context Check (Pre-Split)",
        description="Run check-context-decision.py before section splitting",
        active_form="Checking context (pre-split)",
    ),
    "create-section-index": TaskDefinition(
        subject="Create Section Index",
        description="Read section-index.md and create sections/index.md with SECTION_MANIFEST",
        active_form="Creating section index",
    ),
    "generate-section-tasks": TaskDefinition(
        subject="Generate Section Tasks",
        description="Run generate-section-tasks.py to get batch task operations",
        active_form="Generating section tasks",
    ),
    "write-sections": TaskDefinition(
        subject="Write Section Files",
        description="Read section-splitting.md and execute batch loop with subagents",
        active_form="Writing section files",
    ),
    "final-verification": TaskDefinition(
        subject="Final Verification",
        description="Run check-sections.py to verify all sections complete",
        active_form="Running final verification",
    ),
    "output-summary": TaskDefinition(
        subject="Output Summary",
        description="Print generated files and next steps",
        active_form="Outputting summary",
    ),
}


# ============================================================================
# AUDIT WORKFLOW DEFINITIONS
# ============================================================================

# Task IDs for audit workflow steps
# Steps 1-3 are setup (not tracked as tasks)
# Steps 4-15 are the main audit workflow (4, 4.5, 5, 5.5 added for topic + coverage steps)
AUDIT_TASK_IDS: dict[int, str] = {
    4: "quick-scan",
    5: "topic-enumeration",
    6: "deep-research",
    7: "coverage-validation",
    8: "auto-gaps",
    9: "stakeholder-interview",
    10: "generate-audit-docs",
    11: "generate-build-vs-buy",
    12: "generate-phase-specs",
    13: "external-review",
    14: "user-review",
    15: "output-summary",
}

AUDIT_TASK_ID_TO_STEP: dict[str, int] = {v: k for k, v in AUDIT_TASK_IDS.items()}

AUDIT_STEP_NAMES: dict[int, str] = {
    0: "Context check",
    1: "Validate environment",
    2: "Detect audit mode",
    3: "Setup session",
    4: "Quick scan",
    5: "Topic enumeration (research coverage manifest)",
    6: "Deep research (topic-assigned parallel subagents)",
    7: "Coverage validation (gap agents for uncovered topics)",
    8: "Auto gap identification",
    9: "Stakeholder interview",
    10: "Generate audit documents",
    11: "Generate build-vs-buy analysis",
    12: "Generate phase specs",
    13: "External LLM review",
    14: "User review",
    15: "Output summary",
}

AUDIT_TASK_DEPENDENCIES: dict[str, list[str]] = {
    # Context items
    "context-plugin-root": ["output-summary"],
    "context-planning-dir": ["output-summary"],
    "context-initial-file": ["output-summary"],
    "context-review-mode": ["output-summary"],
    # Main audit workflow — topic enumeration is the coverage contract before research
    "quick-scan": [],
    "topic-enumeration": ["quick-scan"],
    "deep-research": ["topic-enumeration"],       # agents now assigned specific topics
    "coverage-validation": ["deep-research"],     # gap agents for uncovered topics
    "auto-gaps": ["coverage-validation"],
    "stakeholder-interview": ["auto-gaps"],       # interview AFTER research (research-first)
    "generate-audit-docs": ["stakeholder-interview"],
    "generate-build-vs-buy": ["generate-audit-docs"],  # needs audit docs for context
    "generate-phase-specs": ["generate-build-vs-buy"],  # needs build-vs-buy decisions
    "external-review": ["generate-phase-specs"],
    "user-review": ["external-review"],
    "output-summary": ["user-review"],
}

AUDIT_TASK_DEFINITIONS: dict[str, TaskDefinition] = {
    "quick-scan": TaskDefinition(
        subject="Quick Scan",
        description="Read audit-research-protocol.md. Launch 1 Explore agent for structural scan. Detect tech stack, domain, size. Write scan-summary.md.",
        active_form="Running quick codebase scan",
    ),
    "topic-enumeration": TaskDefinition(
        subject="Topic Enumeration",
        description="Read audit-topic-enumeration.md. Simulate 3 perspectives (security auditor, new engineer, PM). Generate research-topics.yaml with 12-20 topics, each with id/category/priority/questions.",
        active_form="Enumerating research topics",
    ),
    "deep-research": TaskDefinition(
        subject="Deep Research",
        description="Read audit-research-protocol.md and research-topics.yaml. Assign 2-3 topics per agent. Each agent writes findings/<topic-id>-<slug>.md answering its assigned questions.",
        active_form="Running topic-assigned parallel research",
    ),
    "coverage-validation": TaskDefinition(
        subject="Coverage Validation",
        description="Read audit-coverage-validation.md. Run validate-coverage.py. Spawn gap agents for uncovered topics. Loop until coverage ≥ 80% or no more topics can be covered.",
        active_form="Validating research coverage",
    ),
    "auto-gaps": TaskDefinition(
        subject="Auto Gap Identification",
        description="Read all findings/<topic-id>-*.md files. Write current-state/ and gaps/ files. Draft build-vs-buy list from coverage findings.",
        active_form="Identifying gaps from research",
    ),
    "stakeholder-interview": TaskDefinition(
        subject="Stakeholder Interview",
        description="Read audit-interview-protocol.md. Present coverage map (research-topics.yaml), expand scope, follow thread. Write interview.md.",
        active_form="Conducting stakeholder interview",
    ),
    "generate-audit-docs": TaskDefinition(
        subject="Generate Audit Documents",
        description="Read audit-doc-writing.md. Launch parallel audit-doc-writer subagents. Eval-on-write quality gate.",
        active_form="Generating audit documents",
    ),
    "generate-build-vs-buy": TaskDefinition(
        subject="Generate Build-vs-Buy Analysis",
        description="Read audit-build-vs-buy.md. Launch parallel subagents to evaluate pip/npm/SaaS for each capability.",
        active_form="Generating build-vs-buy analysis",
    ),
    "generate-phase-specs": TaskDefinition(
        subject="Generate Phase Specs",
        description="Read audit-phasing.md. Discover phases from gaps. Generate phasing-overview.md + per-phase specs.",
        active_form="Generating phase specifications",
    ),
    "external-review": TaskDefinition(
        subject="External LLM Review",
        description="Read external-review.md. Focus: missing gaps, wrong build-vs-buy, phasing errors.",
        active_form="Running external LLM review",
    ),
    "user-review": TaskDefinition(
        subject="User Review",
        description="Present audit directory to user for review and feedback.",
        active_form="Waiting for user review",
    ),
    "output-summary": TaskDefinition(
        subject="Output Summary",
        description="Generate README.md index. Print file listing and next steps.",
        active_form="Outputting summary",
    ),
}


