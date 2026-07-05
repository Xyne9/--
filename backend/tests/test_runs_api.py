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
