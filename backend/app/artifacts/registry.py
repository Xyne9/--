import json
import mimetypes
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from app.core.config import AppSettings
from app.storage.models import Artifact


def index_step_artifacts(
    session: Session,
    *,
    run_id: str,
    step_id: str,
    artifacts_dir: Path,
    workspace_root: Path,
) -> list[Artifact]:
    existing = session.exec(select(Artifact).where(Artifact.step_id == step_id)).all()
    for artifact in existing:
        session.delete(artifact)

    indexed: list[Artifact] = []
    if artifacts_dir.exists():
        for path in sorted(artifacts_dir.iterdir()):
            if not path.is_file():
                continue
            artifact = Artifact(
                run_id=run_id,
                step_id=step_id,
                name=path.name,
                artifact_type=artifact_type_for_path(path),
                mime_type=mime_type_for_path(path),
                uri=workspace_relative_uri(path, workspace_root),
                size_bytes=path.stat().st_size,
            )
            session.add(artifact)
            indexed.append(artifact)

    session.commit()
    for artifact in indexed:
        session.refresh(artifact)
    return indexed


def list_run_artifacts(session: Session, run_id: str) -> list[Artifact]:
    statement = select(Artifact).where(Artifact.run_id == run_id).order_by(Artifact.created_at, Artifact.name)
    return list(session.exec(statement).all())


def get_artifact(session: Session, artifact_id: str) -> Artifact | None:
    return session.get(Artifact, artifact_id)


def read_artifact_content(settings: AppSettings, artifact: Artifact) -> Any:
    path = artifact_path(settings, artifact)
    if artifact.mime_type == "application/json":
        return json.loads(path.read_text(encoding="utf-8"))
    if artifact.mime_type.startswith("text/") or artifact.artifact_type == "report":
        return path.read_text(encoding="utf-8")
    return {"uri": artifact.uri}


def artifact_path(settings: AppSettings, artifact: Artifact) -> Path:
    workspace_root = settings.workspace_root.resolve()
    path = (workspace_root / artifact.uri).resolve()
    if path != workspace_root and workspace_root not in path.parents:
        raise ValueError("Artifact path escapes workspace")
    return path


def workspace_relative_uri(path: Path, workspace_root: Path) -> str:
    return path.resolve().relative_to(workspace_root.resolve()).as_posix()


def artifact_type_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix in {".md", ".markdown", ".html", ".htm"}:
        return "report"
    if suffix in {".png", ".jpg", ".jpeg", ".svg", ".webp"}:
        return "image"
    if suffix in {".csv", ".parquet", ".xlsx"}:
        return "table"
    if suffix in {".pkl", ".joblib", ".onnx"}:
        return "model"
    return "file"


def mime_type_for_path(path: Path) -> str:
    if path.suffix.lower() in {".md", ".markdown"}:
        return "text/markdown"
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"
