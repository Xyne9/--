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
