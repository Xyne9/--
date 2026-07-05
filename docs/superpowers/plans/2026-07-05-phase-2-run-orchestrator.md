# Phase 2 Run Orchestrator Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first Agent run skeleton: users can create an analysis run for a dataset, receive a deterministic plan, inspect run details, and read run events.

**Architecture:** This phase extends the Phase 1 backend with run and step metadata in SQLite. A deterministic planner generates safe, non-LLM plans from dataset metadata so the API shape is stable before adding LLM planning and execution.

**Tech Stack:** Python 3.11+, FastAPI, SQLModel, SQLite, pytest.

---

## Scope

This plan implements:

- `AnalysisRun` and `ExecutionStep` metadata models.
- Registry functions for creating and reading runs.
- A deterministic planner that creates a profile/EDA-oriented plan from a dataset.
- `POST /api/runs`, `GET /api/runs/{run_id}`, and `GET /api/runs/{run_id}/events`.
- Tests covering run creation, missing datasets, run details, and event output.

This plan does not execute generated code, call an LLM, stream live background jobs, or implement plan approval. It creates the stable run contract needed for those phases.

## File Structure

Create or modify these files:

```text
backend/app/agents/__init__.py
backend/app/agents/planner.py
backend/app/api/runs.py
backend/app/datasets/registry.py
backend/app/main.py
backend/app/storage/models.py
backend/tests/test_runs_api.py
```

Responsibilities:

- `backend/app/storage/models.py`: Add persisted run and step models.
- `backend/app/datasets/registry.py`: Add run and step persistence helpers.
- `backend/app/agents/planner.py`: Generate deterministic steps from a dataset and user goal.
- `backend/app/api/runs.py`: Expose run creation, run detail, and event endpoints.
- `backend/app/main.py`: Register the runs router.
- `backend/tests/test_runs_api.py`: Verify public API behavior.

---

### Task 1: Run And Step Models

**Files:**
- Modify: `backend/app/storage/models.py`
- Modify: `backend/app/datasets/registry.py`
- Create: `backend/tests/test_runs_api.py`

- [ ] **Step 1: Write failing registry tests**

Create `backend/tests/test_runs_api.py` with:

```python
from app.datasets.registry import create_analysis_run, create_execution_step, create_project, get_run


def test_create_run_and_steps(db_session):
    project = create_project(db_session, "Run Project")

    run = create_analysis_run(
        db_session,
        project_id=project.id,
        dataset_id="ds_example",
        user_goal="Summarize this dataset",
        status="PLAN_DRAFTED",
    )
    step = create_execution_step(
        db_session,
        run_id=run.id,
        sequence=1,
        title="Profile dataset",
        kind="profile",
        status="pending",
    )

    loaded = get_run(db_session, run.id)

    assert loaded is not None
    assert loaded.id.startswith("run_")
    assert step.id.startswith("step_")
    assert loaded.user_goal == "Summarize this dataset"
```

- [ ] **Step 2: Run the registry test and verify it fails**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_runs_api.py::test_create_run_and_steps -q
```

Expected: FAIL because run models and registry functions do not exist.

- [ ] **Step 3: Add SQLModel models**

Append to `backend/app/storage/models.py`:

```python
class AnalysisRun(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("run"), primary_key=True)
    project_id: str = Field(foreign_key="project.id", index=True)
    dataset_id: str = Field(foreign_key="dataset.id", index=True)
    user_goal: str
    status: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ExecutionStep(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("step"), primary_key=True)
    run_id: str = Field(foreign_key="analysisrun.id", index=True)
    sequence: int
    title: str
    kind: str
    status: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
```

- [ ] **Step 4: Add registry functions**

Append to `backend/app/datasets/registry.py`:

```python
from app.storage.models import AnalysisRun, ExecutionStep


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
```

- [ ] **Step 5: Run the registry test and verify it passes**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_runs_api.py::test_create_run_and_steps -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 1**

Run:

```powershell
git add backend/app/storage/models.py backend/app/datasets/registry.py backend/tests/test_runs_api.py
git commit -m "feat: add run metadata registry"
```

---

### Task 2: Deterministic Planner

**Files:**
- Create: `backend/app/agents/__init__.py`
- Create: `backend/app/agents/planner.py`
- Modify: `backend/tests/test_runs_api.py`

- [ ] **Step 1: Add failing planner test**

Append to `backend/tests/test_runs_api.py`:

```python
from app.agents.planner import generate_initial_plan


def test_generate_initial_plan_uses_dataset_profile():
    plan = generate_initial_plan(
        user_goal="Find churn drivers",
        dataset_name="customers.csv",
        profile={
            "row_count": 3,
            "column_count": 2,
            "columns": [
                {"name": "customer_id", "logical_type": "integer"},
                {"name": "churn", "logical_type": "integer"},
            ],
        },
    )

    assert plan["goal"] == "Find churn drivers"
    assert plan["dataset_name"] == "customers.csv"
    assert [step["kind"] for step in plan["steps"]] == ["profile", "eda", "summary"]
    assert plan["steps"][0]["title"] == "Review dataset profile"
