from typing import Any

import pandas as pd


def infer_logical_type(series: pd.Series) -> str:
    non_null = series.dropna()
    if non_null.empty:
        return "unknown"
    if pd.api.types.is_bool_dtype(non_null):
        return "boolean"
    if pd.api.types.is_integer_dtype(non_null):
        return "integer"
    if pd.api.types.is_float_dtype(non_null):
        return "float"
    if pd.api.types.is_datetime64_any_dtype(non_null):
        return "timestamp"

    unique_count = int(non_null.nunique(dropna=True))
    if unique_count <= max(20, int(len(non_null) * 0.2)):
        return "categorical"
    return "text"


def json_safe_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def sample_values(series: pd.Series, limit: int = 5) -> list[Any]:
    values = []
    for value in series.dropna().drop_duplicates().head(limit).tolist():
        values.append(json_safe_value(value))
    return values


def profile_dataframe(frame: pd.DataFrame) -> dict[str, Any]:
    row_count = int(len(frame))
    columns: list[dict[str, Any]] = []

    for name in frame.columns:
        series = frame[name]
        missing_count = int(series.isna().sum())
        missing_rate = 0.0 if row_count == 0 else missing_count / row_count
        columns.append(
            {
                "name": str(name),
                "logical_type": infer_logical_type(series),
                "physical_type": str(series.dtype),
                "nullable": bool(missing_count > 0),
                "missing_rate": round(missing_rate, 6),
                "unique_count": int(series.nunique(dropna=True)),
                "sample_values": sample_values(series),
                "semantic_role": "feature",
                "pii_risk": "unknown",
            }
        )

    return {
        "row_count": row_count,
        "column_count": int(len(frame.columns)),
        "columns": columns,
    }
