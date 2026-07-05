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


def create_run_via_api(client, project_id, dataset_id, user_goal="Find churn drivers"):
    response = client.post(
        "/api/runs",
        json={
            "project_id": project_id,
            "dataset_id": dataset_id,
            "user_goal": user_goal,
        },
    )
    assert response.status_code == 201
    return response.json()


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
        created = create_run_via_api(client, project.id, dataset.id)
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


def test_run_events_api_returns_created_and_step_events(db_session, tmp_path):
    project, dataset = create_sample_dataset(db_session, tmp_path)
    app.dependency_overrides[get_session] = lambda: db_session
    client = TestClient(app)

    try:
        created = create_run_via_api(client, project.id, dataset.id)
        response = client.get(f"/api/runs/{created['id']}/events")
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

    assert response.status_code == 200
    assert response.json()["events"][0]["type"] == "run.created"
    assert response.json()["events"][1]["type"] == "plan.generated"
    assert response.json()["events"][2]["type"] == "step.created"


def test_execute_step_api_runs_code_and_persists_result(db_session, tmp_path):
    project, dataset = create_sample_dataset(db_session, tmp_path)
    settings = ensure_workspace(build_settings(str(tmp_path / "workspace")))
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)

    try:
        created = create_run_via_api(client, project.id, dataset.id)
        step_id = created["steps"][0]["id"]

        response = client.post(
            f"/api/runs/{created['id']}/steps/{step_id}/execute",
            json={"code": "print('hello step')", "timeout_seconds": 2.0},
        )
        loaded = client.get(f"/api/runs/{created['id']}").json()
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == created["id"]
    assert body["step_id"] == step_id
    assert body["status"] == "completed"
    assert body["exit_code"] == 0
    assert body["stdout"].strip() == "hello step"
    assert body["stderr"] == ""
    assert body["workdir"].endswith(f"runs\\{created['id']}\\steps\\{step_id}") or body[
        "workdir"
    ].endswith(f"runs/{created['id']}/steps/{step_id}")
    assert body["artifacts_dir"].endswith("artifacts")
    assert body["duration_seconds"] >= 0

    persisted_step = loaded["steps"][0]
    assert persisted_step["status"] == "completed"
    assert persisted_step["exit_code"] == 0
    assert persisted_step["stdout"].strip() == "hello step"
    assert persisted_step["stderr"] == ""
    assert persisted_step["duration_seconds"] >= 0


def test_execute_step_api_persists_failed_code(db_session, tmp_path):
    project, dataset = create_sample_dataset(db_session, tmp_path)
    settings = ensure_workspace(build_settings(str(tmp_path / "workspace")))
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)

    try:
        created = create_run_via_api(client, project.id, dataset.id)
        step_id = created["steps"][0]["id"]

        response = client.post(
            f"/api/runs/{created['id']}/steps/{step_id}/execute",
            json={"code": "raise SystemExit(7)", "timeout_seconds": 2.0},
        )
        loaded = client.get(f"/api/runs/{created['id']}").json()
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["exit_code"] == 7
    assert loaded["steps"][0]["status"] == "failed"
    assert loaded["steps"][0]["exit_code"] == 7


def test_execute_step_api_persists_timeout(db_session, tmp_path):
    project, dataset = create_sample_dataset(db_session, tmp_path)
    settings = ensure_workspace(build_settings(str(tmp_path / "workspace")))
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)

    try:
        created = create_run_via_api(client, project.id, dataset.id)
        step_id = created["steps"][0]["id"]

        response = client.post(
            f"/api/runs/{created['id']}/steps/{step_id}/execute",
            json={
                "code": "import time\ntime.sleep(2)",
                "timeout_seconds": 0.1,
            },
        )
        loaded = client.get(f"/api/runs/{created['id']}").json()
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

    assert response.status_code == 200
    assert response.json()["status"] == "timeout"
    assert response.json()["exit_code"] is None
    assert loaded["steps"][0]["status"] == "timeout"
    assert loaded["steps"][0]["duration_seconds"] < 2.0


def test_execute_step_api_rejects_missing_run(db_session, tmp_path):
    project, dataset = create_sample_dataset(db_session, tmp_path)
    settings = ensure_workspace(build_settings(str(tmp_path / "workspace")))
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)

    try:
        created = create_run_via_api(client, project.id, dataset.id)
        step_id = created["steps"][0]["id"]
        response = client.post(
            f"/api/runs/run_missing/steps/{step_id}/execute",
            json={"code": "print('nope')", "timeout_seconds": 2.0},
        )
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Run not found"


def test_execute_step_api_rejects_step_from_another_run(db_session, tmp_path):
    project, dataset = create_sample_dataset(db_session, tmp_path)
    settings = ensure_workspace(build_settings(str(tmp_path / "workspace")))
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)

    try:
        first_run = create_run_via_api(client, project.id, dataset.id, "First goal")
        second_run = create_run_via_api(client, project.id, dataset.id, "Second goal")
        foreign_step_id = second_run["steps"][0]["id"]

        response = client.post(
            f"/api/runs/{first_run['id']}/steps/{foreign_step_id}/execute",
            json={"code": "print('nope')", "timeout_seconds": 2.0},
        )
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Step not found"


def test_execute_step_api_rejects_non_positive_timeout(db_session, tmp_path):
    project, dataset = create_sample_dataset(db_session, tmp_path)
    settings = ensure_workspace(build_settings(str(tmp_path / "workspace")))
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)

    try:
        created = create_run_via_api(client, project.id, dataset.id)
        step_id = created["steps"][0]["id"]

        response = client.post(
            f"/api/runs/{created['id']}/steps/{step_id}/execute",
            json={"code": "print('nope')", "timeout_seconds": 0},
        )
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

    assert response.status_code == 422


def test_run_events_api_includes_step_execution_event(db_session, tmp_path):
    project, dataset = create_sample_dataset(db_session, tmp_path)
    settings = ensure_workspace(build_settings(str(tmp_path / "workspace")))
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)

    try:
        created = create_run_via_api(client, project.id, dataset.id)
        step_id = created["steps"][0]["id"]
        client.post(
            f"/api/runs/{created['id']}/steps/{step_id}/execute",
            json={"code": "print('event ready')", "timeout_seconds": 2.0},
        )

        response = client.get(f"/api/runs/{created['id']}/events")
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

    assert response.status_code == 200
    events = response.json()["events"]
    executed_events = [event for event in events if event["type"] == "step.executed"]
    assert executed_events == [
        {
            "type": "step.executed",
            "run_id": created["id"],
            "step_id": step_id,
            "status": "completed",
            "exit_code": 0,
        }
    ]
