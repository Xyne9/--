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
