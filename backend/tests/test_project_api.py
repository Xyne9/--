from app.datasets.registry import create_project, get_project


def test_create_and_get_project(db_session):
    project = create_project(db_session, name="Customer Churn")

    loaded = get_project(db_session, project.id)

    assert loaded is not None
    assert loaded.id == project.id
    assert loaded.name == "Customer Churn"


from fastapi.testclient import TestClient

from app.api.deps import get_session
from app.main import app


def test_create_project_api(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    client = TestClient(app)

    response = client.post("/api/projects", json={"name": "Local DS Agent"})

    app.dependency_overrides.clear()
    assert response.status_code == 201
    body = response.json()
    assert body["id"].startswith("proj_")
    assert body["name"] == "Local DS Agent"


def test_get_project_api(db_session):
    project = create_project(db_session, name="Existing Project")
    app.dependency_overrides[get_session] = lambda: db_session
    client = TestClient(app)

    response = client.get(f"/api/projects/{project.id}")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["name"] == "Existing Project"
