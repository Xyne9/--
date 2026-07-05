from app.datasets.registry import create_project, get_project


def test_create_and_get_project(db_session):
    project = create_project(db_session, name="Customer Churn")

    loaded = get_project(db_session, project.id)

    assert loaded is not None
    assert loaded.id == project.id
    assert loaded.name == "Customer Churn"
