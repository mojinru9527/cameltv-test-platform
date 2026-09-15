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


def test_ordinary_execution_paths_do_not_call_platform_llm() -> None:
    guarded = [
        ROOT / "backend/app/api/v1/apitest_tasks.py",
        ROOT / "backend/app/api/v1/test_plan_execution.py",
        ROOT / "backend/app/modules/campaign_execution/service.py",
        ROOT / "backend/app/modules/aitde/execution/service.py",
    ]
    offenders = []
    for path in guarded:
        text = path.read_text(encoding="utf-8")
        for token in ("ai_service", "AiProvider", "default_model"):
            if token in text:
                offenders.append(f"{path.name}:{token}")
    assert offenders == [], offenders


def test_canonical_campaign_path_does_not_call_legacy_bridge() -> None:
    text = (ROOT / "backend/app/modules/campaign_execution/service.py").read_text(
        encoding="utf-8"
    )
    assert "legacy_bridge" not in text
    assert "_ensure_legacy_run" not in text

def test_legacy_task_mutations_are_readonly() -> None:
    source = (ROOT / "backend/app/api/v1/apitest_tasks.py").read_text(encoding="utf-8")
    for start_marker, end_marker in (
        ('@router.delete("/tasks/{task_id}"', '@router.post("/tasks/{task_id}/cancel"'),
        ('@router.post("/tasks/{task_id}/cancel"', '@router.post("/tasks/{task_id}/retry-failed"'),
        ('@router.post("/tasks/{task_id}/retry-failed"', '@router.get("/tasks/{task_id}/items/{item_id}/curl"'),
    ):
        block = source[source.index(start_marker):source.index(end_marker, source.index(start_marker))]
        assert "_legacy_mutation_gone()" in block
        assert "db.commit()" not in block
        assert "create_execution_task" not in block


def test_legacy_runner_mutations_are_readonly() -> None:
    source = (ROOT / "backend/app/api/v1/api_runner.py").read_text(encoding="utf-8")
    start = source.index('@router.post("/tasks"')
    end = source.index('@router.get("/tasks"', start)
    block = source[start:end]
    assert "_legacy_runner_gone()" in block
    assert "svc.create_runner_task(" not in block
    assert "svc.claim_runner_task(" not in block
    assert "svc.report_runner_task(" not in block
    assert "db.commit()" not in block
