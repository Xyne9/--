# Phase 1 Backend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working backend slice for the local data science agent: FastAPI app, local workspace configuration, SQLite metadata, project API, CSV upload, profiling, and preview.

**Architecture:** This phase builds a testable backend foundation without LLM orchestration or frontend UI. FastAPI exposes local APIs, SQLModel stores metadata in SQLite, DuckDB stores uploaded CSV data for preview queries, and pandas powers the first profiler.

**Tech Stack:** Python 3.11+, FastAPI, SQLModel, SQLite, DuckDB, pandas, pytest, httpx.

---

## Scope

This plan implements the first backend slice only:

- Health endpoint.
- Local workspace settings.
- SQLite metadata tables.
- Project create/read API.
- CSV dataset upload.
- Dataset profile generation.
- DuckDB-backed dataset preview.

This plan does not implement the React workspace, LLM provider, orchestrator state machine, modeling runtime, remote database connectors, report generation, or GitHub Actions. Those should be planned after this backend slice is running and tested.

## File Structure

Create or modify these files:

```text
.gitignore
backend/pyproject.toml
backend/app/__init__.py
backend/app/main.py
backend/app/api/__init__.py
backend/app/api/deps.py
backend/app/api/projects.py
backend/app/api/datasets.py
backend/app/core/__init__.py
backend/app/core/config.py
backend/app/datasets/__init__.py
backend/app/datasets/ingestion.py
backend/app/datasets/profiler.py
backend/app/datasets/registry.py
backend/app/storage/__init__.py
backend/app/storage/duckdb.py
backend/app/storage/models.py
backend/app/storage/sqlite.py
backend/tests/conftest.py
backend/tests/test_app_smoke.py
backend/tests/test_config.py
backend/tests/test_project_api.py
backend/tests/test_profiler.py
backend/tests/test_dataset_upload_api.py
```

Responsibilities:

- `.gitignore`: Keep generated workspace files, local virtualenvs, caches, and install downloads out of Git.
- `backend/pyproject.toml`: Define backend dependencies and pytest configuration.
- `backend/app/main.py`: Build the FastAPI app, register routers, and expose `/health`.
- `backend/app/core/config.py`: Resolve and create local workspace paths.
- `backend/app/storage/models.py`: Define SQLModel metadata tables.
- `backend/app/storage/sqlite.py`: Create SQLite engines and sessions.
- `backend/app/storage/duckdb.py`: Create DuckDB connections and safe preview helpers.
- `backend/app/datasets/profiler.py`: Generate table and column profiles from pandas DataFrames.
- `backend/app/datasets/registry.py`: Persist projects, datasets, and column profiles.
- `backend/app/datasets/ingestion.py`: Store uploads, materialize CSV into DuckDB, profile data, and register datasets.
- `backend/app/api/deps.py`: Provide request-scoped database sessions and settings.
- `backend/app/api/projects.py`: Expose project APIs.
- `backend/app/api/datasets.py`: Expose dataset upload/profile/preview APIs.

---

### Task 1: Backend Toolchain And Health Endpoint

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/test_app_smoke.py`
- Modify: `.gitignore`

- [ ] **Step 1: Add repository ignore rules**

Create `.gitignore` with:

```gitignore
.venv/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.pyc
*.pyo
*.pyd
*.sqlite
*.duckdb
.data-agent/
work/
backend/.venv/
backend/htmlcov/
backend/.coverage
frontend/node_modules/
frontend/dist/
```

- [ ] **Step 2: Create backend package metadata**

Create `backend/pyproject.toml` with:

```toml
[project]
name = "data-science-agent-backend"
version = "0.1.0"
description = "Local backend for a hybrid data science agent workspace"
requires-python = ">=3.11"
dependencies = [
  "duckdb>=1.0.0",
  "fastapi>=0.115.0",
  "httpx>=0.27.0",
  "pandas>=2.2.0",
  "python-multipart>=0.0.9",
  "sqlmodel>=0.0.22",
  "uvicorn[standard]>=0.30.0"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0"
]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
addopts = "-q"
```

- [ ] **Step 3: Write the failing health test**

Create `backend/tests/test_app_smoke.py` with:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_returns_ok():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 4: Run the health test and verify it fails**

Run:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m pytest tests/test_app_smoke.py -q
```

Expected: FAIL because `app.main` or `/health` does not exist.

- [ ] **Step 5: Implement the minimal FastAPI app**

Create `backend/app/__init__.py` with:

```python
"""Backend package for the local data science agent."""
```

