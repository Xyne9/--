from fastapi.testclient import TestClient

from app.api.deps import get_session
from app.core.config import build_settings, ensure_workspace, get_settings
from app.datasets.ingestion import ingest_csv_dataset
from app.datasets.registry import create_project
from app.main import app


def create_executed_run(db_session, tmp_path):
    settings = ensure_workspace(build_settings(str(tmp_path / "workspace")))
    project = create_project(db_session, "Artifacts Project")
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

    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    created = client.post(
        "/api/runs",
        json={
            "project_id": project.id,
            "dataset_id": dataset.id,
            "user_goal": "Understand churn drivers",
        },
    ).json()
    executed = client.post(
        f"/api/runs/{created['id']}/execute",
        json={"timeout_seconds": 5.0},
    )
    assert executed.status_code == 200
    return client, created


def test_run_artifacts_api_lists_indexed_step_outputs(db_session, tmp_path):
    try:
        client, created = create_executed_run(db_session, tmp_path)
        response = client.get(f"/api/runs/{created['id']}/artifacts")
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

    assert response.status_code == 200
    artifacts = response.json()["artifacts"]
    names = {artifact["name"] for artifact in artifacts}
    assert names == {"profile_summary.json", "eda_summary.json", "summary_report.md"}
    assert {artifact["run_id"] for artifact in artifacts} == {created["id"]}
    assert all(artifact["id"].startswith("artifact_") for artifact in artifacts)
    assert all(artifact["step_id"].startswith("step_") for artifact in artifacts)
    assert all(artifact["size_bytes"] > 0 for artifact in artifacts)
    assert all(artifact["uri"].startswith(f"runs/{created['id']}/steps/") for artifact in artifacts)


def test_artifact_detail_api_returns_json_and_text_content(db_session, tmp_path):
    try:
        client, created = create_executed_run(db_session, tmp_path)
        artifacts = client.get(f"/api/runs/{created['id']}/artifacts").json()["artifacts"]
        profile = next(artifact for artifact in artifacts if artifact["name"] == "profile_summary.json")
        report = next(artifact for artifact in artifacts if artifact["name"] == "summary_report.md")

        profile_response = client.get(f"/api/artifacts/{profile['id']}")
        report_response = client.get(f"/api/artifacts/{report['id']}")
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

    assert profile_response.status_code == 200
    profile_body = profile_response.json()
    assert profile_body["name"] == "profile_summary.json"
    assert profile_body["artifact_type"] == "json"
    assert profile_body["mime_type"] == "application/json"
    assert profile_body["content"]["row_count"] == 3
    assert profile_body["content"]["column_count"] == 3

    assert report_response.status_code == 200
    report_body = report_response.json()
    assert report_body["name"] == "summary_report.md"
    assert report_body["artifact_type"] == "report"
    assert report_body["mime_type"] == "text/markdown"
    assert "Analysis Run Summary" in report_body["content"]
