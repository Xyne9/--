from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.agents.orchestrator import RunOrchestrator
from app.agents.planner import generate_initial_plan
from app.api.artifacts import ArtifactResponse, to_artifact_response
from app.api.deps import get_session
from app.artifacts.registry import index_step_artifacts, list_run_artifacts
from app.core.config import AppSettings, ensure_workspace, get_settings
from app.datasets.registry import (
    create_analysis_run,
    create_execution_step,
    get_dataset,
    get_dataset_profile,
    get_execution_step,
    get_project,
    get_run,
    list_run_steps,
    record_step_execution_result,
)
from app.execution.local_python import LocalPythonRuntime
from app.execution.runtime import ExecutionRequest
from app.storage.models import ExecutionStep


router = APIRouter(prefix="/api/runs", tags=["runs"])


class CreateRunRequest(BaseModel):
    project_id: str
    dataset_id: str
    user_goal: str


class StepResponse(BaseModel):
    id: str
    sequence: int
    title: str
    kind: str
    status: str
    code: str
    exit_code: int | None
    stdout: str
    stderr: str
    workdir: str | None
    artifacts_dir: str | None
    duration_seconds: float | None


class RunResponse(BaseModel):
    id: str
    project_id: str
    dataset_id: str
    user_goal: str
    status: str
    steps: list[StepResponse]


class RunArtifactsResponse(BaseModel):
    artifacts: list[ArtifactResponse]


class ExecuteStepRequest(BaseModel):
    code: str
    timeout_seconds: float = Field(default=30.0, gt=0)


class ExecuteStepResponse(BaseModel):
    run_id: str
    step_id: str
    status: str
    code: str
    exit_code: int | None
    stdout: str
    stderr: str
    workdir: str
    artifacts_dir: str
    duration_seconds: float


class ExecuteRunRequest(BaseModel):
    timeout_seconds: float = Field(default=30.0, gt=0)


class ExecuteRunResponse(BaseModel):
    run_id: str
    status: str
    steps: list[ExecuteStepResponse]


def to_execute_step_response(run_id: str, step: ExecutionStep) -> ExecuteStepResponse:
    return ExecuteStepResponse(
        run_id=run_id,
        step_id=step.id,
        status=step.status,
        code=step.code,
        exit_code=step.exit_code,
        stdout=step.stdout,
        stderr=step.stderr,
        workdir=step.workdir or "",
        artifacts_dir=step.artifacts_dir or "",
        duration_seconds=step.duration_seconds or 0.0,
    )


def to_run_response(session: Session, run_id: str) -> RunResponse:
    run = get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    steps = list_run_steps(session, run.id)
    return RunResponse(
        id=run.id,
        project_id=run.project_id,
        dataset_id=run.dataset_id,
        user_goal=run.user_goal,
        status=run.status,
        steps=[
            StepResponse(
                id=step.id,
                sequence=step.sequence,
                title=step.title,
                kind=step.kind,
                status=step.status,
                code=step.code,
                exit_code=step.exit_code,
                stdout=step.stdout,
                stderr=step.stderr,
                workdir=step.workdir,
                artifacts_dir=step.artifacts_dir,
                duration_seconds=step.duration_seconds,
            )
            for step in steps
        ],
    )


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def create_run_endpoint(
    request: CreateRunRequest,
    session: Session = Depends(get_session),
) -> RunResponse:
    if get_project(session, request.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    dataset = get_dataset(session, request.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    profile = get_dataset_profile(session, dataset.id)
    plan = generate_initial_plan(
        user_goal=request.user_goal,
        dataset_name=dataset.name,
        profile=profile,
    )
    run = create_analysis_run(
        session,
        project_id=request.project_id,
        dataset_id=request.dataset_id,
        user_goal=request.user_goal,
        status="PLAN_DRAFTED",
    )
    for step in plan["steps"]:
        create_execution_step(
            session,
            run_id=run.id,
            sequence=step["sequence"],
            title=step["title"],
            kind=step["kind"],
            status=step["status"],
        )
    return to_run_response(session, run.id)


@router.get("/{run_id}", response_model=RunResponse)
def get_run_endpoint(
    run_id: str,
    session: Session = Depends(get_session),
) -> RunResponse:
    return to_run_response(session, run_id)


@router.get("/{run_id}/artifacts", response_model=RunArtifactsResponse)
def list_run_artifacts_endpoint(
    run_id: str,
    session: Session = Depends(get_session),
) -> RunArtifactsResponse:
    run = get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunArtifactsResponse(
        artifacts=[to_artifact_response(artifact) for artifact in list_run_artifacts(session, run.id)]
    )


@router.post("/{run_id}/execute", response_model=ExecuteRunResponse)
def execute_run_endpoint(
    run_id: str,
    request: ExecuteRunRequest,
    session: Session = Depends(get_session),
    settings: AppSettings = Depends(get_settings),
) -> ExecuteRunResponse:
    try:
        result = RunOrchestrator().execute_run(
            session=session,
            settings=settings,
            run_id=run_id,
            timeout_seconds=request.timeout_seconds,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ExecuteRunResponse(
        run_id=result.run.id,
        status=result.run.status,
        steps=[
            to_execute_step_response(run_id=result.run.id, step=step)
            for step in result.steps
        ],
    )


@router.post("/{run_id}/steps/{step_id}/execute", response_model=ExecuteStepResponse)
def execute_step_endpoint(
    run_id: str,
    step_id: str,
    request: ExecuteStepRequest,
    session: Session = Depends(get_session),
    settings: AppSettings = Depends(get_settings),
) -> ExecuteStepResponse:
    run = get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    step = get_execution_step(session, step_id)
    if step is None or step.run_id != run.id:
        raise HTTPException(status_code=404, detail="Step not found")

    workspace_settings = ensure_workspace(settings)
    result = LocalPythonRuntime().execute(
        ExecutionRequest(
            run_id=run.id,
            step_id=step.id,
            code=request.code,
            workspace_root=workspace_settings.workspace_root,
            timeout_seconds=request.timeout_seconds,
        )
    )
    recorded_step = record_step_execution_result(session, step, result, code=request.code)
    index_step_artifacts(
        session,
        run_id=run.id,
        step_id=recorded_step.id,
        artifacts_dir=result.artifacts_dir,
        workspace_root=workspace_settings.workspace_root,
    )
    return to_execute_step_response(run_id=run.id, step=recorded_step)


@router.get("/{run_id}/events")
def get_run_events_endpoint(
    run_id: str,
    session: Session = Depends(get_session),
) -> dict[str, list[dict[str, Any]]]:
    run = get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    steps = list_run_steps(session, run.id)
    events: list[dict[str, Any]] = [
        {"type": "run.created", "run_id": run.id, "status": run.status},
        {"type": "plan.generated", "run_id": run.id, "step_count": len(steps)},
    ]
    for step in steps:
        events.append(
            {
                "type": "step.created",
                "run_id": run.id,
                "step_id": step.id,
                "sequence": step.sequence,
                "title": step.title,
                "kind": step.kind,
                "status": step.status,
            }
        )
        if step.duration_seconds is not None:
            events.append(
                {
                    "type": "step.executed",
                    "run_id": run.id,
                    "step_id": step.id,
                    "status": step.status,
                    "exit_code": step.exit_code,
                }
            )
    if run.status == "COMPLETED":
        events.append({"type": "run.completed", "run_id": run.id, "status": run.status})
    if run.status == "FAILED":
        events.append({"type": "run.failed", "run_id": run.id, "status": run.status})
    return {"events": events}
