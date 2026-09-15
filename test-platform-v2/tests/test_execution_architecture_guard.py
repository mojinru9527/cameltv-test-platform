from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_second_execution_model() -> None:
    assert not (ROOT / "backend/app/modules/execution/models.py").exists()


def test_no_new_execution_queue() -> None:
    offenders = [
        str(path)
        for path in ROOT.rglob("*_execution_queue.py")
        if path.name != "plan_execution_queue.py"
    ]
    assert offenders == [], offenders


def test_legacy_queue_files_are_present_for_controlled_cutover() -> None:
    assert (ROOT / "backend/app/services/api_task_worker.py").exists()
    assert (ROOT / "backend/app/services/plan_execution_queue.py").exists()


def test_api_task_create_uses_canonical_campaign_adapter() -> None:
    source = (ROOT / "backend/app/api/v1/apitest_tasks.py").read_text(encoding="utf-8")
    start = source.index("def create_task(")
    end = source.index('@router.get("/tasks"', start)
    block = source[start:end]
    assert "create_api_task_campaign" in block
    assert "create_execution_task" not in block
    assert "api_task_worker" not in block


def test_plan_execute_uses_canonical_campaign_adapter() -> None:
    source = (ROOT / "backend/app/api/v1/test_plan_execution.py").read_text(
        encoding="utf-8"
    )
    start = source.index("def execute_all_cases(")
    end = source.index('@router.post("/{plan_id}/auto-execute"', start)
    block = source[start:end]
    assert "create_plan_campaign" in block
    assert "plan_execution_queue" not in block
    assert "test_plan_service.execute_all_cases" not in block


def test_ci_does_not_start_legacy_executors_directly() -> None:
    workflows = ROOT / ".github/workflows"
    offenders = []
    for path in workflows.glob("*.y*ml"):
        text = path.read_text(encoding="utf-8")
        for token in ("api_task_worker", "plan_execution_queue", "playwright_executor"):
            if token in text:
                offenders.append(f"{path.name}:{token}")
    assert offenders == [], offenders
