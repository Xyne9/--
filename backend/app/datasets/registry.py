import json
from typing import Any

from sqlmodel import Session, select

from app.core.config import AppSettings
from app.storage.duckdb import preview_table
from app.storage.models import AnalysisRun, ColumnProfile, Dataset, ExecutionStep, Project


def create_project(session: Session, name: str) -> Project:
    project = Project(name=name)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def get_project(session: Session, project_id: str) -> Project | None:
    return session.get(Project, project_id)


def create_dataset(
    session: Session,
    *,
    project_id: str,
    name: str,
    source_type: str,
    storage_uri: str,
    duckdb_table_name: str,
    schema_hash: str,
    row_count: int,
    column_count: int,
    profile_status: str,
) -> Dataset:
    dataset = Dataset(
        project_id=project_id,
        name=name,
        source_type=source_type,
        storage_uri=storage_uri,
        duckdb_table_name=duckdb_table_name,
        schema_hash=schema_hash,
        row_count=row_count,
        column_count=column_count,
        profile_status=profile_status,
    )
    session.add(dataset)
    session.commit()
    session.refresh(dataset)
    return dataset


def replace_column_profiles(
    session: Session,
    dataset_id: str,
    columns: list[dict[str, Any]],
) -> None:
    existing = session.exec(select(ColumnProfile).where(ColumnProfile.dataset_id == dataset_id)).all()
    for profile in existing:
        session.delete(profile)

    for column in columns:
        session.add(
            ColumnProfile(
                dataset_id=dataset_id,
                name=column["name"],
                logical_type=column["logical_type"],
                physical_type=column["physical_type"],
                nullable=column["nullable"],
                missing_rate=column["missing_rate"],
                unique_count=column["unique_count"],
                sample_values_json=json.dumps(column["sample_values"]),
                semantic_role=column["semantic_role"],
                pii_risk=column["pii_risk"],
            )
        )
    session.commit()


def get_dataset(session: Session, dataset_id: str) -> Dataset | None:
    return session.get(Dataset, dataset_id)


def get_dataset_profile(session: Session, dataset_id: str) -> dict[str, Any]:
    dataset = get_dataset(session, dataset_id)
    if dataset is None:
        raise ValueError("Dataset not found")
    columns = session.exec(select(ColumnProfile).where(ColumnProfile.dataset_id == dataset_id)).all()
    return {
        "dataset_id": dataset.id,
        "name": dataset.name,
        "row_count": dataset.row_count,
        "column_count": dataset.column_count,
        "columns": [
            {
                "name": column.name,
                "logical_type": column.logical_type,
                "physical_type": column.physical_type,
                "nullable": column.nullable,
                "missing_rate": column.missing_rate,
                "unique_count": column.unique_count,
                "sample_values": json.loads(column.sample_values_json),
                "semantic_role": column.semantic_role,
                "pii_risk": column.pii_risk,
            }
            for column in columns
        ],
    }


def preview_dataset(settings: AppSettings, table_name: str, limit: int = 20) -> dict[str, Any]:
    return preview_table(settings.duckdb_path, table_name, limit)


def create_analysis_run(
    session: Session,
    *,
    project_id: str,
    dataset_id: str,
    user_goal: str,
    status: str,
) -> AnalysisRun:
    run = AnalysisRun(
        project_id=project_id,
        dataset_id=dataset_id,
        user_goal=user_goal,
        status=status,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def create_execution_step(
    session: Session,
    *,
    run_id: str,
    sequence: int,
    title: str,
    kind: str,
    status: str,
) -> ExecutionStep:
    step = ExecutionStep(
        run_id=run_id,
        sequence=sequence,
        title=title,
        kind=kind,
        status=status,
    )
    session.add(step)
    session.commit()
    session.refresh(step)
    return step


def get_run(session: Session, run_id: str) -> AnalysisRun | None:
    return session.get(AnalysisRun, run_id)


def list_run_steps(session: Session, run_id: str) -> list[ExecutionStep]:
    statement = select(ExecutionStep).where(ExecutionStep.run_id == run_id).order_by(ExecutionStep.sequence)
    return list(session.exec(statement).all())
