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
