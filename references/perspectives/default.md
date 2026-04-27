# Default Perspectives

domain: default

## Perspective 1: Security Auditor
Asks: What can go wrong? What is exposed?
- Authentication and authorization mechanisms
- Session management and token handling
- Input validation and injection vectors (SQL, command, XSS)
- Secrets management (hardcoded credentials, env vars, vault)
- Dependency vulnerabilities (known CVEs)
- Data encryption at rest and in transit
- Audit logging and access trails
- Path traversal and file handling risks

## Perspective 2: New Engineer Onboarding
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

## Perspective 3: Product Manager / Operator
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
