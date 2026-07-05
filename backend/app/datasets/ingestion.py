from hashlib import sha256
from pathlib import Path
import shutil
from uuid import uuid4

import pandas as pd
from sqlmodel import Session

from app.core.config import AppSettings
from app.datasets.profiler import profile_dataframe
from app.datasets.registry import create_dataset, replace_column_profiles
from app.storage.duckdb import create_table_from_csv
from app.storage.models import Dataset


def schema_hash(columns: list[str]) -> str:
    return sha256("|".join(columns).encode("utf-8")).hexdigest()


def dataset_table_name() -> str:
    return f"dataset_{uuid4().hex}"


def ingest_csv_dataset(
    *,
    session: Session,
    settings: AppSettings,
    project_id: str,
    source_path: Path,
    original_name: str,
) -> Dataset:
    upload_dir = settings.uploads_dir / project_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_path = upload_dir / f"{uuid4().hex}_{original_name}"
    shutil.copyfile(source_path, stored_path)

    frame = pd.read_csv(stored_path)
    profile = profile_dataframe(frame)
    table_name = dataset_table_name()
    create_table_from_csv(settings.duckdb_path, table_name, stored_path)

    dataset = create_dataset(
        session,
        project_id=project_id,
        name=original_name,
        source_type="file",
        storage_uri=str(stored_path),
        duckdb_table_name=table_name,
        schema_hash=schema_hash([str(column) for column in frame.columns]),
        row_count=profile["row_count"],
        column_count=profile["column_count"],
        profile_status="completed",
    )
    replace_column_profiles(session, dataset.id, profile["columns"])
    return dataset
