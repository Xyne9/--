# Data Science Agent Design

Date: 2026-07-05

## Goal

Build a local, single-user, hybrid data science agent workspace. The user interacts through chat, while the workspace shows datasets, generated code, tables, charts, experiment results, warnings, and reports. The system supports structured data science workflows: data understanding, cleaning, EDA, statistical analysis, modeling, validation, and reproducible reporting.

The first version runs on the user's machine. Data execution, file handling, database connections, model training, and artifacts stay local. The LLM may be cloud-hosted, but it receives only schemas, metadata, profiles, small samples, and summarized execution results, not full datasets.

## Product Shape

The product is a hybrid workspace rather than a pure chat app or a pure notebook.

```text
Browser at localhost
  -> Local Web UI
  -> Local FastAPI backend
  -> Agent orchestrator
  -> LLM provider adapter
  -> Local Python and SQL runtimes
  -> Local SQLite, DuckDB, and workspace files
```

The UI has these primary panels:

- Chat panel for intent, questions, confirmations, and final answers.
- Dataset explorer for schemas, profiles, previews, and versions.
- Code/notebook panel for generated SQL and Python steps.
- Chart and table viewer for outputs.
- Cleaning pipeline view for versioned transformations.
- Experiment tracker for model metrics and artifacts.
- Report panel for generated Markdown or HTML reports.

The design principle is: chat captures intent, the workspace shows evidence.

## Core Architecture

```text
Local Hybrid Data Science Agent
+-- Web UI
|   +-- Chat Panel
|   +-- Dataset Explorer
|   +-- Code / Notebook Panel
|   +-- Chart & Table Viewer
|   +-- Cleaning Pipeline View
|   +-- Experiment Tracker View
|   +-- Report Panel
|
+-- Local Backend API
|   +-- Project / Session Service
|   +-- Dataset Registry
|   +-- Artifact Store
|   +-- Agent Orchestrator
|   +-- LLM Provider Adapter
|
+-- Agent Layer
|   +-- Intent Router
|   +-- Data Understanding Agent
|   +-- Cleaning Agent
|   +-- EDA Agent
|   +-- Statistical Analysis Agent
|   +-- Modeling Agent
|   +-- Visualization Agent
|   +-- Verifier Agent
|
+-- Execution Layer
|   +-- Python Runtime Adapter
|   |   +-- Local venv executor, first version
|   |   +-- Docker sandbox executor, reserved interface
|   +-- SQL Runtime
|   |   +-- DuckDB for local files
|   |   +-- Read-only database connectors
|   +-- Job Manager
|
+-- Local Storage
    +-- SQLite: metadata, sessions, runs
    +-- DuckDB: file-backed analytics tables
    +-- Workspace files: uploads, notebooks, reports
    +-- Artifacts: charts, models, metrics, logs
```

## Key Decisions

- The first product target is a data science assistant, not BI.
- The first deployment target is a local single-user app.
- The first interaction model is hybrid chat plus workspace.
- The first data inputs include both uploaded files and database connections.
- The first execution runtime uses the local Python virtual environment.
- The runtime is abstracted so Docker sandbox execution can be added later.
- Agent behavior uses a lightweight state machine plus tool calls.
- The system avoids an early dependency on complex multi-agent debate.
- The LLM is accessed only through a provider adapter.
- Full raw data is not sent to the LLM by default.

## Agent Workflow

The orchestrator turns a natural-language request into a reproducible analysis run.

```text
User Request
  -> Intent Router
  -> Context Builder
  -> Plan Generator
  -> Plan Reviewer
  -> Step Executor
  -> Result Verifier
  -> Workspace Renderer
  -> Final Answer / Report
```

Example request:

```text
Help me predict customer churn and identify the main drivers.
```

The system should:

1. Classify the task as supervised classification, feature analysis, and reporting.
2. Build context from the selected dataset, schema, profiles, previous runs, and available libraries.
3. Generate a structured plan.
4. Review the plan for missing target fields, data leakage, low sample size, class imbalance, time-series split risks, and unclear assumptions.
5. Ask for user confirmation when a consequential choice is required.
6. Generate and execute SQL or Python steps.
7. Verify runtime success and methodology quality.
8. Render code, outputs, warnings, metrics, charts, and summaries in the workspace.
9. Produce a final answer that cites generated evidence.

The orchestrator state machine is:

