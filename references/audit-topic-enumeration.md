# Audit Topic Enumeration

Generates the research coverage manifest (`research-topics.yaml`) that acts as the topic contract for all subsequent research agents. Done after Quick Scan, before Deep Research.

## Purpose

Without a topic contract, research agents write what they find interesting rather than what the audit needs. STORM research showed that outline-first enumeration improves topic breadth coverage by 25%. This step is that outline.

## Step 1: Read scan-summary.md

Read `{planning_dir}/scan-summary.md` (written by Quick Scan). Extract:
- Project type and domain
- Primary language(s) and framework(s)
- Rough scale (files, lines, services)
- Any obviously missing areas flagged by the scan

Also check `{planning_dir}/objective.md` if it exists (from inline prompt auto-spec).

## Step 2: Check for Prior Research (MemPalace, if available)

If the `mempalace_search` MCP tool is available:
1. Call `mempalace_search` with 2–3 key terms from the project domain (e.g. "authentication Python API")
2. Filter results where room = "research-topics"
3. Review returned topics — mark any that are directly relevant as candidates
4. These become suggested topics in the manifest (with `source: prior_project`)

This avoids re-researching what you already know from other projects.

## Step 3: Simulate Three Perspectives

Generate topic questions from three distinct viewpoints. Each perspective asks different questions — their union becomes the topic manifest.

### Perspective 1: Security Auditor
Asks: What can go wrong? What is exposed?
- Authentication and authorization mechanisms
- Session management and token handling
- Input validation and injection vectors (SQL, command, XSS)
- Secrets management (hardcoded credentials, env vars, vault)
- Dependency vulnerabilities (known CVEs)
- Data encryption at rest and in transit
- Audit logging and access trails
- Path traversal and file handling risks

### Perspective 2: New Engineer Onboarding
Asks: How do I understand this system?
- Project structure and entry points
- Data model and database schema
- Core business logic and domain entities
- API surface (internal and external)
- Configuration management
- Local development setup
- Testing infrastructure and coverage
- Error handling and logging conventions
- Background jobs and async processing
- Inter-service communication patterns

### Perspective 3: Product Manager / Operator
Asks: How does this run in production? What breaks?
- Deployment pipeline and environments
- Observability: metrics, logging, alerting, tracing
- Performance characteristics and bottlenecks
- Scalability constraints and known limits
- Feature flag / rollout infrastructure
- SLA/SLO definitions and breach handling
- Operational runbooks and incident process
- Data retention and backup policies
- User-facing error handling and recovery

## Step 4: Build the Manifest

1. Collect all questions from all three perspectives
2. Group similar questions under a single topic (dedup)
3. Assign each topic:
   - `id`: `rt-NN` (two-digit, e.g. `rt-01`)
   - `topic`: short descriptive name (3–6 words)
   - `category`: one of `architecture | data-model | api | security | performance | testing | observability | dependencies | deployment`
   - `priority`: `high` (core to identifying gaps), `medium` (supporting), `low` (nice-to-know)
   - `questions`: 2–4 specific questions the research agent must answer
   - `status`: `pending`
   - `findings_file`: `null`

Target **12–20 topics** for a typical project. Fewer for tiny projects, more for large distributed systems.

## Step 5: Write research-topics.yaml

Write to `{planning_dir}/research-topics.yaml`:

```yaml
metadata:
  project: <project name from scan-summary>
  generated: <ISO date>
  perspectives:
    - security_auditor
    - new_engineer
    - product_manager
  total: <N>
  covered: 0
  coverage_pct: 0

topics:
  - id: rt-01
    topic: "Authentication & Authorization"
    category: security
    priority: high
    questions:
      - "What authentication mechanism is used (JWT, sessions, OAuth)?"
      - "How are permissions enforced? Is there RBAC or ABAC?"
      - "What happens when a token expires or is revoked?"
    status: pending
    findings_file: null

  - id: rt-02
    topic: "Database Schema & Migrations"
    category: data-model
    priority: high
    questions:
      - "What is the primary data store? What is the schema structure?"
      - "How are migrations managed? Is there a rollback strategy?"
      - "Are there N+1 query risks or missing indexes?"
    status: pending
    findings_file: null

  # ... continue for all topics
```

## Rules

1. **Do not skip categories** — every category should have at least one topic unless the project genuinely has nothing in that area (e.g. a CLI tool has no deployment category — mark it explicitly as N/A in metadata).
2. **Questions must be specific and answerable** — not "How does security work?" but "What input validation exists at API boundaries?".
3. **Priority is about gap-finding impact**, not importance to the project. Security topics are often high priority even for small projects because they're commonly missed.
4. **Prior-project topics** (from MemPalace) should be reviewed critically — mark them `source: prior_project` in a notes field and verify they apply to this codebase before including.
