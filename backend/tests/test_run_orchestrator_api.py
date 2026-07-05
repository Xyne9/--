from pathlib import Path

from fastapi.testclient import TestClient

from app.api.deps import get_session
from app.core.config import build_settings, ensure_workspace, get_settings
from app.datasets.ingestion import ingest_csv_dataset
from app.datasets.registry import create_project
from app.main import app


def create_dataset_for_run(db_session, tmp_path):
    settings = ensure_workspace(build_settings(str(tmp_path / "workspace")))
    project = create_project(db_session, "Run Orchestrator Project")
    csv_path = tmp_path / "customers.csv"
    csv_path.write_text(
        "customer_id,churn,monthly_spend\n1,0,12.5\n2,1,31.0\n3,0,22.0\n",
        encoding="utf-8",
    )
    dataset = ingest_csv_dataset(
        session=db_session,
        settings=settings,
        project_id=project.id,
        source_path=csv_path,
        original_name="customers.csv",
    )
    return settings, project, dataset


def create_run(client, project_id, dataset_id):
    response = client.post(
        "/api/runs",
        json={
            "project_id": project_id,
            "dataset_id": dataset_id,
            "user_goal": "Understand churn drivers",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_execute_run_api_runs_all_steps_and_marks_run_completed(db_session, tmp_path):
    settings, project, dataset = create_dataset_for_run(db_session, tmp_path)
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)

    try:
        created = create_run(client, project.id, dataset.id)
        response = client.post(
            f"/api/runs/{created['id']}/execute",
            json={"timeout_seconds": 5.0},
        )
        loaded = client.get(f"/api/runs/{created['id']}").json()
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == created["id"]
    assert body["status"] == "COMPLETED"
    assert len(body["steps"]) == 3
    assert {step["status"] for step in body["steps"]} == {"completed"}
    assert all(step["code"] for step in body["steps"])

    assert loaded["status"] == "COMPLETED"
    assert {step["status"] for step in loaded["steps"]} == {"completed"}
    assert all(step["code"] for step in loaded["steps"])

    summary_artifact = Path(body["steps"][-1]["artifacts_dir"]) / "summary_report.md"
    assert summary_artifact.exists()


def test_execute_run_api_rejects_missing_run(db_session, tmp_path):
    settings, _, _ = create_dataset_for_run(db_session, tmp_path)
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)

    try:
        response = client.post(
            "/api/runs/run_missing/execute",
            json={"timeout_seconds": 5.0},
        )
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Run not found"


def test_execute_run_api_rejects_non_positive_timeout(db_session, tmp_path):
    settings, project, dataset = create_dataset_for_run(db_session, tmp_path)
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)

    try:
        created = create_run(client, project.id, dataset.id)
        response = client.post(
            f"/api/runs/{created['id']}/execute",
            json={"timeout_seconds": 0},
        )
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

    assert response.status_code == 422


def test_run_events_api_includes_run_completed_event(db_session, tmp_path):
    settings, project, dataset = create_dataset_for_run(db_session, tmp_path)
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)

    try:
        created = create_run(client, project.id, dataset.id)
        client.post(
            f"/api/runs/{created['id']}/execute",
            json={"timeout_seconds": 5.0},
        )
        response = client.get(f"/api/runs/{created['id']}/events")
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

    assert response.status_code == 200
    events = response.json()["events"]
    completed_events = [event for event in events if event["type"] == "run.completed"]
    assert completed_events == [
        {
            "type": "run.completed",
            "run_id": created["id"],
            "status": "COMPLETED",
        }
    ]
