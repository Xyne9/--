import pandas as pd

from app.datasets.profiler import profile_dataframe


def test_profile_dataframe_reports_table_shape_and_columns():
    frame = pd.DataFrame(
        {
            "customer_id": [1, 2, 3],
            "churn": [0, 1, 0],
            "plan": ["basic", "pro", None],
            "monthly_charge": [10.0, 25.5, 11.0],
        }
    )

    profile = profile_dataframe(frame)

    assert profile["row_count"] == 3
    assert profile["column_count"] == 4
    assert [column["name"] for column in profile["columns"]] == [
        "customer_id",
        "churn",
        "plan",
        "monthly_charge",
    ]


def test_profile_dataframe_reports_missing_and_unique_counts():
    frame = pd.DataFrame({"plan": ["basic", "pro", None, "basic"]})

    profile = profile_dataframe(frame)

    column = profile["columns"][0]
    assert column["missing_rate"] == 0.25
    assert column["unique_count"] == 2
    assert column["nullable"] is True
    assert column["logical_type"] == "categorical"
    assert column["sample_values"] == ["basic", "pro"]