```text
CREATED
 -> CONTEXT_READY
 -> PLAN_DRAFTED
 -> PLAN_APPROVED
 -> RUNNING_STEP
 -> STEP_VERIFIED
 -> WAITING_USER_INPUT
 -> COMPLETED
 -> FAILED
```

Every step stores code, inputs, outputs, warnings, artifacts, and validation results. Users can rerun one step or the full plan.

## Execution Contract

Agents do not execute code directly. They submit an execution request to a runtime adapter.

```text
ExecutionRequest
  - project_id
  - dataset_id
  - run_id
  - step_id
  - language: python | sql
  - code
  - input_artifacts
  - expected_outputs
  - timeout_seconds
```

The runtime returns:

```text
ExecutionResult
  - status
  - stdout
  - stderr
  - output_tables
  - charts
  - model_files
  - metrics
  - warnings
  - artifact_ids
```

First-version runtime constraints:

- Each task has a timeout.
- Each execution has a run id and step id.
- Working directories are scoped to the project workspace.
- Database connectors are read-only by default.
- Remote database previews and generated queries use limits by default.
- Automatic repair is capped at two retries per step.

## Data Layer

The local data layer has three responsibilities:

- SQLite stores metadata and run state.
- DuckDB stores local analytical tables and views.
- The file workspace stores uploads, notebooks, charts, models, reports, logs, and exports.

```text
Local Data Layer
+-- Dataset Registry, SQLite
+-- Analytical Store, DuckDB
+-- File Workspace
+-- Profiler / Metadata Builder
```

SQLite tables include:

```text
projects
sessions
datasets
dataset_versions
data_sources
columns
profiles
analysis_runs
execution_steps
artifacts
experiments
```

Dataset metadata includes:

```text
dataset_id
project_id
name
source_type: file | database | query_result
storage_uri
duckdb_table_name
schema_hash
row_count
created_at
updated_at
```

Column metadata includes:

```text
column_name
logical_type
physical_type
nullable
missing_rate
unique_count
sample_values
semantic_role: target | feature | id | timestamp | category | text
pii_risk
```

DuckDB responsibilities:

- Ingest CSV, Excel, and Parquet into local tables or views.
- Support SQL-based EDA, filtering, aggregation, and profiling.
- Store intermediate cleaned dataset versions.
- Provide modeling-ready extracts to pandas.

Remote database responsibilities:

- Introspect schema.
- Read small previews and profiles.
- Run read-only queries.
- Materialize local samples or tables only when the user or plan requires it.

## Profiler

The profiler runs after dataset registration and after important cleaned versions.

Table-level profile:

- Row count.
- Column count.
- Duplicate row estimate.
- Memory estimate.
- Time range when a timestamp column exists.

Column-level profile:

- Type inference.
- Missing rate.
- Unique count.
- Numeric min, max, mean, standard deviation, and quantiles.
- Top categories.
- Sample values.
- Possible id, timestamp, target, categorical, text, and PII roles.

Profiler output feeds both the UI and the LLM context.

## Dataset Versions And Cleaning

Cleaning never overwrites the original dataset. Each meaningful cleaning operation creates a new dataset version.

```text
raw_dataset
  -> clean_step_1_remove_duplicates
  -> clean_step_2_impute_missing
  -> clean_step_3_encode_categories
```

Each version stores:

```text
parent_dataset_version_id
operation_type
generated_code
input_artifacts
output_table
profile_diff
created_by: agent | user
```

The user can inspect how missing values, duplicates, type conversions, and outliers were handled.

## Artifact Store

Artifacts are stored as files and referenced from SQLite.

```text
workspace/
  project.sqlite
  analytics.duckdb
  uploads/
  datasets/
  runs/
    run_001/
      plan.json
      steps/
      artifacts/
  reports/
  models/
  notebooks/
```

Artifact types include:

- Tables.
- Chart specifications.
- Images.
- Model files.
- Metrics JSON.
- Reports.
- Generated notebooks.
- Logs.

## First-Version Capabilities

The first version supports structured data science workflows.

Supported data understanding:

- Upload CSV, Excel, and Parquet.
- Connect Postgres, MySQL, SQLite, and SQLAlchemy URLs.
- Generate schema, missingness, distributions, samples, duplicates, outliers, and semantic role suggestions.

Supported cleaning:

- Deduplication.
- Missing-value handling.
- Type conversion.
- Outlier detection and suggested handling.
- Categorical encoding.
- Timestamp parsing.
- Profile diff before and after cleaning.
- Versioned rollback.

Supported EDA:

