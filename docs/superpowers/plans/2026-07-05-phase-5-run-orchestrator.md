# Phase 5 Run Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute a whole analysis run end to end by generating deterministic Python code for each planned step and running it through the existing local runtime.

**Architecture:** Add a small backend orchestrator that reads a run, its dataset, and ordered steps, generates first-version Python scripts for `profile`, `eda`, and `summary` step kinds, executes them with `LocalPythonRuntime`, records step code/results, and updates the run status. This does not introduce LLM code generation yet; it creates the state-machine surface that the LLM adapter can later call into.

**Tech Stack:** FastAPI, Pydantic, SQLModel, SQLite metadata, DuckDB, local Python runtime, pytest.

---

### Task 1: Test Full Run Execution Contract

**Files:**
- Create: `backend/tests/test_run_orchestrator_api.py`

- [x] **Step 1: Write failing end-to-end API test**

Add a test for `POST /api/runs/{run_id}/execute` that creates a CSV-backed dataset, creates a run, executes it, and expects:

```python
assert response.status_code == 200
assert body["run_id"] == created_run["id"]
assert body["status"] == "COMPLETED"
assert len(body["steps"]) == 3
assert {step["status"] for step in body["steps"]} == {"completed"}
```

- [x] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python -m pytest tests\test_run_orchestrator_api.py::test_execute_run_api_runs_all_steps_and_marks_run_completed -q`

Expected: FAIL because the run-level execute endpoint does not exist.

### Task 2: Persist Generated Step Code And Run Status

**Files:**
- Modify: `backend/app/storage/models.py`
- Modify: `backend/app/datasets/registry.py`
- Modify: `backend/app/api/runs.py`
- Test: `backend/tests/test_runs_api.py`

- [x] **Step 1: Add `ExecutionStep.code`**

Add `code: str = ""` so generated or user-submitted code appears in the workspace API.

- [x] **Step 2: Update step responses**

Return `code` from `StepResponse`.

- [x] **Step 3: Store code when executing a single step**

Extend `record_step_execution_result()` with `code: str | None = None` and pass `request.code` from the single-step endpoint.

- [x] **Step 4: Add run status helper**

Add `update_run_status(session, run, status)` to update `AnalysisRun.status` and `updated_at`.

### Task 3: Implement Deterministic Orchestrator

**Files:**
- Create: `backend/app/agents/orchestrator.py`
- Modify: `backend/app/api/runs.py`
- Test: `backend/tests/test_run_orchestrator_api.py`

- [x] **Step 1: Add generated code templates**

Generate local Python scripts for:

```text
profile -> writes artifacts/profile_summary.json
eda -> writes artifacts/eda_summary.json
summary -> writes artifacts/summary_report.md
```

- [x] **Step 2: Execute ordered steps**

For each step, build `ExecutionRequest`, execute via `LocalPythonRuntime`, and persist result plus generated code.

- [x] **Step 3: Add run endpoint**

Add `POST /api/runs/{run_id}/execute` with a positive `timeout_seconds` request field.

- [x] **Step 4: Mark run final status**

Set run status to `COMPLETED` if all steps complete, otherwise `FAILED`.

### Task 4: Events And Validation

**Files:**
- Modify: `backend/app/api/runs.py`
- Test: `backend/tests/test_run_orchestrator_api.py`

- [x] **Step 1: Add missing run and invalid timeout tests**

Expect `404` for missing run and `422` for non-positive timeout.

- [x] **Step 2: Add run completion event test**

After run execution, `/api/runs/{run_id}/events` should include:

```json
{"type": "run.completed", "run_id": "...", "status": "COMPLETED"}
```

- [x] **Step 3: Update events**

Append `run.completed` or `run.failed` based on final run status.

- [x] **Step 4: Run all backend tests**

Run: `.\.venv\Scripts\python -m pytest -q`

Expected: all tests pass.

### Self-Review

- Spec coverage: This phase implements the first state-machine execution surface without LLM code generation, artifact indexing, or frontend rendering.
- Placeholder scan: No TODO/TBD placeholders remain.
- Type consistency: Run execution responses reuse the single-step execution response fields.
