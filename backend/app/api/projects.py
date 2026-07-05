from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from app.api.deps import get_session
from app.datasets.registry import create_project, get_project


router = APIRouter(prefix="/api/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str


class ProjectResponse(BaseModel):
    id: str
    name: str


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project_endpoint(
    request: CreateProjectRequest,
    session: Session = Depends(get_session),
) -> ProjectResponse:
    project = create_project(session, request.name)
    return ProjectResponse(id=project.id, name=project.name)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project_endpoint(
    project_id: str,
    session: Session = Depends(get_session),
) -> ProjectResponse:
    project = get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(id=project.id, name=project.name)
