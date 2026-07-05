import pytest
from sqlmodel import Session

from app.storage.sqlite import create_db_and_tables, create_engine_for_path


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine_for_path(tmp_path / "project.sqlite")
    create_db_and_tables(engine)
    with Session(engine) as session:
        yield session
