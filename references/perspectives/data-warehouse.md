# Data Warehouse Perspectives

domain: data-warehouse

## Perspective 1: Analytics Engineer / Modeler
Asks: Is the transformation logic correct and maintainable?
- Model layering strategy (staging, intermediate, marts) and naming conventions
- Grain documentation (what does one row represent in each model)
- Slowly changing dimension handling (SCD type 1, 2, or snapshots)
- Incremental vs full-refresh strategy per model
- Schema naming conventions and model organization
- Model dependencies and DAG structure (ref/source usage)
- Source freshness configuration and monitoring
- Materialization strategy (view, table, incremental, ephemeral)

## Perspective 2: Data Quality Engineer
Asks: How do we know the data is correct? What can go wrong silently?
- Data validation tests (not-null, unique, accepted-values, relationships)
- Anomaly detection for volume, distribution, and freshness
- Data contracts with upstream sources (schema agreements, SLAs)
- Schema change handling and backward compatibility
- Row count monitoring and alerting thresholds
- Freshness SLAs per model and alerting when breached
- Cross-database consistency checks (source vs warehouse)
- Documentation coverage for models and columns

## Perspective 3: Data Consumer / Analyst
Asks: Can I find and trust the data I need?
- Model discoverability (catalog, search, documentation site)
- Metric definitions and consistency across reports
- Query performance on common access patterns
- Data dictionary completeness (column descriptions, business definitions)
- Historical data availability and retention policy
- Self-service access patterns (who can query what)
- Dashboard refresh latency and staleness indicators
- Known data caveats and limitations documented per model
