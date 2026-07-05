from dataclasses import dataclass
from textwrap import dedent

from sqlmodel import Session

from app.artifacts.registry import index_step_artifacts
from app.core.config import AppSettings, ensure_workspace
from app.datasets.registry import (
    get_dataset,
    get_run,
    list_run_steps,
    record_step_execution_result,
    update_run_status,
)
from app.execution.local_python import LocalPythonRuntime
from app.execution.runtime import ExecutionRequest
from app.storage.models import AnalysisRun, Dataset, ExecutionStep


@dataclass(frozen=True)
class RunExecutionResult:
    run: AnalysisRun
    steps: list[ExecutionStep]


class RunOrchestrator:
    def __init__(self, runtime: LocalPythonRuntime | None = None) -> None:
        self.runtime = runtime or LocalPythonRuntime()

    def execute_run(
        self,
        session: Session,
        settings: AppSettings,
        run_id: str,
        timeout_seconds: float,
    ) -> RunExecutionResult:
        run = get_run(session, run_id)
        if run is None:
            raise ValueError("Run not found")
        dataset = get_dataset(session, run.dataset_id)
        if dataset is None:
            raise ValueError("Dataset not found")

        workspace_settings = ensure_workspace(settings)
        run = update_run_status(session, run, "RUNNING")
        executed_steps: list[ExecutionStep] = []
        final_status = "COMPLETED"

        for step in list_run_steps(session, run.id):
            code = generate_step_code(
                run=run,
                dataset=dataset,
                step=step,
                settings=workspace_settings,
            )
            result = self.runtime.execute(
                ExecutionRequest(
                    run_id=run.id,
                    step_id=step.id,
                    code=code,
                    workspace_root=workspace_settings.workspace_root,
                    timeout_seconds=timeout_seconds,
                )
            )
            recorded_step = record_step_execution_result(session, step, result, code=code)
            index_step_artifacts(
                session,
                run_id=run.id,
                step_id=recorded_step.id,
                artifacts_dir=result.artifacts_dir,
                workspace_root=workspace_settings.workspace_root,
            )
            executed_steps.append(recorded_step)
            if result.status != "completed":
                final_status = "FAILED"
                break

        run = update_run_status(session, run, final_status)
        return RunExecutionResult(run=run, steps=executed_steps)


def generate_step_code(
    *,
    run: AnalysisRun,
    dataset: Dataset,
    step: ExecutionStep,
    settings: AppSettings,
) -> str:
    if step.kind == "profile":
        return profile_step_code(dataset=dataset, settings=settings)
    if step.kind == "eda":
        return eda_step_code(dataset=dataset, settings=settings)
    if step.kind == "summary":
        return summary_step_code(run=run, dataset=dataset)
    return generic_step_code(step=step, dataset=dataset)


def duckdb_bindings(dataset: Dataset, settings: AppSettings) -> tuple[str, str]:
    return repr(str(settings.duckdb_path)), repr(dataset.duckdb_table_name)


def profile_step_code(dataset: Dataset, settings: AppSettings) -> str:
    db_path, table_name = duckdb_bindings(dataset, settings)
    return dedent(
        f"""
        import json
        from pathlib import Path

        import duckdb

        db_path = {db_path}
        table_name = {table_name}
        quoted_table = '"' + table_name.replace('"', '""') + '"'
        artifacts_dir = Path("artifacts")
        artifacts_dir.mkdir(exist_ok=True)

        with duckdb.connect(db_path, read_only=True) as connection:
            row_count = connection.execute(f"SELECT COUNT(*) FROM {{quoted_table}}").fetchone()[0]
            cursor = connection.execute(f"SELECT * FROM {{quoted_table}} LIMIT 0")
            columns = [description[0] for description in cursor.description]
            missing_counts = {{}}
            for column in columns:
                quoted_column = '"' + column.replace('"', '""') + '"'
                missing_counts[column] = connection.execute(
                    f"SELECT COUNT(*) FROM {{quoted_table}} WHERE {{quoted_column}} IS NULL"
                ).fetchone()[0]

        summary = {{
            "table_name": table_name,
            "row_count": row_count,
            "column_count": len(columns),
            "columns": columns,
            "missing_counts": missing_counts,
        }}
        (artifacts_dir / "profile_summary.json").write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )
        print(f"Profiled {{row_count}} rows and {{len(columns)}} columns from {{table_name}}.")
        """
    ).strip() + "\n"


def eda_step_code(dataset: Dataset, settings: AppSettings) -> str:
    db_path, table_name = duckdb_bindings(dataset, settings)
    return dedent(
        f"""
        import json
        from pathlib import Path

        import duckdb

        db_path = {db_path}
        table_name = {table_name}
        quoted_table = '"' + table_name.replace('"', '""') + '"'
        artifacts_dir = Path("artifacts")
        artifacts_dir.mkdir(exist_ok=True)

        with duckdb.connect(db_path, read_only=True) as connection:
            sample = connection.execute(f"SELECT * FROM {{quoted_table}} LIMIT 1000").fetchdf()

        if sample.empty:
            describe = {{}}
        else:
            describe = sample.describe(include="all").fillna("").astype(str).to_dict()

        summary = {{
            "table_name": table_name,
            "sample_rows": len(sample),
            "columns": list(sample.columns),
            "describe": describe,
        }}
        (artifacts_dir / "eda_summary.json").write_text(
            json.dumps(summary, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"Generated EDA summary for {{len(sample)}} sampled rows from {{table_name}}.")
        """
    ).strip() + "\n"


def summary_step_code(run: AnalysisRun, dataset: Dataset) -> str:
    dataset_name = repr(dataset.name)
    table_name = repr(dataset.duckdb_table_name)
    user_goal = repr(run.user_goal)
    return dedent(
        f"""
        from pathlib import Path

        dataset_name = {dataset_name}
        table_name = {table_name}
        user_goal = {user_goal}
        artifacts_dir = Path("artifacts")
        artifacts_dir.mkdir(exist_ok=True)

        report = "\\n".join(
            [
                "# Analysis Run Summary",
                "",
                f"Dataset: {{dataset_name}}",
                f"DuckDB table: {{table_name}}",
                f"User goal: {{user_goal}}",
                "",
                "This deterministic first-pass run generated a dataset profile and EDA summary.",
                "LLM narrative synthesis and evidence-linked reporting will be added in a later phase.",
                "",
            ]
        )
        (artifacts_dir / "summary_report.md").write_text(report, encoding="utf-8")
        print(f"Wrote summary report for {{dataset_name}}.")
        """
    ).strip() + "\n"


def generic_step_code(step: ExecutionStep, dataset: Dataset) -> str:
    step_title = repr(step.title)
    dataset_name = repr(dataset.name)
    return dedent(
        f"""
        from pathlib import Path

        step_title = {step_title}
        dataset_name = {dataset_name}
        artifacts_dir = Path("artifacts")
        artifacts_dir.mkdir(exist_ok=True)
        output = f"Skipped generic step '{{step_title}}' for dataset '{{dataset_name}}'."
        (artifacts_dir / "step_output.txt").write_text(output, encoding="utf-8")
        print(output)
        """
    ).strip() + "\n"
