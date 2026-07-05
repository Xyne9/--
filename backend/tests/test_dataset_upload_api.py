from pathlib import Path

from fastapi.testclient import TestClient

from app.api.deps import get_session
from app.core.config import build_settings, ensure_workspace, get_settings
from app.datasets.ingestion import ingest_csv_dataset
from app.datasets.registry import create_project, get_dataset_profile, preview_dataset
from app.main import app


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


def test_upload_profile_and_preview_api(db_session, tmp_path, monkeypatch):
    settings = ensure_workspace(build_settings(str(tmp_path / "workspace")))
    monkeypatch.setenv("DATA_AGENT_WORKSPACE", str(settings.workspace_root))
    get_settings.cache_clear()
    project = create_project(db_session, "Upload API Project")
    app.dependency_overrides[get_session] = lambda: db_session
    client = TestClient(app)

    try:
        upload_response = client.post(
            "/api/datasets/upload",
            data={"project_id": project.id},
            files={"file": ("customers.csv", b"customer_id,churn\n1,0\n2,1\n", "text/csv")},
        )

        assert upload_response.status_code == 201
        dataset_id = upload_response.json()["id"]

        profile_response = client.get(f"/api/datasets/{dataset_id}/profile")
        preview_response = client.get(f"/api/datasets/{dataset_id}/preview?limit=1")
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

    assert profile_response.status_code == 200
    assert profile_response.json()["row_count"] == 2
    assert preview_response.status_code == 200
    assert preview_response.json()["rows"] == [{"customer_id": 1, "churn": 0}]
