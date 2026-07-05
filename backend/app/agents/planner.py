from typing import Any


def generate_initial_plan(
    *,
    user_goal: str,
    dataset_name: str,
    profile: dict[str, Any],
) -> dict[str, Any]:
    row_count = profile["row_count"]
    column_count = profile["column_count"]
    column_names = [column["name"] for column in profile["columns"]]

    return {
        "goal": user_goal,
        "dataset_name": dataset_name,
        "context": {
            "row_count": row_count,
            "column_count": column_count,
            "columns": column_names,
        },
        "steps": [
            {
                "sequence": 1,
                "title": "Review dataset profile",
                "kind": "profile",
                "status": "pending",
            },
            {
                "sequence": 2,
                "title": "Identify exploratory analysis angles",
                "kind": "eda",
                "status": "pending",
            },
            {
                "sequence": 3,
                "title": "Summarize initial findings and next actions",
                "kind": "summary",
                "status": "pending",
            },
        ],
    }
