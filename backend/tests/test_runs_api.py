from app.datasets.registry import create_analysis_run, create_execution_step, create_project, get_run


def test_create_run_and_steps(db_session):
    project = create_project(db_session, "Run Project")

    run = create_analysis_run(
        db_session,
        project_id=project.id,
        dataset_id="ds_example",
        user_goal="Summarize this dataset",
        status="PLAN_DRAFTED",
    )
    step = create_execution_step(
        db_session,
        run_id=run.id,
        sequence=1,
        title="Profile dataset",
        kind="profile",
        status="pending",
    )

    loaded = get_run(db_session, run.id)

    assert loaded is not None
    assert loaded.id.startswith("run_")
    assert step.id.startswith("step_")
    assert loaded.user_goal == "Summarize this dataset"
