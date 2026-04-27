# Infrastructure Perspectives

domain: infrastructure

## Perspective 1: Infrastructure Security Reviewer
Asks: What is the attack surface of this infrastructure?
- IAM policy scope and least-privilege adherence
- Network segmentation and security group rules
- Secrets management (Vault, SSM, sealed secrets, env vars)
- TLS termination points and certificate management
- Compliance controls (SOC2, HIPAA, PCI) and evidence collection
- Container image vulnerability scanning and base image policy
- Access audit trails and session logging
- Service mesh mTLS and zero-trust implementation

## Perspective 2: IaC Reliability Engineer
Asks: What happens when this infrastructure changes?
- State file management (locking, backend, encryption)
- Drift detection and automated remediation
- Blast radius of changes (resource dependency analysis)
- Rollback strategy for failed deployments
- Module versioning and upgrade path
- Environment parity (dev, staging, prod) and configuration drift
- Resource tagging standards and enforcement
- Import strategy for existing unmanaged resources

## Perspective 3: Cost & Capacity Planner
Asks: Are we paying for what we use? Will it scale?
- Resource right-sizing and utilization monitoring
- Auto-scaling configuration and thresholds
- Reserved vs on-demand vs spot allocation strategy
- Cost allocation tags and per-team attribution
- Unused resource detection and cleanup automation
- Cross-region replication costs and necessity
- Data transfer costs between services and regions
- Budget alerts, thresholds, and anomaly detection
