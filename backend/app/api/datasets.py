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
    try:
        dataset = ingest_csv_dataset(
            session=session,
            settings=settings,
            project_id=project_id,
            source_path=temp_path,
            original_name=file.filename,
        )
    finally:
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
