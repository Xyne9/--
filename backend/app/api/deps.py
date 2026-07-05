from collections.abc import Generator

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.core.config import ensure_workspace, get_settings
from app.storage.sqlite import create_db_and_tables, create_engine_for_path


_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = ensure_workspace(get_settings())
        _engine = create_engine_for_path(settings.sqlite_path)
        create_db_and_tables(_engine)
    return _engine


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session
