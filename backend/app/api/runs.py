from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from app.agents.planner import generate_initial_plan
from app.api.deps import get_session
from app.datasets.registry import (
    create_analysis_run,
    create_execution_step,
    get_dataset,
    get_dataset_profile,
    get_project,
    get_run,
    list_run_steps,
)


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


class RunResponse(BaseModel):
    id: str
    project_id: str
    dataset_id: str
    user_goal: str
    status: str
    steps: list[StepResponse]


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