```

- [ ] **Step 2: Run the planner test and verify it fails**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_runs_api.py::test_generate_initial_plan_uses_dataset_profile -q
```

Expected: FAIL because planner module does not exist.

- [ ] **Step 3: Implement deterministic planner**

Create `backend/app/agents/__init__.py` with:

```python
"""Agent planning and orchestration modules."""
```

Create `backend/app/agents/planner.py` with:

```python
from typing import Any


def generate_initial_plan(
    *,
    user_goal: str,
    dataset_name: str,
    profile: dict[str, Any],
) -> dict[str, Any]:
    row_count = profile["row_count"]
    column_count = profile["column_count"]
    column_names = [column["name"] for column in profile["columns"]]

    return {
        "goal": user_goal,
        "dataset_name": dataset_name,
        "context": {
            "row_count": row_count,
            "column_count": column_count,
            "columns": column_names,
        },
        "steps": [
            {
                "sequence": 1,
                "title": "Review dataset profile",
                "kind": "profile",
                "status": "pending",
            },
            {
                "sequence": 2,
                "title": "Identify exploratory analysis angles",
                "kind": "eda",
                "status": "pending",
            },
            {
                "sequence": 3,
                "title": "Summarize initial findings and next actions",
                "kind": "summary",
                "status": "pending",
            },
        ],
    }
```

- [ ] **Step 4: Run planner test and verify it passes**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_runs_api.py::test_generate_initial_plan_uses_dataset_profile -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

Run:

```powershell
git add backend/app/agents backend/tests/test_runs_api.py
git commit -m "feat: add deterministic run planner"
```

---

### Task 3: Runs API

**Files:**
- Create: `backend/app/api/runs.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_runs_api.py`

- [ ] **Step 1: Add failing API tests**

Append to `backend/tests/test_runs_api.py`:

```python
from fastapi.testclient import TestClient

from app.api.deps import get_session
from app.core.config import build_settings, ensure_workspace, get_settings
from app.datasets.ingestion import ingest_csv_dataset
from app.main import app


def create_sample_dataset(db_session, tmp_path):
    settings = ensure_workspace(build_settings(str(tmp_path / "workspace")))
    get_settings.cache_clear()
    project = create_project(db_session, "Runs API Project")
    csv_path = tmp_path / "customers.csv"
    csv_path.write_text("customer_id,churn\n1,0\n2,1\n", encoding="utf-8")
    dataset = ingest_csv_dataset(
        session=db_session,
        settings=settings,
        project_id=project.id,
        source_path=csv_path,
        original_name="customers.csv",
    )
    return project, dataset


def test_create_run_api_returns_plan_and_steps(db_session, tmp_path):
    project, dataset = create_sample_dataset(db_session, tmp_path)
    app.dependency_overrides[get_session] = lambda: db_session
    client = TestClient(app)

    try:
        response = client.post(
            "/api/runs",
            json={
                "project_id": project.id,
                "dataset_id": dataset.id,
                "user_goal": "Find churn drivers",
            },
        )
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

    assert response.status_code == 201
    body = response.json()
    assert body["id"].startswith("run_")
    assert body["status"] == "PLAN_DRAFTED"
    assert [step["kind"] for step in body["steps"]] == ["profile", "eda", "summary"]


def test_get_run_api_returns_steps(db_session, tmp_path):
    project, dataset = create_sample_dataset(db_session, tmp_path)
    app.dependency_overrides[get_session] = lambda: db_session
    client = TestClient(app)

    try:
        created = client.post(
            "/api/runs",
            json={
                "project_id": project.id,
                "dataset_id": dataset.id,
                "user_goal": "Find churn drivers",
            },
        ).json()
        response = client.get(f"/api/runs/{created['id']}")
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert len(response.json()["steps"]) == 3


def test_create_run_api_rejects_missing_dataset(db_session):
    project = create_project(db_session, "Runs API Project")
    app.dependency_overrides[get_session] = lambda: db_session
    client = TestClient(app)

    try:
        response = client.post(
            "/api/runs",
            json={
                "project_id": project.id,
                "dataset_id": "ds_missing",
                "user_goal": "Find churn drivers",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
```

- [ ] **Step 2: Run API tests and verify they fail**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_runs_api.py::test_create_run_api_returns_plan_and_steps -q
```

Expected: FAIL because `/api/runs` is not registered.

- [ ] **Step 3: Implement runs API**

Create `backend/app/api/runs.py` with:

```python
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from app.agents.planner import generate_initial_plan
from app.api.deps import get_session
from app.datasets.registry import (
    create_analysis_run,
    create_execution_step,
    get_dataset,
    get_dataset_profile,
    get_project,
    get_run,
    list_run_steps,
)


router = APIRouter(prefix="/api/runs", tags=["runs"])


class CreateRunRequest(BaseModel):
    project_id: str
    dataset_id: str
    user_goal: str


class StepResponse(BaseModel):
    id: str
    sequence: int
    title: str
    kind: str
    status: str


