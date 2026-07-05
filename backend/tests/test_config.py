from app.core.config import build_settings, ensure_workspace


def test_build_settings_uses_explicit_workspace_root(tmp_path):
    workspace = tmp_path / "workspace"

    settings = build_settings(str(workspace))

    assert settings.workspace_root == workspace
    assert settings.sqlite_path == workspace / "project.sqlite"
    assert settings.duckdb_path == workspace / "analytics.duckdb"
    assert settings.uploads_dir == workspace / "uploads"
    assert settings.runs_dir == workspace / "runs"


def test_ensure_workspace_creates_required_directories(tmp_path):
    settings = build_settings(str(tmp_path / "workspace"))

    ensure_workspace(settings)

    assert settings.workspace_root.exists()
    assert settings.uploads_dir.exists()
    assert settings.runs_dir.exists()
