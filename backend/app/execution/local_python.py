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