class RunResponse(BaseModel):
    id: str
    project_id: str
    dataset_id: str
    user_goal: str
    status: str
    steps: list[StepResponse]


def to_run_response(session: Session, run_id: str) -> RunResponse:
    run = get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    steps = list_run_steps(session, run.id)
    return RunResponse(
        id=run.id,
        project_id=run.project_id,
        dataset_id=run.dataset_id,
        user_goal=run.user_goal,
        status=run.status,
        steps=[
            StepResponse(
                id=step.id,
                sequence=step.sequence,
                title=step.title,
                kind=step.kind,
                status=step.status,
            )
            for step in steps
        ],
    )


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def create_run_endpoint(
    request: CreateRunRequest,
    session: Session = Depends(get_session),
) -> RunResponse:
    if get_project(session, request.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    dataset = get_dataset(session, request.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    profile = get_dataset_profile(session, dataset.id)
    plan = generate_initial_plan(
        user_goal=request.user_goal,
        dataset_name=dataset.name,
        profile=profile,
    )
    run = create_analysis_run(
        session,
        project_id=request.project_id,
        dataset_id=request.dataset_id,
        user_goal=request.user_goal,
        status="PLAN_DRAFTED",
    )
    for step in plan["steps"]:
        create_execution_step(
            session,
            run_id=run.id,
            sequence=step["sequence"],
            title=step["title"],
            kind=step["kind"],
            status=step["status"],
        )
    return to_run_response(session, run.id)


@router.get("/{run_id}", response_model=RunResponse)
def get_run_endpoint(
    run_id: str,
    session: Session = Depends(get_session),
) -> RunResponse:
    return to_run_response(session, run_id)
```

- [ ] **Step 4: Register runs router**

Modify `backend/app/main.py` to include:

```python
from app.api.runs import router as runs_router

app.include_router(runs_router)
```

- [ ] **Step 5: Run runs API tests and verify they pass**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_runs_api.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 3**

Run:

```powershell
git add backend/app/api/runs.py backend/app/main.py backend/tests/test_runs_api.py
git commit -m "feat: expose run planning api"
```

---

### Task 4: Run Events Endpoint

**Files:**
- Modify: `backend/app/api/runs.py`
- Modify: `backend/tests/test_runs_api.py`

- [ ] **Step 1: Add failing events test**

Append to `backend/tests/test_runs_api.py`:

```python
def test_run_events_api_returns_created_and_step_events(db_session, tmp_path):
    project, dataset = create_sample_dataset(db_session, tmp_path)
    app.dependency_overrides[get_session] = lambda: db_session
    client = TestClient(app)

    try:
        created = client.post(
            "/api/runs",
            json={
                "project_id": project.id,
                "dataset_id": dataset.id,
                "user_goal": "Find churn drivers",
            },
        ).json()
        response = client.get(f"/api/runs/{created['id']}/events")
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

    assert response.status_code == 200
    assert response.json()["events"][0]["type"] == "run.created"
    assert response.json()["events"][1]["type"] == "plan.generated"
    assert response.json()["events"][2]["type"] == "step.created"
```

- [ ] **Step 2: Run events test and verify it fails**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_runs_api.py::test_run_events_api_returns_created_and_step_events -q
```

Expected: FAIL because run events endpoint does not exist.

- [ ] **Step 3: Implement events endpoint**

Append to `backend/app/api/runs.py`:

```python
@router.get("/{run_id}/events")
def get_run_events_endpoint(
    run_id: str,
    session: Session = Depends(get_session),
) -> dict[str, list[dict[str, Any]]]:
    run = get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    steps = list_run_steps(session, run.id)
    events: list[dict[str, Any]] = [
        {"type": "run.created", "run_id": run.id, "status": run.status},
        {"type": "plan.generated", "run_id": run.id, "step_count": len(steps)},
    ]
    for step in steps:
        events.append(
            {
                "type": "step.created",
                "run_id": run.id,
                "step_id": step.id,
                "sequence": step.sequence,
                "title": step.title,
                "kind": step.kind,
                "status": step.status,
            }
        )
    return {"events": events}
```

- [ ] **Step 4: Run all backend tests and verify they pass**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 4**

Run:

```powershell
git add backend/app/api/runs.py backend/tests/test_runs_api.py
git commit -m "feat: expose run events api"
```

---

## Self-Review Checklist

Spec coverage for this phase:

- Agent workflow run state: covered by Tasks 1 and 3.
- Structured plan generation: covered by Task 2.
- Run API contract: covered by Task 3.
- Run events: covered by Task 4.

Spec items intentionally outside this phase:

- LLM planning.
- Code execution.
- Step verification.
- Plan approval.
- SSE streaming.
- Frontend workspace.

Final verification command:

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
```

Expected final backend state:

```text
All existing Phase 1 tests pass.
Run registry can persist runs and execution steps.
POST /api/runs creates a PLAN_DRAFTED run with three deterministic steps.
GET /api/runs/{run_id} returns run metadata and steps.
GET /api/runs/{run_id}/events returns run and step event JSON.
```

