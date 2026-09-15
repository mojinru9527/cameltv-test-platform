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
