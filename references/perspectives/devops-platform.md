# DevOps Platform Perspectives

domain: devops-platform

## Perspective 1: Pipeline Reliability Engineer
Asks: What happens when the pipeline breaks?
- Pipeline failure modes and automatic retry logic
- Secret injection mechanism (vault, OIDC, environment scoping)
- Artifact caching strategy and cache invalidation
- Parallel execution and resource contention management
- Pipeline-as-code structure and reusability (templates, shared workflows)
- Environment promotion gates (manual approval, automated checks)
- Rollback trigger conditions and automated rollback support
- Deployment verification (smoke tests, canary analysis, health checks)

## Perspective 2: Platform Security Reviewer
Asks: What can an attacker do through the pipeline?
- CI/CD secret scoping (repo-level, org-level, environment-level)
- Supply chain security (signed commits, SLSA levels, SBOM generation)
- Runner isolation (shared vs dedicated, container sandboxing)
- Image registry access controls and image signing
- Deployment approval workflows and separation of duties
- Audit logging of all deployments and configuration changes
- Third-party action and plugin vetting process
- Credential rotation automation and emergency revocation

## Perspective 3: Developer Experience Engineer
Asks: Does this platform help or hinder developer productivity?
- Pipeline execution time and optimization opportunities
- Local reproducibility of CI steps (can developers run CI locally)
- Flaky test detection, quarantine, and reporting
- Branch protection rules and merge requirements
- PR feedback loop time (time from push to first CI result)
- Self-service environment provisioning (preview envs, ephemeral envs)
- Documentation of pipeline customization and extension points
- Onboarding friction for new repositories
