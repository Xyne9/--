# Phase 3 Local Python Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local Python execution runtime adapter that can run controlled backend-generated analysis code inside a per-run workspace and return structured execution results.

**Architecture:** This phase adds an internal execution contract and a subprocess-backed local Python runtime. Each execution writes a script into `workspace/runs/<run_id>/steps/<step_id>/`, captures stdout/stderr, reports completed/failed/timeout status, and creates an artifacts directory for future outputs.

**Tech Stack:** Python 3.11+, dataclasses, subprocess, pytest.

---

## Scope

This phase implements:

- `ExecutionRequest` and `ExecutionResult` contracts.
- `LocalPythonRuntime` for backend-controlled Python code.
- Per-step work directories and artifact directories.
- Completed, failed, and timeout result states.
- Unit tests covering success, failure, timeout, and workspace layout.

This phase does not expose an execution HTTP endpoint, execute LLM-generated code, stream logs, persist artifacts in SQLite, or connect execution steps to `AnalysisRun` status updates.

## File Structure

Create these files:

```text
backend/app/execution/__init__.py
backend/app/execution/runtime.py
backend/app/execution/local_python.py
backend/tests/test_local_python_runtime.py
```

Responsibilities:

- `runtime.py`: Defines request and result dataclasses.
- `local_python.py`: Writes scripts, creates directories, invokes the current Python executable, and returns results.
- `test_local_python_runtime.py`: Verifies behavior without touching global state.

---

### Task 1: Execution Contracts

**Files:**
- Create: `backend/app/execution/__init__.py`
- Create: `backend/app/execution/runtime.py`
- Create: `backend/tests/test_local_python_runtime.py`

- [ ] **Step 1: Write failing contract test**

Create `backend/tests/test_local_python_runtime.py` with:

```python
from pathlib import Path

from app.execution.runtime import ExecutionRequest, ExecutionResult


def test_execution_contracts_store_request_and_result_paths(tmp_path):
    request = ExecutionRequest(
        run_id="run_1",
        step_id="step_1",
        code="print('hello')",
        workspace_root=tmp_path,
        timeout_seconds=1.0,
    )
    result = ExecutionResult(
        status="completed",
        exit_code=0,
        stdout="hello\n",
        stderr="",
        workdir=tmp_path / "runs" / "run_1" / "steps" / "step_1",
        artifacts_dir=tmp_path / "runs" / "run_1" / "steps" / "step_1" / "artifacts",
        duration_seconds=0.01,
    )

    assert request.workspace_root == Path(tmp_path)
    assert request.timeout_seconds == 1.0
    assert result.status == "completed"
    assert result.artifacts_dir.name == "artifacts"
```

- [ ] **Step 2: Run contract test and verify it fails**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_local_python_runtime.py::test_execution_contracts_store_request_and_result_paths -q
```

Expected: FAIL because `app.execution.runtime` does not exist.

- [ ] **Step 3: Implement contracts**

Create `backend/app/execution/__init__.py` with:

```python
"""Execution runtime adapters."""
```

Create `backend/app/execution/runtime.py` with:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


ExecutionStatus = Literal["completed", "failed", "timeout"]


@dataclass(frozen=True)
class ExecutionRequest:
    run_id: str
    step_id: str
    code: str
    workspace_root: Path
    timeout_seconds: float = 30.0


@dataclass(frozen=True)
class ExecutionResult:
    status: ExecutionStatus
    exit_code: int | None
    stdout: str
    stderr: str
    workdir: Path
    artifacts_dir: Path
    duration_seconds: float
```

- [ ] **Step 4: Run contract test and verify it passes**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_local_python_runtime.py::test_execution_contracts_store_request_and_result_paths -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

Run:

```powershell
git add backend/app/execution backend/tests/test_local_python_runtime.py
git commit -m "feat: add execution runtime contracts"
```

---

### Task 2: Local Python Runtime Success And Failure

**Files:**
- Create: `backend/app/execution/local_python.py`
- Modify: `backend/tests/test_local_python_runtime.py`

- [ ] **Step 1: Add failing success and failure tests**

Append to `backend/tests/test_local_python_runtime.py`:

```python
from app.execution.local_python import LocalPythonRuntime


def test_local_python_runtime_captures_success_stdout(tmp_path):
    runtime = LocalPythonRuntime()
    request = ExecutionRequest(
        run_id="run_success",
        step_id="step_success",
        code="print('hello runtime')",
        workspace_root=tmp_path,
        timeout_seconds=2.0,
    )

    result = runtime.execute(request)

    assert result.status == "completed"
    assert result.exit_code == 0
    assert result.stdout.strip() == "hello runtime"
    assert result.stderr == ""
    assert (result.workdir / "script.py").exists()
    assert result.artifacts_dir.exists()


def test_local_python_runtime_reports_failure_exit_code(tmp_path):
    runtime = LocalPythonRuntime()
    request = ExecutionRequest(
        run_id="run_failure",
        step_id="step_failure",
        code="raise SystemExit(7)",
        workspace_root=tmp_path,
        timeout_seconds=2.0,
    )

    result = runtime.execute(request)

    assert result.status == "failed"
    assert result.exit_code == 7
```

