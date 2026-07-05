from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path


@dataclass(frozen=True)
class AppSettings:
    workspace_root: Path
    sqlite_path: Path
    duckdb_path: Path
    uploads_dir: Path
    runs_dir: Path


def build_settings(workspace_root: str | None = None) -> AppSettings:
    root = Path(workspace_root or os.getenv("DATA_AGENT_WORKSPACE", ".data-agent")).resolve()
    return AppSettings(
        workspace_root=root,
        sqlite_path=root / "project.sqlite",
        duckdb_path=root / "analytics.duckdb",
        uploads_dir=root / "uploads",
        runs_dir=root / "runs",
    )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return build_settings()


def ensure_workspace(settings: AppSettings) -> AppSettings:
    settings.workspace_root.mkdir(parents=True, exist_ok=True)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.runs_dir.mkdir(parents=True, exist_ok=True)
    return settings
