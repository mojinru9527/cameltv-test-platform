import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_legacy_files_remain_until_delete_gate_is_fully_satisfied() -> None:
    gate = json.loads((ROOT / "backend/tests/fixtures/legacy_delete_gate.json").read_text(encoding="utf-8"))
    assert all(gate.values()), gate
    assert not (ROOT / "backend/app/services/api_task_worker.py").exists()
    assert not (ROOT / "backend/app/services/plan_execution_queue.py").exists()


def test_legacy_bridge_has_no_implicit_run_creation() -> None:
    source = (ROOT / "backend/app/modules/aitde/execution/legacy_bridge.py").read_text(encoding="utf-8")
    assert "_ensure_legacy_run" not in source
    assert "run_id is None" not in source
