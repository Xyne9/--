from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.api.deps import get_session
from app.artifacts.registry import get_artifact, read_artifact_content
from app.core.config import AppSettings, get_settings
from app.storage.models import Artifact


router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


class ArtifactResponse(BaseModel):
    id: str
    run_id: str
    step_id: str
    name: str
    artifact_type: str
    mime_type: str
    uri: str
    size_bytes: int


class ArtifactDetailResponse(ArtifactResponse):
    content: Any


def to_artifact_response(artifact: Artifact) -> ArtifactResponse:
    return ArtifactResponse(
        id=artifact.id,
        run_id=artifact.run_id,
        step_id=artifact.step_id,
        name=artifact.name,
        artifact_type=artifact.artifact_type,
        mime_type=artifact.mime_type,
        uri=artifact.uri,
        size_bytes=artifact.size_bytes,
    )


@router.get("/{artifact_id}", response_model=ArtifactDetailResponse)
def get_artifact_endpoint(
    artifact_id: str,
    session: Session = Depends(get_session),
    settings: AppSettings = Depends(get_settings),
) -> ArtifactDetailResponse:
    artifact = get_artifact(session, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    try:
        content = read_artifact_content(settings, artifact)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="Artifact content not found") from exc
    return ArtifactDetailResponse(
        id=artifact.id,
        run_id=artifact.run_id,
        step_id=artifact.step_id,
        name=artifact.name,
        artifact_type=artifact.artifact_type,
        mime_type=artifact.mime_type,
        uri=artifact.uri,
        size_bytes=artifact.size_bytes,
        content=content,
    )