- Univariate distributions.
- Correlation analysis.
- Grouped statistics.
- Time trends.
- Target comparisons.
- Chart recommendations.
- Evidence-linked exploratory conclusions.

Supported statistics:

- t-test.
- Chi-square test.
- ANOVA.
- Confidence intervals.
- Basic linear and logistic regression interpretation.
- Basic A/B experiment analysis.
- Warnings for low sample size, assumption mismatch, and causal overclaiming.

Supported modeling:

- Classification.
- Regression.
- Train/test split.
- Preprocessing pipelines.
- Baseline model training.
- Common scikit-learn model comparison.
- Optional XGBoost if installed.
- Metrics such as AUC, F1, RMSE, MAE, and R2.
- Feature importance and permutation importance.
- Model artifact saving.

Supported reporting and reproduction:

- Generated SQL and Python cells.
- Step outputs and artifacts.
- Run history.
- Re-run single step or full run.
- Markdown and HTML reports.

## Explicit Non-Goals For Version One

The first version does not support:

- Deep learning training.
- Distributed Spark-style computation.
- Full AutoML search.
- Real-time streaming analytics.
- Multi-user collaboration.
- Enterprise permission and audit administration.
- Automatic mutation of remote databases.
- Image, audio, or long-text model training.
- Full causal inference automation.
- R runtime execution.

Reserved extension points:

- Docker sandbox executor.
- Multi-user projects.
- Additional database connectors.
- Model registry.
- Scheduled jobs.
- Dashboard publishing.
- R runtime adapter.

## Technology Choices

```text
Frontend: React + TypeScript + Vite
Backend: Python + FastAPI
Agent Runtime: lightweight in-house orchestrator
LLM: OpenAI-compatible provider adapter
Local Metadata: SQLite + SQLAlchemy or SQLModel
Analytical Engine: DuckDB
Execution: local Python venv executor first, Docker executor later
DataFrame: pandas first, optional polars later
ML: scikit-learn + statsmodels
Charts: ECharts or Plotly chart specs
Reports: Markdown + HTML
Events: server-sent events
```

Backend structure:

```text
backend/
  app/
    main.py
    api/
      projects.py
      datasets.py
      chat.py
      runs.py
      artifacts.py
    core/
      config.py
      llm.py
      security.py
    agents/
      orchestrator.py
      planner.py
      verifier.py
      prompts/
    datasets/
      registry.py
      connectors/
      profiler.py
      ingestion.py
    execution/
      runtime.py
      local_python.py
      docker_runtime.py
      sql_runtime.py
    storage/
      sqlite.py
      duckdb.py
      artifacts.py
    experiments/
      tracker.py
```

Frontend structure:

```text
frontend/
  src/
    app/
    api/
    components/
    features/
      chat/
      datasets/
      notebook/
      charts/
      experiments/
      reports/
    layouts/
    stores/
    types/
```

LLM access is isolated behind methods such as:

```text
generate_plan()
generate_code()
repair_code()
summarize_result()
critique_result()
```

No business module should call a model provider directly.

## MVP User Flow

```text
1. User creates a project.
2. User uploads a file or connects a database.
3. System registers a dataset and creates a profile.
4. User asks an analysis question in chat.
5. Agent generates a structured plan.
6. User approves the plan or adjusts key parameters.
7. Backend executes SQL and Python steps.
8. Frontend shows code, tables, charts, metrics, warnings, and artifacts.
9. Agent summarizes results and generates a report.
10. User can rerun a step, edit code, or export the report.
```

## MVP API Contract

```text
POST   /api/projects
GET    /api/projects/{project_id}

POST   /api/datasets/upload
POST   /api/datasources/test
POST   /api/datasets/from-database
GET    /api/datasets/{dataset_id}
GET    /api/datasets/{dataset_id}/profile
GET    /api/datasets/{dataset_id}/preview

POST   /api/chat/messages
POST   /api/runs
GET    /api/runs/{run_id}
GET    /api/runs/{run_id}/events
POST   /api/runs/{run_id}/approve-plan
POST   /api/runs/{run_id}/steps/{step_id}/retry

GET    /api/artifacts/{artifact_id}
GET    /api/reports/{report_id}
POST   /api/reports
```

Run events include:

```text
run.created
plan.generated
plan.requires_approval
step.started
step.code_generated
step.output_created
step.warning_created
step.completed
step.failed
run.completed
```

## Core Data Contracts

Dataset:

