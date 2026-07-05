# Phase 6 Artifact Store Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Index files produced by execution steps as queryable artifacts so the backend can expose generated JSON summaries, reports, and future charts to the workspace UI.

**Architecture:** Add an `Artifact` metadata table, an artifact registry that scans a step artifact directory after execution, and API endpoints to list run artifacts and retrieve artifact content. The first version indexes local files only and replaces a step's artifact records on rerun.

**Tech Stack:** FastAPI, SQLModel, SQLite metadata, local workspace files, pytest.

---

### Task 1: Test Artifact Indexing Contract

**Files:**
- Create: `backend/tests/test_artifacts_api.py`

- [x] **Step 1: Write failing run artifact listing test**

After executing a run, `GET /api/runs/{run_id}/artifacts` should return the generated `profile_summary.json`, `eda_summary.json`, and `summary_report.md` metadata.

- [x] **Step 2: Write failing artifact content test**

`GET /api/artifacts/{artifact_id}` should return metadata plus parsed JSON content for JSON artifacts and text content for Markdown artifacts.

- [x] **Step 3: Run tests to verify they fail**

Run: `.\.venv\Scripts\python -m pytest tests\test_artifacts_api.py -q`

Expected: FAIL because artifact metadata and endpoints do not exist.

### Task 2: Add Artifact Model And Registry

**Files:**
- Modify: `backend/app/storage/models.py`
- Create: `backend/app/artifacts/__init__.py`
- Create: `backend/app/artifacts/registry.py`

- [x] **Step 1: Add `Artifact` model**

Fields:

```python
id: str
run_id: str
step_id: str
name: str
artifact_type: str
mime_type: str
uri: str
size_bytes: int
created_at: datetime
```

- [x] **Step 2: Add indexing helper**

`index_step_artifacts(session, run_id, step_id, artifacts_dir, workspace_root)` deletes prior artifacts for that step, scans files directly under `artifacts_dir`, and creates metadata rows with workspace-relative URI values.

- [x] **Step 3: Add retrieval helpers**

Add `list_run_artifacts()`, `get_artifact()`, and `read_artifact_content()`.

### Task 3: Index Artifacts During Execution

**Files:**
- Modify: `backend/app/api/runs.py`
- Modify: `backend/app/agents/orchestrator.py`

- [x] **Step 1: Index single-step artifacts**

After `record_step_execution_result()` in `POST /api/runs/{run_id}/steps/{step_id}/execute`, call `index_step_artifacts()`.

- [x] **Step 2: Index orchestrated run artifacts**

After each orchestrated step executes, index files from the runtime result artifact directory.

### Task 4: Expose Artifact APIs

**Files:**
- Create: `backend/app/api/artifacts.py`
- Modify: `backend/app/api/runs.py`
- Modify: `backend/app/main.py`

- [x] **Step 1: Add run artifact list endpoint**

`GET /api/runs/{run_id}/artifacts` returns metadata for all artifacts in run order.

- [x] **Step 2: Add artifact detail endpoint**

`GET /api/artifacts/{artifact_id}` returns metadata and content:

```json
{
  "id": "artifact_...",
  "name": "profile_summary.json",
  "artifact_type": "json",
  "mime_type": "application/json",
  "content": {"row_count": 3}
}
```

- [x] **Step 3: Run all backend tests**

Run: `.\.venv\Scripts\python -m pytest -q`

Expected: all tests pass.

### Self-Review

- Spec coverage: This phase covers first-version artifact metadata and content access, not artifact version history, chart rendering, or remote object storage.
- Placeholder scan: No TODO/TBD placeholders remain.
- Type consistency: Artifact ids use the existing `new_id()` helper pattern.