Create `backend/app/main.py` with:

```python
from fastapi import FastAPI


app = FastAPI(title="Local Data Science Agent")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 6: Run the health test and verify it passes**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_app_smoke.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit Task 1**

Run:

```powershell
git add .gitignore backend/pyproject.toml backend/app/__init__.py backend/app/main.py backend/tests/test_app_smoke.py
git commit -m "feat: scaffold backend health endpoint"
```

---

### Task 2: Local Workspace Configuration

**Files:**
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/tests/test_config.py`

- [ ] **Step 1: Write the failing workspace settings test**

Create `backend/tests/test_config.py` with:

```python
from pathlib import Path

from app.core.config import build_settings, ensure_workspace


def test_build_settings_uses_explicit_workspace_root(tmp_path):
    workspace = tmp_path / "workspace"

    settings = build_settings(str(workspace))

    assert settings.workspace_root == workspace
    assert settings.sqlite_path == workspace / "project.sqlite"
    assert settings.duckdb_path == workspace / "analytics.duckdb"
    assert settings.uploads_dir == workspace / "uploads"
    assert settings.runs_dir == workspace / "runs"


def test_ensure_workspace_creates_required_directories(tmp_path):
    settings = build_settings(str(tmp_path / "workspace"))

    ensure_workspace(settings)

    assert settings.workspace_root.exists()
    assert settings.uploads_dir.exists()
    assert settings.runs_dir.exists()
```

- [ ] **Step 2: Run the settings tests and verify they fail**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_config.py -q
```

Expected: FAIL because `app.core.config` does not exist.

- [ ] **Step 3: Implement workspace settings**

Create `backend/app/core/__init__.py` with:

```python
"""Core configuration and application utilities."""
```

Create `backend/app/core/config.py` with:

```python
from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path


@dataclass(frozen=True)
class AppSettings:
    workspace_root: Path
    sqlite_path: Path
    duckdb_path: Path
    uploads_dir: Path
    runs_dir: Path


def build_settings(workspace_root: str | None = None) -> AppSettings:
    root = Path(workspace_root or os.getenv("DATA_AGENT_WORKSPACE", ".data-agent")).resolve()
    return AppSettings(
        workspace_root=root,
        sqlite_path=root / "project.sqlite",
        duckdb_path=root / "analytics.duckdb",
        uploads_dir=root / "uploads",
        runs_dir=root / "runs",
    )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return build_settings()


def ensure_workspace(settings: AppSettings) -> AppSettings:
    settings.workspace_root.mkdir(parents=True, exist_ok=True)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.runs_dir.mkdir(parents=True, exist_ok=True)
    return settings
```

- [ ] **Step 4: Run the settings tests and verify they pass**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_config.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

Run:

```powershell
git add backend/app/core backend/tests/test_config.py
git commit -m "feat: add local workspace settings"
```

---

### Task 3: SQLite Metadata Models And Registry

**Files:**
- Create: `backend/app/storage/__init__.py`
- Create: `backend/app/storage/models.py`
- Create: `backend/app/storage/sqlite.py`
- Create: `backend/app/datasets/__init__.py`
- Create: `backend/app/datasets/registry.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_project_api.py`

- [ ] **Step 1: Write failing registry tests**

Create `backend/tests/conftest.py` with:

```python
import pytest
from sqlmodel import Session

from app.storage.sqlite import create_db_and_tables, create_engine_for_path


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine_for_path(tmp_path / "project.sqlite")
    create_db_and_tables(engine)
    with Session(engine) as session:
        yield session
```

Create `backend/tests/test_project_api.py` with this registry-level test first:

```python
from app.datasets.registry import create_project, get_project


def test_create_and_get_project(db_session):
    project = create_project(db_session, name="Customer Churn")

    loaded = get_project(db_session, project.id)

    assert loaded is not None
    assert loaded.id == project.id
    assert loaded.name == "Customer Churn"
```

- [ ] **Step 2: Run the registry test and verify it fails**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_project_api.py::test_create_and_get_project -q
```

Expected: FAIL because storage and registry modules do not exist.

- [ ] **Step 3: Implement metadata models and SQLite helpers**

Create `backend/app/storage/__init__.py` with:

```python
"""Storage adapters for SQLite metadata and DuckDB analytics."""
```

Create `backend/app/storage/models.py` with:

```python
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
```

Create `backend/app/storage/sqlite.py` with:

```python
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, create_engine


def create_engine_for_path(path: Path) -> Engine:
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})


def create_db_and_tables(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine)
```

