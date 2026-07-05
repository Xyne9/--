from pathlib import Path
from typing import Any

import duckdb


def connect_duckdb(path: Path) -> duckdb.DuckDBPyConnection:
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def create_table_from_csv(db_path: Path, table_name: str, csv_path: Path) -> None:
    with connect_duckdb(db_path) as connection:
        connection.execute(
            f'CREATE OR REPLACE TABLE "{table_name}" AS SELECT * FROM read_csv_auto(?)',
            [str(csv_path)],
        )


def preview_table(db_path: Path, table_name: str, limit: int = 20) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 100))
    with connect_duckdb(db_path) as connection:
        result = connection.execute(f'SELECT * FROM "{table_name}" LIMIT {safe_limit}')
        columns = [description[0] for description in result.description]
        rows = [dict(zip(columns, row, strict=False)) for row in result.fetchall()]
    return {"columns": columns, "rows": rows}
