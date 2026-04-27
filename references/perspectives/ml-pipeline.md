# ML Pipeline Perspectives

domain: ml-pipeline

## Perspective 1: ML Engineer / Model Evaluator
Asks: Can I trust these models and reproduce these results?
- Model training reproducibility (seeds, versioned data, deterministic pipelines)
- Experiment tracking and hyperparameter management (MLflow, W&B, etc.)
- Evaluation metrics and validation strategy (train/val/test split integrity)
- Model versioning and registry (how are models stored, tagged, promoted)
- Feature engineering pipeline (transformations, feature stores, drift detection)
- Model serving architecture (batch vs real-time, latency requirements)
- Data versioning and lineage (DVC, delta tables, snapshot strategy)
- Model interpretability and explainability (SHAP, LIME, feature importance)

## Perspective 2: Data Engineer / Pipeline Operator
Asks: How reliable is the data pipeline? What breaks silently?
- Data ingestion sources and freshness guarantees
- Pipeline orchestration (Airflow, Prefect, Dagster) and DAG structure
- Data validation between pipeline stages (schema checks, anomaly detection)
- Compute resource management (GPU allocation, spot instances, scaling)
- Pipeline failure recovery and retry strategies
- Artifact storage and lifecycle (model files, embeddings, intermediate outputs)
- Feature store integration and consistency
- Cost management for training and inference workloads

## Perspective 3: ML Governance / Risk Reviewer
Asks: What risks does this system introduce? Who is accountable?
- Model bias detection and fairness testing across demographic groups
- Data drift and model performance degradation monitoring
- A/B testing infrastructure and experiment isolation
- Model rollback procedures and canary deployments
- Training data provenance and compliance requirements
- Audit trail for model decisions (predictions, recommendations)
- Model performance alerting thresholds and escalation paths
- Regulatory compliance (GDPR right-to-explanation, industry-specific requirements)
