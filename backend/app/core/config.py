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
    llm_provider: str
    llm_base_url: str
    llm_api_key: str | None
    llm_model: str


def build_settings(workspace_root: str | None = None) -> AppSettings:
    root = Path(workspace_root or os.getenv("DATA_AGENT_WORKSPACE", ".data-agent")).resolve()
    return AppSettings(
        workspace_root=root,
        sqlite_path=root / "project.sqlite",
        duckdb_path=root / "analytics.duckdb",
        uploads_dir=root / "uploads",
        runs_dir=root / "runs",
        llm_provider=os.getenv("LLM_PROVIDER", "openai-compatible"),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        llm_api_key=os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"),
        llm_model=os.getenv("LLM_MODEL", "gpt-4.1-mini"),
    )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return build_settings()


def ensure_workspace(settings: AppSettings) -> AppSettings:
    settings.workspace_root.mkdir(parents=True, exist_ok=True)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.runs_dir.mkdir(parents=True, exist_ok=True)
    return settings