- [ ] **Step 4: Implement project registry functions**

Create `backend/app/datasets/__init__.py` with:

```python
"""Dataset ingestion, profiling, and metadata registry modules."""
```

Create `backend/app/datasets/registry.py` with:

```python
from sqlmodel import Session

from app.storage.models import Project


def create_project(session: Session, name: str) -> Project:
    project = Project(name=name)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def get_project(session: Session, project_id: str) -> Project | None:
    return session.get(Project, project_id)
```

- [ ] **Step 5: Run the registry test and verify it passes**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_project_api.py::test_create_and_get_project -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 3**

Run:

```powershell
git add backend/app/storage backend/app/datasets/__init__.py backend/app/datasets/registry.py backend/tests/conftest.py backend/tests/test_project_api.py
git commit -m "feat: add sqlite metadata registry"
```

---

### Task 4: Project API

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/api/projects.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_project_api.py`

- [ ] **Step 1: Add failing API tests**

Append these tests to `backend/tests/test_project_api.py`:

```python
from fastapi.testclient import TestClient

from app.api.deps import get_session
from app.main import app


def test_create_project_api(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    client = TestClient(app)

    response = client.post("/api/projects", json={"name": "Local DS Agent"})

    app.dependency_overrides.clear()
    assert response.status_code == 201
    body = response.json()
    assert body["id"].startswith("proj_")
    assert body["name"] == "Local DS Agent"


def test_get_project_api(db_session):
    project = create_project(db_session, name="Existing Project")
    app.dependency_overrides[get_session] = lambda: db_session
    client = TestClient(app)

    response = client.get(f"/api/projects/{project.id}")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["name"] == "Existing Project"
```

- [ ] **Step 2: Run project API tests and verify they fail**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_project_api.py -q
```

Expected: FAIL because API dependencies and routes do not exist.

- [ ] **Step 3: Implement API dependencies**

Create `backend/app/api/__init__.py` with:

```python
"""HTTP API routers."""
```

Create `backend/app/api/deps.py` with:

```python
from collections.abc import Generator

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.core.config import ensure_workspace, get_settings
from app.storage.sqlite import create_db_and_tables, create_engine_for_path


_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = ensure_workspace(get_settings())
        _engine = create_engine_for_path(settings.sqlite_path)
        create_db_and_tables(_engine)
    return _engine


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session
```

- [ ] **Step 4: Implement project routes**

Create `backend/app/api/projects.py` with:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from app.api.deps import get_session
from app.datasets.registry import create_project, get_project


router = APIRouter(prefix="/api/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str


class ProjectResponse(BaseModel):
    id: str
    name: str


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project_endpoint(
    request: CreateProjectRequest,
    session: Session = Depends(get_session),
) -> ProjectResponse:
    project = create_project(session, request.name)
    return ProjectResponse(id=project.id, name=project.name)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project_endpoint(
    project_id: str,
    session: Session = Depends(get_session),
) -> ProjectResponse:
    project = get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(id=project.id, name=project.name)
```

- [ ] **Step 5: Register the project router**

Replace `backend/app/main.py` with:

```python
from fastapi import FastAPI

from app.api.projects import router as projects_router


app = FastAPI(title="Local Data Science Agent")
app.include_router(projects_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 6: Run project API tests and verify they pass**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_project_api.py tests/test_app_smoke.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit Task 4**

Run:

```powershell
git add backend/app/api backend/app/main.py backend/tests/test_project_api.py
git commit -m "feat: expose project api"
```

---

### Task 5: Dataset Profiler

**Files:**
- Create: `backend/app/datasets/profiler.py`
- Create: `backend/tests/test_profiler.py`

- [ ] **Step 1: Write failing profiler tests**

Create `backend/tests/test_profiler.py` with:

```python
import pandas as pd

from app.datasets.profiler import profile_dataframe


def test_profile_dataframe_reports_table_shape_and_columns():
    frame = pd.DataFrame(
        {
            "customer_id": [1, 2, 3],
            "churn": [0, 1, 0],
            "plan": ["basic", "pro", None],
            "monthly_charge": [10.0, 25.5, 11.0],
        }
    )

    profile = profile_dataframe(frame)

    assert profile["row_count"] == 3
    assert profile["column_count"] == 4
    assert [column["name"] for column in profile["columns"]] == [
        "customer_id",
        "churn",
        "plan",
        "monthly_charge",
    ]


def test_profile_dataframe_reports_missing_and_unique_counts():
    frame = pd.DataFrame({"plan": ["basic", "pro", None, "basic"]})

    profile = profile_dataframe(frame)

    column = profile["columns"][0]
    assert column["missing_rate"] == 0.25
    assert column["unique_count"] == 2
    assert column["nullable"] is True
    assert column["logical_type"] == "categorical"
    assert column["sample_values"] == ["basic", "pro"]
```

- [ ] **Step 2: Run profiler tests and verify they fail**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_profiler.py -q
```

Expected: FAIL because `profile_dataframe` does not exist.

- [ ] **Step 3: Implement the profiler**

Create `backend/app/datasets/profiler.py` with:

```python
from typing import Any

import pandas as pd


def infer_logical_type(series: pd.Series) -> str:
    non_null = series.dropna()
    if non_null.empty:
        return "unknown"
    if pd.api.types.is_bool_dtype(non_null):
        return "boolean"
    if pd.api.types.is_integer_dtype(non_null):
        return "integer"
    if pd.api.types.is_float_dtype(non_null):
        return "float"
    if pd.api.types.is_datetime64_any_dtype(non_null):
        return "timestamp"

    unique_count = int(non_null.nunique(dropna=True))
    if unique_count <= max(20, int(len(non_null) * 0.2)):
        return "categorical"
    return "text"


def json_safe_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def sample_values(series: pd.Series, limit: int = 5) -> list[Any]:
    values = []
    for value in series.dropna().drop_duplicates().head(limit).tolist():
        values.append(json_safe_value(value))
    return values


def profile_dataframe(frame: pd.DataFrame) -> dict[str, Any]:
    row_count = int(len(frame))
    columns: list[dict[str, Any]] = []

    for name in frame.columns:
        series = frame[name]
        missing_count = int(series.isna().sum())
        missing_rate = 0.0 if row_count == 0 else missing_count / row_count
        columns.append(
            {
                "name": str(name),
                "logical_type": infer_logical_type(series),
                "physical_type": str(series.dtype),
                "nullable": bool(missing_count > 0),
                "missing_rate": round(missing_rate, 6),
                "unique_count": int(series.nunique(dropna=True)),
                "sample_values": sample_values(series),
                "semantic_role": "feature",
                "pii_risk": "unknown",
            }
        )

    return {
        "row_count": row_count,
        "column_count": int(len(frame.columns)),
        "columns": columns,
    }
```

- [ ] **Step 4: Run profiler tests and verify they pass**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_profiler.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 5**

Run:

```powershell
git add backend/app/datasets/profiler.py backend/tests/test_profiler.py
git commit -m "feat: add dataframe profiler"
```

---

### Task 6: CSV Ingestion, DuckDB Storage, And Dataset Registry

**Files:**
- Create: `backend/app/storage/duckdb.py`
- Create: `backend/app/datasets/ingestion.py`
- Modify: `backend/app/datasets/registry.py`
- Create: `backend/tests/test_dataset_upload_api.py`

- [ ] **Step 1: Write failing ingestion test**

Create `backend/tests/test_dataset_upload_api.py` with:

```python
from pathlib import Path

from app.core.config import build_settings, ensure_workspace
from app.datasets.ingestion import ingest_csv_dataset
from app.datasets.registry import create_project, get_dataset_profile, preview_dataset


def test_ingest_csv_dataset_registers_profile_and_preview(db_session, tmp_path):
    settings = ensure_workspace(build_settings(str(tmp_path / "workspace")))
    project = create_project(db_session, "CSV Project")
    csv_path = tmp_path / "customers.csv"
    csv_path.write_text(
        "customer_id,churn,plan\n1,0,basic\n2,1,pro\n3,0,basic\n",
        encoding="utf-8",
    )

    dataset = ingest_csv_dataset(
        session=db_session,
        settings=settings,
        project_id=project.id,
        source_path=Path(csv_path),
        original_name="customers.csv",
    )
    profile = get_dataset_profile(db_session, dataset.id)
    preview = preview_dataset(settings, dataset.duckdb_table_name, limit=2)

    assert dataset.name == "customers.csv"
    assert dataset.source_type == "file"
    assert dataset.row_count == 3
    assert dataset.column_count == 3
    assert profile["row_count"] == 3
    assert [column["name"] for column in profile["columns"]] == ["customer_id", "churn", "plan"]
    assert preview["columns"] == ["customer_id", "churn", "plan"]
    assert preview["rows"] == [
        {"customer_id": 1, "churn": 0, "plan": "basic"},
        {"customer_id": 2, "churn": 1, "plan": "pro"},
    ]
```

- [ ] **Step 2: Run ingestion test and verify it fails**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_dataset_upload_api.py::test_ingest_csv_dataset_registers_profile_and_preview -q
```

Expected: FAIL because ingestion, DuckDB helpers, and dataset registry functions do not exist.

- [ ] **Step 3: Implement DuckDB helpers**

Create `backend/app/storage/duckdb.py` with:

```python
from pathlib import Path
from typing import Any

import duckdb


def connect_duckdb(path: Path) -> duckdb.DuckDBPyConnection:
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def create_table_from_csv(db_path: Path, table_name: str, csv_path: Path) -> None:
    with connect_duckdb(db_path) as connection:
        connection.execute(
            f'CREATE OR REPLACE TABLE "{table_name}" AS SELECT * FROM read_csv_auto(?)',
            [str(csv_path)],
        )


def preview_table(db_path: Path, table_name: str, limit: int = 20) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 100))
    with connect_duckdb(db_path) as connection:
        result = connection.execute(f'SELECT * FROM "{table_name}" LIMIT {safe_limit}')
        columns = [description[0] for description in result.description]
        rows = [dict(zip(columns, row, strict=False)) for row in result.fetchall()]
    return {"columns": columns, "rows": rows}
```

- [ ] **Step 4: Extend registry for datasets and profiles**

Replace `backend/app/datasets/registry.py` with:

```python
import json
from typing import Any

from sqlmodel import Session, select

from app.core.config import AppSettings
from app.storage.duckdb import preview_table
from app.storage.models import ColumnProfile, Dataset, Project


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
```

- [ ] **Step 5: Implement CSV ingestion**

Create `backend/app/datasets/ingestion.py` with:

```python
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
```

- [ ] **Step 6: Run ingestion test and verify it passes**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_dataset_upload_api.py::test_ingest_csv_dataset_registers_profile_and_preview -q
```

Expected: PASS.

- [ ] **Step 7: Commit Task 6**

Run:

```powershell
git add backend/app/storage/duckdb.py backend/app/datasets/ingestion.py backend/app/datasets/registry.py backend/tests/test_dataset_upload_api.py
git commit -m "feat: ingest csv datasets"
```

---

### Task 7: Dataset Upload, Profile, And Preview API

**Files:**
- Create: `backend/app/api/datasets.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_dataset_upload_api.py`

- [ ] **Step 1: Add failing dataset API test**

Append this test to `backend/tests/test_dataset_upload_api.py`:

```python
from fastapi.testclient import TestClient

from app.api.deps import get_session
from app.core.config import build_settings, ensure_workspace
from app.datasets.registry import create_project
from app.main import app


def test_upload_profile_and_preview_api(db_session, tmp_path, monkeypatch):
    settings = ensure_workspace(build_settings(str(tmp_path / "workspace")))
    monkeypatch.setenv("DATA_AGENT_WORKSPACE", str(settings.workspace_root))
    project = create_project(db_session, "Upload API Project")
    app.dependency_overrides[get_session] = lambda: db_session
    client = TestClient(app)

    upload_response = client.post(
        "/api/datasets/upload",
        data={"project_id": project.id},
        files={"file": ("customers.csv", b"customer_id,churn\n1,0\n2,1\n", "text/csv")},
    )

    assert upload_response.status_code == 201
    dataset_id = upload_response.json()["id"]

    profile_response = client.get(f"/api/datasets/{dataset_id}/profile")
    preview_response = client.get(f"/api/datasets/{dataset_id}/preview?limit=1")

    app.dependency_overrides.clear()
    assert profile_response.status_code == 200
    assert profile_response.json()["row_count"] == 2
    assert preview_response.status_code == 200
    assert preview_response.json()["rows"] == [{"customer_id": 1, "churn": 0}]
```

- [ ] **Step 2: Run dataset API test and verify it fails**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_dataset_upload_api.py::test_upload_profile_and_preview_api -q
```

Expected: FAIL because dataset routes do not exist.

- [ ] **Step 3: Implement dataset routes**

Create `backend/app/api/datasets.py` with:

```python
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlmodel import Session

from app.api.deps import get_session
from app.core.config import ensure_workspace, get_settings
from app.datasets.ingestion import ingest_csv_dataset
from app.datasets.registry import get_dataset, get_dataset_profile, get_project, preview_dataset


router = APIRouter(prefix="/api/datasets", tags=["datasets"])


class DatasetResponse(BaseModel):
    id: str
    project_id: str
    name: str
    source_type: str
    row_count: int
    column_count: int
    profile_status: str


@router.post("/upload", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset_endpoint(
    project_id: str = Form(),
    file: UploadFile = File(),
    session: Session = Depends(get_session),
) -> DatasetResponse:
    if get_project(session, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV upload is supported in phase 1")

    content = await file.read()
    with NamedTemporaryFile(delete=False, suffix=".csv") as temp_file:
        temp_file.write(content)
        temp_path = Path(temp_file.name)

    settings = ensure_workspace(get_settings())
    dataset = ingest_csv_dataset(
        session=session,
        settings=settings,
        project_id=project_id,
        source_path=temp_path,
        original_name=file.filename,
    )
    temp_path.unlink(missing_ok=True)
    return DatasetResponse(
        id=dataset.id,
        project_id=dataset.project_id,
        name=dataset.name,
        source_type=dataset.source_type,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        profile_status=dataset.profile_status,
    )


@router.get("/{dataset_id}/profile")
def get_dataset_profile_endpoint(
    dataset_id: str,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    if get_dataset(session, dataset_id) is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return get_dataset_profile(session, dataset_id)


@router.get("/{dataset_id}/preview")
def preview_dataset_endpoint(
    dataset_id: str,
    limit: int = 20,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    dataset = get_dataset(session, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    settings = ensure_workspace(get_settings())
    return preview_dataset(settings, dataset.duckdb_table_name, limit)
```

- [ ] **Step 4: Register dataset routes**

Replace `backend/app/main.py` with:

```python
from fastapi import FastAPI

from app.api.datasets import router as datasets_router
from app.api.projects import router as projects_router


app = FastAPI(title="Local Data Science Agent")
app.include_router(projects_router)
app.include_router(datasets_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 5: Run all backend tests and verify they pass**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
```

Expected: PASS for all tests.

- [ ] **Step 6: Commit Task 7**

Run:

```powershell
git add backend/app/api/datasets.py backend/app/main.py backend/tests/test_dataset_upload_api.py
git commit -m "feat: expose dataset upload api"
```

---

### Task 8: Manual Backend Smoke Check

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Start the backend server**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Expected: server starts on `http://127.0.0.1:8000`.

- [ ] **Step 2: Verify health endpoint from another shell**

Run:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
```

Expected:

```text
status
------
ok
```

- [ ] **Step 3: Update README with backend commands**

Replace `README.md` with:

````markdown
# Local Data Science Agent

This repository contains a local, single-user, hybrid data science agent workspace.

## Backend Development

Create the backend environment:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

Run tests:

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
```

Run the API server:

```powershell
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

The health endpoint is available at:

```text
http://127.0.0.1:8000/health
```
````

- [ ] **Step 4: Run final verification**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
git status -sb
```

Expected:

```text
all tests pass
README.md is modified
```

- [ ] **Step 5: Commit Task 8**

Run:

```powershell
git add README.md
git commit -m "docs: add backend development commands"
```

---

## Self-Review Checklist

Spec coverage for this phase:

- Local FastAPI backend: covered by Tasks 1, 4, and 7.
- SQLite metadata: covered by Task 3.
- Local workspace paths: covered by Task 2.
- CSV upload: covered by Tasks 6 and 7.
- Profiler: covered by Task 5.
- DuckDB preview: covered by Tasks 6 and 7.
- Test strategy: covered by every task.

Spec items intentionally outside this phase:

- React workspace.
- LLM provider adapter.
- Agent orchestrator.
- SQL database connectors.
- Cleaning version chain.
- Statistical analysis and modeling.
- Report generation.
- Docker runtime adapter.

Placeholder scan:

- Do not leave placeholder comments in code.
- Do not commit generated `.data-agent/`, `work/`, `.venv/`, or cache files.
- Do not use `git add -A`; stage the exact files listed in each task.

Type consistency:

- Project ids use `proj_` prefix.
- Dataset ids use `ds_` prefix.
- Dataset profile shape uses `row_count`, `column_count`, and `columns`.
- Preview shape uses `columns` and `rows`.
- API dependency name is `get_session`.

Final verification command:

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
```

Expected final backend state:

```text
Health endpoint returns {"status": "ok"}.
Project API creates and reads projects.
CSV ingestion stores upload files under the local workspace.
CSV ingestion creates DuckDB tables.
Dataset profile endpoint returns row, column, and column profile metadata.
Dataset preview endpoint returns JSON rows from DuckDB.
```