- [ ] **Step 2: Run runtime tests and verify they fail**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_local_python_runtime.py::test_local_python_runtime_captures_success_stdout -q
```

Expected: FAIL because `LocalPythonRuntime` does not exist.

- [ ] **Step 3: Implement local runtime**

Create `backend/app/execution/local_python.py` with:

```python
import os
from pathlib import Path
import subprocess
import sys
import time

from app.execution.runtime import ExecutionRequest, ExecutionResult, ExecutionStatus


class LocalPythonRuntime:
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        started_at = time.perf_counter()
        workdir = self.step_workdir(request)
        artifacts_dir = workdir / "artifacts"
        workdir.mkdir(parents=True, exist_ok=True)
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        script_path = workdir / "script.py"
        script_path.write_text(request.code, encoding="utf-8")

        try:
            completed = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
                env=self.execution_env(),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return ExecutionResult(
                status="timeout",
                exit_code=None,
                stdout=self.output_text(exc.stdout),
                stderr=self.output_text(exc.stderr),
                workdir=workdir,
                artifacts_dir=artifacts_dir,
                duration_seconds=self.duration_since(started_at),
            )

        return ExecutionResult(
            status=self.status_for_exit_code(completed.returncode),
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            workdir=workdir,
            artifacts_dir=artifacts_dir,
            duration_seconds=self.duration_since(started_at),
        )

    def step_workdir(self, request: ExecutionRequest) -> Path:
        return request.workspace_root / "runs" / request.run_id / "steps" / request.step_id

    def execution_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        return env

    def status_for_exit_code(self, exit_code: int) -> ExecutionStatus:
        return "completed" if exit_code == 0 else "failed"

    def duration_since(self, started_at: float) -> float:
        return round(time.perf_counter() - started_at, 6)

    def output_text(self, value: str | bytes | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value
```

- [ ] **Step 4: Run success and failure tests**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_local_python_runtime.py -q
```

Expected: PASS for contract, success, and failure tests.

- [ ] **Step 5: Commit Task 2**

Run:

```powershell
git add backend/app/execution/local_python.py backend/tests/test_local_python_runtime.py
git commit -m "feat: add local python runtime"
```

---

### Task 3: Timeout And Full Verification

**Files:**
- Modify: `backend/tests/test_local_python_runtime.py`

- [ ] **Step 1: Add failing timeout test**

Append to `backend/tests/test_local_python_runtime.py`:

```python
def test_local_python_runtime_reports_timeout(tmp_path):
    runtime = LocalPythonRuntime()
    request = ExecutionRequest(
        run_id="run_timeout",
        step_id="step_timeout",
        code="import time\ntime.sleep(2)",
        workspace_root=tmp_path,
        timeout_seconds=0.1,
    )

    result = runtime.execute(request)

    assert result.status == "timeout"
    assert result.exit_code is None
    assert result.duration_seconds < 2.0
```

- [ ] **Step 2: Run timeout test and verify it passes or fails for the intended reason**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_local_python_runtime.py::test_local_python_runtime_reports_timeout -q
```

Expected: PASS if timeout handling already works, otherwise FAIL with timeout result mismatch.

- [ ] **Step 3: Fix timeout handling when needed**

If the test fails because timeout output is not normalized, update `output_text()` in `backend/app/execution/local_python.py` to preserve `None`, `str`, and `bytes` safely:

```python
    def output_text(self, value: str | bytes | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value
```

- [ ] **Step 4: Run all backend tests**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
```

Expected: PASS for every backend test.

- [ ] **Step 5: Commit Task 3**

Run:

```powershell
git add backend/app/execution/local_python.py backend/tests/test_local_python_runtime.py
git commit -m "test: cover local python timeout"
```

---

## Self-Review Checklist

Spec coverage for this phase:

- ExecutionRequest and ExecutionResult contract: covered by Task 1.
- Local Python runtime adapter: covered by Task 2.
- Per-step workspace directory: covered by Task 2.
- Timeout behavior: covered by Task 3.

Spec items intentionally outside this phase:

- Docker runtime.
- API endpoint for execution.
- Persisted artifact metadata.
- Step status updates in SQLite.
- LLM-generated code execution.

Final verification command:

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
```

Expected final backend state:

```text
All existing tests pass.
ExecutionRequest captures run id, step id, code, workspace root, and timeout.
LocalPythonRuntime writes script.py into the step workdir.
LocalPythonRuntime returns completed, failed, and timeout states.
Artifacts directory is created for each execution.
```

