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