```json
{
  "dataset_id": "ds_001",
  "project_id": "proj_001",
  "name": "customer_churn.csv",
  "source_type": "file",
  "row_count": 10000,
  "column_count": 24,
  "profile_status": "completed"
}
```

Run:

```json
{
  "run_id": "run_001",
  "project_id": "proj_001",
  "dataset_id": "ds_001",
  "user_goal": "Predict customer churn and identify the main drivers.",
  "status": "running",
  "current_step_id": "step_003"
}
```

Step:

```json
{
  "step_id": "step_003",
  "run_id": "run_001",
  "title": "Train baseline classification models",
  "language": "python",
  "status": "completed",
  "code": "...",
  "outputs": ["artifact_metrics_001", "artifact_chart_002"],
  "warnings": []
}
```

Artifact:

```json
{
  "artifact_id": "artifact_chart_002",
  "run_id": "run_001",
  "type": "chart",
  "format": "echarts_spec",
  "uri": "runs/run_001/artifacts/chart_002.json"
}
```

## Validation And Error Handling

The system separates runtime success from data science validity.

Error categories:

```text
SystemError
- File read failure
- Database connection failure
- Execution timeout
- Missing dependency
- Artifact write failure

CodeError
- SQL syntax error
- Python syntax error
- Missing column
- Type conversion failure
- Model training exception

DataError
- Empty dataset
- Excessive missingness
- Missing target column
- Excessive category cardinality
- Insufficient sample size
- Extreme class imbalance

MethodologyWarning
- Data leakage risk
- Random split on time-series data
- Mismatched metric
- Misread p-value
- Correlation treated as causation
- Suspiciously high model score

UserDecisionRequired
- Multiple possible target columns
- Ambiguous missing-value strategy
- Whether to remove outliers
- Whether to materialize remote data locally
- Whether to exclude suspected leakage fields
```

Every execution step is validated through:

```text
Step Executor
  -> Raw Result
  -> Runtime Validation
  -> Data Validation
  -> Methodology Validation
  -> UI Warning / Retry / Continue
```

Validation result:

```json
{
  "status": "passed | warning | failed | needs_user_input",
  "checks": [
    {
      "check": "target_balance",
      "severity": "warning",
      "message": "Target classes are imbalanced at 92:8; use stratified split or class weights."
    }
  ]
}
```

Automatic repair is allowed for low-risk errors:

- Field name casing or spacing issues.
- Missing SQL limit.
- Missing Python import.
- Chart spec formatting.
- Minor type conversion issues.

User confirmation is required for consequential changes:

- Deleting rows or columns.
- Choosing missing-value imputation strategy.
- Selecting target field.
- Excluding suspected leakage features.
- Running large remote database queries.

## Reporting Requirements

The final answer and report must cite evidence from the run:

- Metrics.
- Charts.
- Tables.
- Generated code steps.
- Validation warnings.
- Data limitations.

Reports must include a limitations section when warnings exist.

Example:

```text
Limitations:
- The target class is imbalanced, so AUC and F1 are more informative than accuracy.
- The result is based on a local sample of 10,000 rows, not the full remote table.
- Feature importance should not be interpreted as causality.
```

## Testing Strategy

Unit tests:

- Dataset registry CRUD.
- Profiler type inference.
- Runtime adapter request and result handling.
- LLM provider adapter contract.
- Plan and step state transitions.
- Validation rules.

Integration tests:

- Upload CSV, profile it, preview it.
- Register a SQLite or Postgres-like source through a connector abstraction.
- Run a simple EDA plan end to end.
- Run a classification baseline on a small fixture dataset.
- Produce chart artifacts and a report.

Agent evaluation fixtures:

- Missing target column.
- Imbalanced classification.
- Time-series dataset where random split is risky.
- Dataset with suspected leakage field.
- Dataset with high missingness.

UI verification:

- Run progress events render correctly.
- Plan approval blocks execution until confirmed.
- Step warnings are visible.
- Artifacts open from the workspace.
- Report export works.

## Success Criteria

Version one is successful when a user can:

1. Start the local app.
2. Create a project.
3. Upload a structured dataset or connect a read-only database.
4. See automatic profile and preview.
5. Ask for cleaning, EDA, statistical analysis, or modeling.
6. Review and approve the generated plan.
7. Watch steps execute with visible code and outputs.
8. Inspect warnings and validation results.
9. Export a reproducible Markdown or HTML report.

The core end-to-end target is:

```text
Data understanding -> cleaning suggestion -> EDA -> modeling/statistics -> charts -> reproducible report
```
