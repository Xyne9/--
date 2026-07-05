# Phase 4 Run Execution Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect persisted `ExecutionStep` rows to the local Python runtime through a testable API endpoint.

**Architecture:** The runs API will accept Python code for a specific step, validate that the step belongs to the requested run, execute it with `LocalPythonRuntime`, persist the structured result on the step row, and return a stable response model. This is an internal Phase 4 control surface, not the final autonomous agent loop.

**Tech Stack:** FastAPI, Pydantic, SQLModel, SQLite metadata, local subprocess Python runtime, pytest.

---

### Task 1: Persist Step Execution Result Metadata

**Files:**
- Modify: `backend/app/storage/models.py`
- Modify: `backend/app/datasets/registry.py`
- Test: `backend/tests/test_runs_api.py`

- [x] **Step 1: Write failing registry/API expectations**

Add tests that expect executed steps to expose `status`, `exit_code`, `stdout`, `stderr`, `workdir`, `artifacts_dir`, and `duration_seconds`.

- [x] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python -m pytest tests\test_runs_api.py::test_execute_step_api_runs_code_and_persists_result -q`

Expected: FAIL because the execute endpoint does not exist.

- [x] **Step 3: Add nullable result fields**

Add nullable columns to `ExecutionStep`:

```python
exit_code: int | None = None
stdout: str = ""
stderr: str = ""
workdir: str | None = None
artifacts_dir: str | None = None
duration_seconds: float | None = None
```

- [x] **Step 4: Add registry helpers**

Add `get_execution_step()` and `record_step_execution_result()` helpers so API code does not mutate SQLModel rows inline.

- [x] **Step 5: Run targeted tests**

Run: `.\.venv\Scripts\python -m pytest tests\test_runs_api.py -q`

Expected: all run API tests pass.

### Task 2: Add Step Execute Endpoint

**Files:**
- Modify: `backend/app/api/runs.py`
- Test: `backend/tests/test_runs_api.py`

- [x] **Step 1: Write failing endpoint tests**

Cover success, failed code, timeout, missing run, and a step that does not belong to the run.

- [x] **Step 2: Run tests to verify they fail**

Run: `.\.venv\Scripts\python -m pytest tests\test_runs_api.py -q`

Expected: FAIL because route and result response are missing.

- [x] **Step 3: Add request/response models**

Add:

```python
class ExecuteStepRequest(BaseModel):
    code: str
    timeout_seconds: float = 30.0


class ExecuteStepResponse(BaseModel):
    run_id: str
    step_id: str
    status: str
    exit_code: int | None
    stdout: str
    stderr: str
    workdir: str
    artifacts_dir: str
    duration_seconds: float
```

- [x] **Step 4: Implement endpoint**

Validate run and step, execute with `LocalPythonRuntime`, persist result, and return `ExecuteStepResponse`.

- [x] **Step 5: Run targeted tests**

Run: `.\.venv\Scripts\python -m pytest tests\test_runs_api.py -q`

Expected: all run API tests pass.

### Task 3: Surface Execution Events

**Files:**
- Modify: `backend/app/api/runs.py`
- Test: `backend/tests/test_runs_api.py`

- [x] **Step 1: Add failing event test**

After a step executes, `/api/runs/{run_id}/events` should include a `step.executed` event with the step id and final status.

- [x] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python -m pytest tests\test_runs_api.py::test_run_events_api_includes_step_execution_event -q`

Expected: FAIL because execution events are not emitted.

- [x] **Step 3: Append execution event**

When a step has a recorded `duration_seconds`, append a `step.executed` event after `step.created`.

- [x] **Step 4: Run all backend tests**

Run: `.\.venv\Scripts\python -m pytest -q`

Expected: all tests pass.

### Self-Review

- Spec coverage: This plan covers only Phase 4 execution integration and leaves autonomous orchestration, LLM calls, artifact indexing, and real SSE to later phases.
- Placeholder scan: No TODO/TBD placeholders remain.
- Type consistency: Response field names match persisted result fields and runtime result names.
