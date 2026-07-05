from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import Field, SQLModel


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Project(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("proj"), primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=utc_now)


class Dataset(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("ds"), primary_key=True)
    project_id: str = Field(foreign_key="project.id", index=True)
    name: str
    source_type: str
    storage_uri: str
    duckdb_table_name: str
    schema_hash: str
    row_count: int
    column_count: int
    profile_status: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ColumnProfile(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("col"), primary_key=True)
    dataset_id: str = Field(foreign_key="dataset.id", index=True)
    name: str
    logical_type: str
    physical_type: str
    nullable: bool
    missing_rate: float
    unique_count: int
    sample_values_json: str
    semantic_role: str
    pii_risk: str
